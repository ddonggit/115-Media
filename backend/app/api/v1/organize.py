"""Organize API — unrecognized files, rule CRUD, organize config."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from app.core.database import async_session_factory
from app.core.security import get_current_user
from app.models.media_file import MediaFile
from app.models.organize_rule import OrganizeRule
from app.models.organize_config import OrganizeConfig
from app.schemas.media_file import MediaFileResponse
from app.schemas.organize_rule import OrganizeRuleCreate, OrganizeRuleUpdate, OrganizeRuleResponse
from app.schemas.organize_config import OrganizeConfigCreate, OrganizeConfigUpdate, OrganizeConfigResponse

router = APIRouter(prefix="/organize", tags=["organize"])


# ── Organize Records ──────────────────────────────────────────────


@router.get("/records", response_model=list[MediaFileResponse])
async def list_organize_records(
    q: str | None = Query(None, description="Search by file name"),
    limit: int = Query(100, ge=1, le=500),
    auth=Depends(get_current_user),
):
    """List organize records (both success and failure), with optional search."""
    async with async_session_factory() as session:
        stmt = select(MediaFile).where(
            or_(
                MediaFile.organized == True,
                MediaFile.retry_count > 0,
                MediaFile.recognized == True,
            )
        )
        if q:
            stmt = stmt.where(MediaFile.file_name.ilike(f'%{q}%'))
        stmt = stmt.order_by(MediaFile.updated_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()


# ── Unrecognized Files ────────────────────────────────────────────


@router.get("/unrecognized", response_model=list[MediaFileResponse])
async def list_unrecognized(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(
            select(MediaFile).where(MediaFile.recognized == False).order_by(MediaFile.created_at.desc())
        )
        return result.scalars().all()


@router.post("/fix/{file_id}", response_model=MediaFileResponse)
async def fix_file(file_id: int, tmdb_id: int = Query(...), auth=Depends(get_current_user)):
    """Manually set tmdb_id for an unrecognized file."""
    async with async_session_factory() as session:
        result = await session.execute(select(MediaFile).where(MediaFile.id == file_id))
        file_ = result.scalar_one_or_none()
        if not file_:
            raise HTTPException(status_code=404, detail="File not found")
        file_.tmdb_id = tmdb_id
        file_.recognized = True
        await session.commit()
        return file_


# ── Organize Rules ────────────────────────────────────────────────


@router.get("/rules", response_model=list[OrganizeRuleResponse])
async def list_rules(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(
            select(OrganizeRule).order_by(OrganizeRule.priority)
        )
        return result.scalars().all()


@router.post("/rules", response_model=OrganizeRuleResponse, status_code=201)
async def create_rule(data: OrganizeRuleCreate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        rule = OrganizeRule(**data.model_dump())
        session.add(rule)
        await session.commit()
        return rule


@router.put("/rules/{rule_id}", response_model=OrganizeRuleResponse)
async def update_rule(rule_id: int, data: OrganizeRuleUpdate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(OrganizeRule).where(OrganizeRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(rule, key, val)
        await session.commit()
        return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(OrganizeRule).where(OrganizeRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        await session.delete(rule)
        await session.commit()
        return {"message": "deleted"}


@router.post("/reorder")
async def reorder_rules(rule_ids: list[int], auth=Depends(get_current_user)):
    """Reorder rules by submitting a list of rule IDs in desired priority order."""
    async with async_session_factory() as session:
        for idx, rid in enumerate(rule_ids):
            result = await session.execute(select(OrganizeRule).where(OrganizeRule.id == rid))
            rule = result.scalar_one_or_none()
            if rule:
                rule.priority = idx
        await session.commit()
        return {"message": "reordered"}


@router.post("/start")
async def start_organize(rule_id: int | None = Query(None), auth=Depends(get_current_user)):
    """Trigger organize task with optional rule filter (SPEC-compliant)."""
    try:
        from app.core.celery_app import celery_app
        celery_app.send_task("app.tasks.organize.organize_task", args=[rule_id] if rule_id else [])
    except Exception:
        pass
    from app.services.log_service import log_action
    await log_action(action="start_organize", module="organize", detail=f"整理任务已加入队列, rule_id={rule_id}")
    return {"message": "organize task queued", "rule_id": rule_id}


@router.post("/run")
async def run_organize(auth=Depends(get_current_user)):
    """Trigger organize task manually."""
    try:
        from app.core.celery_app import celery_app
        celery_app.send_task("app.tasks.organize.organize_task")
    except Exception:
        pass
    from app.services.log_service import log_action
    await log_action(action="run_organize", module="organize", detail="整理任务已加入队列")
    return {"message": "organize task queued"}


# ── Organize Config ───────────────────────────────────────────────


@router.get("/config", response_model=OrganizeConfigResponse | None)
async def get_organize_config(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(OrganizeConfig).limit(1))
        return result.scalar_one_or_none()


@router.post("/config", response_model=OrganizeConfigResponse)
async def save_organize_config(data: OrganizeConfigCreate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(OrganizeConfig).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            for key, val in data.model_dump().items():
                setattr(existing, key, val)
        else:
            config = OrganizeConfig(**data.model_dump())
            session.add(config)
        await session.commit()
        return existing or config
