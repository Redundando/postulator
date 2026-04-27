"""Typed progress events for postulator adapters and enrichers."""

from dataclasses import dataclass, field
import time


@dataclass
class BaseEvent:
    ts: float = field(default_factory=time.time)


# --- Contentful: ASIN events ---

@dataclass
class ResolvingAsinsEvent(BaseEvent):
    count: int = 0

@dataclass
class EnrichingAsinsEvent(BaseEvent):
    count: int = 0

@dataclass
class WritingAsinEvent(BaseEvent):
    asin: str = ""
    marketplace: str = ""

@dataclass
class AsinPublishConflictEvent(BaseEvent):
    asin: str = ""
    entry_id: str = ""

@dataclass
class AsinDraftCleanupEvent(BaseEvent):
    asin: str = ""
    entry_id: str = ""

@dataclass
class AsinPublishFailedEvent(BaseEvent):
    asin: str = ""
    message: str = ""


# --- Contentful: Asset events ---

@dataclass
class UploadingAssetEvent(BaseEvent):
    title: str = ""
    file_name: str = ""

@dataclass
class AssetUploadFailedEvent(BaseEvent):
    title: str = ""
    message: str = ""

@dataclass
class AssetProcessingTimeoutEvent(BaseEvent):
    asset_id: str = ""


# --- Contentful: Post events ---

@dataclass
class WritingPostEvent(BaseEvent):
    entry_id: str = ""

@dataclass
class CreatingPostEvent(BaseEvent):
    slug: str = ""
    locale: str = ""

@dataclass
class PostInvalidEvent(BaseEvent):
    slug: str = ""
    reason: str = ""


# --- Contentful: Author events ---

@dataclass
class WritingAuthorEvent(BaseEvent):
    entry_id: str = ""

@dataclass
class CreatingAuthorEvent(BaseEvent):
    slug: str = ""


# --- Contentful: Tag/Author resolution ---

@dataclass
class TagResolvedEvent(BaseEvent):
    name: str = ""
    source_id: str = ""

@dataclass
class TagNotFoundEvent(BaseEvent):
    name: str = ""

@dataclass
class AuthorResolvedEvent(BaseEvent):
    name: str = ""
    source_id: str = ""

@dataclass
class AuthorNotFoundEvent(BaseEvent):
    name: str = ""


# --- Contentful: Embed skip events ---

@dataclass
class ListSkippedEvent(BaseEvent):
    reason: str = ""

@dataclass
class CarouselSkippedEvent(BaseEvent):
    reason: str = ""
    asins: list[str] = field(default_factory=list)


# --- Contentful: Read events ---

@dataclass
class FetchingEntriesEvent(BaseEvent):
    count: int = 0

@dataclass
class FetchingNestedEvent(BaseEvent):
    count: int = 0

@dataclass
class ParsingEvent(BaseEvent):
    pass


# --- HTTP events ---

@dataclass
class RequestFailedEvent(BaseEvent):
    method: str = ""
    url: str = ""
    status_code: int = 0


# --- DOCX events ---

@dataclass
class ReadingMetadataEvent(BaseEvent):
    pass

@dataclass
class ReadingBodyEvent(BaseEvent):
    paragraph_count: int = 0

@dataclass
class ReadingEmbedEvent(BaseEvent):
    type: str = ""
    asin: str | None = None
    asins: list[str] | None = None

@dataclass
class ReadingImageEvent(BaseEvent):
    index: int = 0

@dataclass
class WritingMetadataEvent(BaseEvent):
    pass

@dataclass
class WritingBodyEvent(BaseEvent):
    node_count: int = 0

@dataclass
class WritingEmbedEvent(BaseEvent):
    type: str = ""
    asin: str | None = None
    asins: list[str] | None = None

@dataclass
class WritingFeaturedImageEvent(BaseEvent):
    url: str | None = None

@dataclass
class WritingImageEvent(BaseEvent):
    url: str | None = None

@dataclass
class ImageDownloadFailedEvent(BaseEvent):
    url: str = ""
    message: str = ""

@dataclass
class ParseWarningEvent(BaseEvent):
    message: str = ""
