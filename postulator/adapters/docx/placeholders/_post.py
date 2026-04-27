from __future__ import annotations
from typing import Any

from ._base import (
    BasePlaceholder, ml, locale_to_market, resolve_locale,
    split_lines, parse_kv_segments, resolve_aliases,
    parse_bool, parse_date_flexible,
)
from ....models import Post


_ALIASES: dict[str, str] = {
    "title": "title",
    "market": "market",
    "slug": "slug",
    "date": "date",
    "intro": "intro",
    "introduction": "intro",
    "source_id": "source_id",
    "update_date": "update_date",
    "show_in_feed": "show_in_feed",
    "feed": "show_in_feed",
    "show_publish_date": "show_publish_date",
    "show_hero_image": "show_hero_image",
    "custom_recommended_title": "custom_recommended_title",
    "related_posts": "related_posts",
}


class PostPlaceholder(BasePlaceholder):
    keywords = ["post"]

    @classmethod
    def format(cls, post: Post, **ctx) -> str:
        market = locale_to_market(post.locale)
        lines = [
            f"title = {post.title}",
            f"market = {market}",
            f"slug = {post.slug}",
            f"date = {post.date.strftime('%Y-%m-%d')}",
        ]
        if post.source_id:
            lines.append(f"source-id = {post.source_id}")
        if post.update_date:
            lines.append(f"update-date = {post.update_date.strftime('%Y-%m-%d')}")
        if post.custom_recommended_title:
            lines.append(f"custom-recommended-title = {post.custom_recommended_title}")
        if not post.show_in_feed:
            lines.append("show-in-feed = false")
        if not post.show_publish_date:
            lines.append("show-publish-date = false")
        if not post.show_hero_image:
            lines.append("show-hero-image = false")
        if post.related_posts:
            lines.append(f"related-posts = {','.join(post.related_posts)}")
        return ml("Post", lines)

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        lines = split_lines(content)
        kv = parse_kv_segments(lines)
        kv = resolve_aliases(kv, _ALIASES)

        date = parse_date_flexible(kv["date"]) if "date" in kv else None
        update_date = parse_date_flexible(kv["update_date"]) if "update_date" in kv else None

        related = []
        if "related_posts" in kv:
            related = [r.strip() for r in kv["related_posts"].split(",") if r.strip()]

        locale = resolve_locale(kv)

        return {
            "type": "post",
            "title": kv.get("title"),
            "slug": kv.get("slug"),
            "locale": locale,
            "date": date,
            "introduction": kv.get("intro"),
            "source_id": kv.get("source_id"),
            "update_date": update_date,
            "show_in_feed": parse_bool(kv.get("show_in_feed", "true")),
            "show_publish_date": parse_bool(kv.get("show_publish_date", "true")),
            "show_hero_image": parse_bool(kv.get("show_hero_image", "true")),
            "custom_recommended_title": kv.get("custom_recommended_title"),
            "related_posts": related,
        }
