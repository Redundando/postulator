from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel

from .nodes import DocumentNode, AssetRef, LocalAsset


class AuthorRef(BaseModel):
    slug: str
    locale: str
    name: str
    source_id: str | None = None


class TagRef(BaseModel):
    slug: str
    locale: str
    name: str
    source_id: str | None = None


class SeoMeta(BaseModel):
    source_id: str | None = None
    label: str | None = None
    slug_replacement: str | None = None
    slug_redirect: str | None = None
    no_index: bool | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: AssetRef | LocalAsset | None = None
    schema_type: str | None = None
    json_ld_id: str | None = None
    similar_content_ids: list[str] = []
    external_links_source_code: str | None = None


class Author(BaseModel):
    source_id: str | None = None
    country_code: str | None = None
    slug: str
    name: str
    short_name: str | None = None
    title: str | None = None
    bio: str | None = None
    picture: AssetRef | LocalAsset | None = None
    seo: SeoMeta | None = None


class Post(BaseModel):
    source_id: str | None = None
    slug: str
    locale: str
    title: str
    date: datetime
    introduction: str | None = None
    body: DocumentNode
    featured_image: AssetRef | LocalAsset | None = None
    authors: list[AuthorRef] = []
    tags: list[TagRef] = []
    update_date: datetime | None = None
    seo: SeoMeta | None = None
    custom_recommended_title: str | None = None
    show_in_feed: bool = True
    show_publish_date: bool = True
    show_hero_image: bool = True
    related_posts: list[str] = []
