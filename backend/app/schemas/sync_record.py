"""SyncRecord Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class SyncRecordCreate(BaseModel):
    type: str = Field(..., pattern="^(full|incremental)$")
    status: str = "running"
    total_files: int = 0


class SyncRecordUpdate(BaseModel):
    status: str | None = Field(None, pattern="^(running|completed|interrupted)$")
    progress: int | None = Field(None, ge=0, le=100)
    checkpoint_cid: str | None = None
    current_path: str | None = None
    scanned_files: int | None = None
    errors: str | None = None
    can_resume: bool | None = None
    finished_at: datetime | None = None


class SyncRecordResponse(BaseModel):
    id: int
    type: str
    status: str
    progress: int
    started_at: datetime
    finished_at: datetime | None
    checkpoint_cid: str | None
    current_path: str | None
    total_files: int
    scanned_files: int
    errors: str | None
    can_resume: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("errors", mode="before")
    @classmethod
    def coerce_errors(cls, v):
        """Accept list[str] from JSON column or str from JSON string."""
        if isinstance(v, list):
            return ",".join(v) if v else None
        return v

    class Config:
        from_attributes = True