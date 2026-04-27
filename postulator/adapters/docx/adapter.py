"""DOCX adapter — read and write Post models to/from DOCX files."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any

from docx import Document

from ...models import Post, AuthorRef, TagRef, SeoMeta
from ...models import (
    BlockNode, TextNode, ParagraphNode, AudiobookListNode,
    AssetRef, LocalAsset,
)
from ...events import (
    BaseEvent, ReadingMetadataEvent, ReadingBodyEvent, ParseWarningEvent,
    WritingMetadataEvent, WritingBodyEvent, WritingFeaturedImageEvent,
)
from .placeholders import slugify
from ._reader import parse_document
from ._writer import build_document


class DocxAdapter:
    def __init__(self, on_progress: Callable | None = None, image_dir: str | None = None):
        self._on_progress = on_progress
        self._image_dir = image_dir

    def _emit(self, event: BaseEvent) -> None:
        if self._on_progress:
            self._on_progress(event)

    # ==================================================================
    # READ
    # ==================================================================

    def read(self, path: str | Path) -> Post:
        doc = Document(str(path))
        return self._parse(doc, filename=Path(path).stem)

    def read_bytes(self, data: bytes, filename: str | None = None) -> Post:
        doc = Document(io.BytesIO(data))
        return self._parse(doc, filename=filename)

    def _parse(self, doc: Document, filename: str | None = None) -> Post:
        self._emit(ReadingMetadataEvent())
        metadata, body_nodes, featured_image = parse_document(doc, self._image_dir)
        self._emit(ReadingBodyEvent(paragraph_count=len(body_nodes)))

        post = self._assemble_post(metadata, body_nodes, featured_image)
        self._post_process(post, filename)
        return post

    # ------------------------------------------------------------------
    # Assembly (pure mapping, no cross-placeholder defaults)
    # ------------------------------------------------------------------

    def _assemble_post(self, metadata: dict, body_nodes: list[BlockNode],
                       featured_image: AssetRef | LocalAsset | None) -> Post:
        post_meta = metadata.get("post", {})
        locale = post_meta.get("locale") or "en-US"
        title = post_meta.get("title") or ""

        # Intro precedence: [Intro] block > POST intro key
        introduction = None
        if "intro" in metadata:
            introduction = metadata["intro"].get("text", "")
        elif post_meta.get("introduction") is not None:
            introduction = post_meta["introduction"]

        authors = [
            AuthorRef(
                slug=a["name"].lower().replace(" ", "-"),
                locale=locale,
                name=a["name"],
                source_id=a.get("source_id"),
            )
            for a in metadata.get("authors", {}).get("authors", [])
        ]

        tags = [
            TagRef(
                slug=t["name"].lower().replace(" ", "-"),
                locale=locale,
                name=t["name"],
                source_id=t.get("source_id"),
            )
            for t in metadata.get("tags", {}).get("tags", [])
        ]

        seo = None
        seo_data = metadata.get("seo")
        if seo_data:
            seo = SeoMeta(
                source_id=seo_data.get("source_id"),
                label=seo_data.get("label"),
                meta_title=seo_data.get("meta_title"),
                meta_description=seo_data.get("meta_description"),
                og_title=seo_data.get("og_title"),
                og_description=seo_data.get("og_description"),
                no_index=seo_data.get("no_index"),
                schema_type=seo_data.get("schema_type"),
                slug_replacement=seo_data.get("slug_replacement"),
                slug_redirect=seo_data.get("slug_redirect"),
                external_links_source_code=seo_data.get("external_links_source_code"),
            )

        fi_meta = metadata.get("featured_image", {})
        if not featured_image and fi_meta.get("source_id"):
            featured_image = AssetRef(
                source_id=fi_meta.get("source_id"),
                title=fi_meta.get("title"),
                alt=fi_meta.get("alt"),
            )

        return Post(
            source_id=post_meta.get("source_id"),
            slug=post_meta.get("slug") or "",
            locale=locale,
            title=title,
            date=post_meta.get("date") or datetime.now(timezone.utc),
            introduction=introduction,
            body=body_nodes if body_nodes else [ParagraphNode(children=[TextNode(value="")])],
            featured_image=featured_image,
            authors=authors,
            tags=tags,
            seo=seo,
            update_date=post_meta.get("update_date"),
            show_in_feed=post_meta.get("show_in_feed", True),
            show_publish_date=post_meta.get("show_publish_date", True),
            show_hero_image=post_meta.get("show_hero_image", True),
            custom_recommended_title=post_meta.get("custom_recommended_title"),
            related_posts=post_meta.get("related_posts", []),
        )

    # ------------------------------------------------------------------
    # Post-processing (cross-placeholder defaults, inference)
    # ------------------------------------------------------------------

    def _post_process(self, post: Post, filename: str | None = None) -> None:
        """Apply cross-placeholder defaults and inference. Mutates post in-place.

        Order matters — later rules depend on earlier ones.
        """
        # 1. Title: POST title > filename
        if not post.title and filename:
            post.title = filename
            self._emit(ParseWarningEvent(message=f"No title found, using filename: {filename}"))

        # 2. Slug: POST slug > derived from title
        if not post.slug and post.title:
            post.slug = slugify(post.title)

        # 3. Date: already defaulted to today in _assemble_post

        # 4. Intro: [Intro] > POST intro already resolved in _assemble_post.
        #    Here we apply the first-paragraph fallback.
        if post.introduction is None:
            if post.body and isinstance(post.body[0], ParagraphNode):
                first = post.body[0]
                text = "".join(
                    c.value for c in first.children if isinstance(c, TextNode)
                ).strip()
                if text:
                    post.introduction = text
                    post.body = post.body[1:]
                    if not post.body:
                        post.body = [ParagraphNode(children=[TextNode(value="")])]

        # 5–9. SEO defaults
        if post.seo:
            if not post.seo.meta_title:
                post.seo.meta_title = post.title
            if not post.seo.meta_description and post.introduction:
                post.seo.meta_description = post.introduction
            if not post.seo.og_title:
                post.seo.og_title = post.seo.meta_title
            if not post.seo.og_description:
                post.seo.og_description = post.seo.meta_description
            if not post.seo.label and post.seo.meta_title:
                post.seo.label = f"SEO Settings {post.seo.meta_title}"

        # 10–11. Featured image defaults
        if isinstance(post.featured_image, AssetRef):
            if not post.featured_image.title:
                post.featured_image.title = post.title
            if not post.featured_image.alt:
                post.featured_image.alt = post.title

        # 12. LIST label defaults
        for node in post.body:
            if isinstance(node, AudiobookListNode) and not node.label:
                node.label = post.title

    # ==================================================================
    # WRITE
    # ==================================================================

    def write(self, post: Post, path: str | Path) -> None:
        doc = self._build(post)
        doc.save(str(path))

    def write_bytes(self, post: Post) -> bytes:
        doc = self._build(post)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def _build(self, post: Post) -> Document:
        self._emit(WritingMetadataEvent())

        def _on_image(img):
            self._emit(WritingFeaturedImageEvent(url=getattr(img, "url", None)))

        self._emit(WritingBodyEvent(node_count=len(post.body)))
        return build_document(post, on_image_event=_on_image)
