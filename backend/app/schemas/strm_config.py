"""StrmConfig Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class StrmConfigCreate(BaseModel):
    strm_base_url: str = Field(..., max_length=512)
    media_library_path: str = Field(..., max_length=1024)
    auto_generate: bool = True


class StrmConfigUpdate(BaseModel):
    strm_base_url: str | None = Field(None, max_length=512)
    media_library_path: str | None = Field(None, max_length=1024)
    auto_generate: bool | None = None


class StrmConfigResponse(BaseModel):
    id: int
    strm_base_url: str
    media_library_path: str
    auto_generate: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
