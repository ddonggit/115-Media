"""NotifyConfig Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class NotifyConfigCreate(BaseModel):
    channel: str = Field(..., pattern="^(feishu|telegram)$")
    webhook_url: str = Field(..., max_length=1024, description="will be encrypted")
    bot_token: str | None = Field(None, max_length=256, description="telegram only, encrypted")
    chat_id: str | None = Field(None, max_length=128, description="telegram only")
    enabled: bool = False
    notify_on: list[str] | None = Field(None, description="e.g. ['transfer_done','organize_done']")


class NotifyConfigUpdate(BaseModel):
    webhook_url: str | None = Field(None, max_length=1024)
    bot_token: str | None = Field(None, max_length=256)
    chat_id: str | None = Field(None, max_length=128)
    enabled: bool | None = None
    notify_on: list[str] | None = None


class NotifyConfigResponse(BaseModel):
    id: int
    channel: str
    enabled: bool
    notify_on: list[str] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True