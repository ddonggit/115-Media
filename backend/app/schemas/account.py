"""Account115 Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class Account115Create(BaseModel):
    cookie: str = Field(..., max_length=4096, description="encrypted cookie")
    uid: str | None = Field(None, max_length=64)
    username: str | None = Field(None, max_length=128)
    total_space: int | None = Field(None, description="bytes")
    used_space: int | None = Field(None, description="bytes")
    expire_time: datetime | None = None


class Account115Update(BaseModel):
    cookie: str | None = Field(None, max_length=4096)
    uid: str | None = Field(None, max_length=64)
    username: str | None = Field(None, max_length=128)
    total_space: int | None = None
    used_space: int | None = None
    expire_time: datetime | None = None


class Account115Response(BaseModel):
    id: int
    uid: str | None
    username: str | None
    total_space: int | None
    used_space: int | None
    expire_time: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
