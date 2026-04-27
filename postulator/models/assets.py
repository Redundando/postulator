from pydantic import BaseModel


class AssetRef(BaseModel):
    source_id: str | None = None
    url: str | None = None
    title: str | None = None
    alt: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    width: int | None = None
    height: int | None = None
    size: int | None = None


class LocalAsset(BaseModel):
    local_path: str
    title: str
    alt: str | None = None
    file_name: str | None = None
    content_type: str | None = None
