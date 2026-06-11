"""SubscriptionConfig Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class SubscriptionConfigCreate(BaseModel):
    rss_check_interval_minutes: int = Field(10, ge=5, le=1440)


class SubscriptionConfigUpdate(BaseModel):
    rss_check_interval_minutes: int | None = Field(None, ge=5, le=1440)


class SubscriptionConfigResponse(BaseModel):
    id: int
    rss_check_interval_minutes: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
