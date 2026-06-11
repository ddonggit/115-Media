"""Auth API — login, token refresh, user info."""
import logging
import os
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

# Admin credentials: username from ADMIN_USER env, password from ADMIN_PASSWORD env.
# Defaults are insecure and should be changed via env vars in production.
_ADMIN_USER = os.getenv("ADMIN_USER", "admin")
_ADMIN_PASS_HASH = hash_password(os.getenv("ADMIN_PASSWORD", "admin123"))


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class CookieLoginRequest(BaseModel):
    cookie: str = Field(..., min_length=1, description="Raw 115 cookie string")


@router.post("/login")
async def login(body: LoginRequest):
    """Username/password login returning JWT token."""
    if body.username != _ADMIN_USER or not verify_password(body.password, _ADMIN_PASS_HASH):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": body.username, "role": "admin"})
    from app.services.log_service import log_action
    await log_action(action="login", module="auth", detail=f"用户登录: {body.username}")
    return {"data": {"token": token, "username": body.username}, "message": "ok"}


@router.post("/cookie")
async def cookie_login(body: CookieLoginRequest):
    """Login with 115 cookie string.

    Creates a P115Client from the raw cookie, verifies it, encrypts and stores
    the cookie in the Account115 table, then returns a JWT token.
    """
    from app.core.p115_wrapper import (
        create_client_from_cookie,
        set_client,
        encrypt_cookie,
        get_user_info,
    )
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.account import Account115

    try:
        client = await create_client_from_cookie(body.cookie)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid 115 cookie: {e}",
        )

    # Get user info from 115
    try:
        user_info = await get_user_info(client)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to verify 115 account: {e}",
        )

    uid = str(user_info.get("uid", ""))
    username = user_info.get("user_name", "")
    total_space = user_info.get("total_space", 0)
    used_space = user_info.get("used_space", 0)

    # Encrypt and store in DB (upsert)
    encrypted = encrypt_cookie(body.cookie)
    async with async_session_factory() as session:
        result = await session.execute(select(Account115).limit(1))
        account = result.scalar_one_or_none()
        if account:
            account.cookie = encrypted
            account.uid = uid
            account.username = username
            account.total_space = total_space
            account.used_space = used_space
        else:
            account = Account115(
                cookie=encrypted,
                uid=uid,
                username=username,
                total_space=total_space,
                used_space=used_space,
            )
            session.add(account)
        await session.commit()

    # Set the global client
    set_client(client, uid)

    token = create_access_token({"sub": username, "role": "admin", "uid": uid})
    from app.services.log_service import log_action
    await log_action(action="cookie_login", module="auth", detail=f"Cookie 登录: uid={uid}, {username}")
    return {
        "data": {
            "token": token,
            "username": username,
            "uid": uid,
            "total_space": total_space,
            "used_space": used_space,
        },
        "message": "ok",
    }


@router.get("/qrcode")
async def get_qrcode():
    """Generate a QR code token for 115 scan login.

    Returns a token (for polling) and a QR image base64 string.
    """
    from app.core.p115_wrapper import get_qrcode_token

    try:
        result = await get_qrcode_token()
        return {"data": result, "message": "ok"}
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/qrcode/status")
async def qrcode_status(uid: str, time: int | None = None, sign: str | None = None):
    """Check the QR code login status (short poll).

    Returns immediately with current status:
    'scanning' | 'scanned' | 'confirmed' | 'expired' | 'cancelled'.
    When status='confirmed', automatically stores the cookie and issues JWT.
    """
    from app.core.p115_wrapper import (
        check_qrcode_status,
        create_client_from_cookie,
        set_client,
        encrypt_cookie,
        get_user_info,
    )
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.account import Account115

    result = await check_qrcode_status(uid, time, sign)
    status = result["status"]

    if status in ("scanning", "scanned", "cancelled", "expired"):
        return {"data": {"status": status, "error": result.get("error")}}

    if status != "confirmed":
        return {"data": {"status": "expired", "error": "unknown status"}}

    # confirmed: verify cookie, save to DB, issue JWT
    cookies = result.get("cookies", {})
    if isinstance(cookies, dict):
        raw_cookie = cookies.get("cookie")
        if isinstance(raw_cookie, dict):
            cookie_str = "; ".join(f"{k}={v}" for k, v in raw_cookie.items())
        else:
            cookie_str = raw_cookie or ""
    else:
        cookie_str = str(cookies)
    if not cookie_str:
        logger.warning("QR confirmed but no cookie in result")
        return {"data": {"status": "expired", "error": "cookie extraction failed"}}

    try:
        client = await create_client_from_cookie(cookie_str)
        user_info = await get_user_info(client)
    except Exception as e:
        logger.warning("QR: verified confirmed cookie failed: %s", e)
        return {"data": {"status": "expired", "error": f"cookie verification failed: {e}"}}

    new_uid = str(user_info.get("uid", ""))
    username = user_info.get("user_name", "")
    total_space = user_info.get("total_space", 0)
    used_space = user_info.get("used_space", 0)

    encrypted = encrypt_cookie(cookie_str)
    async with async_session_factory() as session:
        db_result = await session.execute(select(Account115).limit(1))
        account = db_result.scalar_one_or_none()
        if account:
            account.cookie = encrypted
            account.uid = new_uid
            account.username = username
            account.total_space = total_space
            account.used_space = used_space
        else:
            account = Account115(
                cookie=encrypted, uid=new_uid, username=username,
                total_space=total_space, used_space=used_space,
            )
            session.add(account)
        await session.commit()

    set_client(client, new_uid)
    jwt_token = create_access_token({"sub": username, "role": "admin", "uid": new_uid})

    return {
        "data": {
            "status": "confirmed",
            "token": jwt_token,
            "username": username,
            "uid": new_uid,
            "total_space": total_space,
            "used_space": used_space,
        },
        "message": "ok",
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return current user info from JWT, validating 115 cookie freshness."""
    from app.core.p115_wrapper import get_client, get_user_info, validate_client

    # Validate 115 client cookie first
    client = get_client()
    if client:
        is_valid = await validate_client(client)
        if not is_valid:
            client = None

    result = {
        "username": current_user.get("sub"),
        "role": current_user.get("role"),
    }

    if client:
        try:
            info = await get_user_info(client)
            result["uid"] = str(info.get("uid", ""))
            result["total_space"] = info.get("total_space", 0)
            result["used_space"] = info.get("used_space", 0)
        except Exception:
            pass

    return {"data": result}


@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Issue a new token."""
    new_token = create_access_token(current_user)
    return {"data": {"token": new_token}, "message": "ok"}


@router.get("/status")
async def auth_status(current_user: dict = Depends(get_current_user)):
    """Return current auth status: logged_in, username, cookie expire_time.

    Also validates the 115 cookie in real time so the frontend can detect expiry.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.account import Account115
    from app.core.p115_wrapper import get_client, validate_client

    # Validate 115 client cookie in real time
    client = get_client()
    cookie_valid = False
    if client:
        cookie_valid = await validate_client(client)

    result = {
        "logged_in": bool(current_user) and cookie_valid,
        "username": current_user.get("sub", "") if current_user else "",
    }
    async with async_session_factory() as session:
        db_result = await session.execute(select(Account115).limit(1))
        account = db_result.scalar_one_or_none()
        if account:
            result["expire_time"] = account.expire_time.isoformat() if account.expire_time else None
        else:
            result["expire_time"] = None
    return {"data": result}
