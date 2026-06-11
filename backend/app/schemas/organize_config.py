"""OrganizeConfig Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class OrganizeConfigCreate(BaseModel):
    source_cid: str = Field(..., max_length=64)
    duplicate_cid: str = Field(..., max_length=64)
    processed_cid: str = Field(..., max_length=64)


class OrganizeConfigUpdate(BaseModel):
    source_cid: str | None = Field(None, max_length=64)
    duplicate_cid: str | None = Field(None, max_length=64)
    processed_cid: str | None = Field(None, max_length=64)


class OrganizeConfigResponse(BaseModel):
    id: int
    source_cid: str
    duplicate_cid: str
    processed_cid: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
