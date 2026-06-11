"""115 client wrapper — manages P115Client lifecycle and cookie encryption."""
import asyncio
import base64
import logging
from typing import Any
import httpx
from p115client import P115Client

logger = logging.getLogger(__name__)

# Global client reference (set after login)
_client: P115Client | None = None
_uid: str | None = None
_event_last_id: str | None = None


def get_client() -> P115Client | None:
    """Return the current P115Client instance."""
    return _client


def set_client(client: P115Client, uid: str | None = None) -> None:
    """Set the global P115Client instance."""
    global _client, _uid
    _client = client
    _uid = uid


def clear_client() -> None:
    """Clear the global client (logout)."""
    global _client, _uid, _event_last_id
    _client = None
    _uid = None
    _event_last_id = None


def get_uid() -> str | None:
    return _uid


async def create_client_from_cookie(cookie: str) -> P115Client:
    """Create and verify a P115Client from a raw cookie string.

    Constructs the client directly, then verifies with login_status.
    Avoids ensure_cookies=True which triggers QR-code login on failure.
    """
    client = P115Client(cookie)
    is_valid = await client.login_status(async_=True, timeout=10.0)
    if not is_valid:
        raise ValueError("Invalid or expired 115 cookie")
    return client


async def validate_client(client: P115Client | None = None) -> bool:
    """Validate whether the current (or provided) P115Client cookie is still valid.

    If invalid, clears the global client so subsequent calls know we are logged out.
    """
    if client is None:
        client = _client
    if client is None:
        return False
    try:
        is_valid = await client.login_status(async_=True, timeout=10.0)
        if not is_valid:
            logger.warning("115 client cookie expired or invalid, clearing client")
            clear_client()
        return bool(is_valid)
    except Exception as e:
        logger.warning("validate_client failed: %s", e)
        clear_client()
        return False


async def get_user_info(client: P115Client) -> dict[str, Any]:
    """Get user account info from 115."""
    uid = client.user_id or 0

    username = ""
    try:
        info = await client.user_info(async_=True, timeout=10.0)
        if isinstance(info, dict):
            data = info.get("data", info)
            username = str(data.get("user_name") or data.get("nick_name") or data.get("user_id", ""))
    except Exception as e:
        logger.warning("user_info failed: %s", e)
        # If auth-related error, invalidate client
        if "login" in str(e).lower() or "auth" in str(e).lower() or "invalid" in str(e).lower():
            clear_client()
        raise

    total_space = 0
    used_space = 0
    try:
        resp = await client.fs_index_info(0, async_=True, timeout=10.0)
        if isinstance(resp, dict):
            space = resp.get("data", {}).get("space_info", {})
            total_space = int(space.get("all_total", {}).get("size", 0))
            used_space = int(space.get("all_use", {}).get("size", 0))
    except Exception as e:
        logger.warning("fs_index_info failed: %s", e)

    return {
        "uid": uid,
        "user_name": username,
        "total_space": total_space,
        "used_space": used_space,
    }


def encrypt_cookie(cookie: str) -> str:
    """Encode a cookie string for storage (base64)."""
    return base64.b64encode(cookie.encode("utf-8")).decode("ascii")


def decrypt_cookie(encrypted: str) -> str:
    """Decode a stored cookie string (base64)."""
    return base64.b64decode(encrypted.encode("ascii")).decode("utf-8")



async def init_client_from_db() -> P115Client | None:
    """Load the first valid 115 account from DB and create a P115Client.

    Called at application startup. Returns None if no stored cookie or if
    the cookie is invalid.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.account import Account115

    try:
        async with async_session_factory() as session:
            result = await session.execute(select(Account115).limit(1))
            account = result.scalar_one_or_none()
            if not account or not account.cookie:
                logger.info("No stored 115 account found at startup")
                return None

            cookie = decrypt_cookie(account.cookie)
            client = await create_client_from_cookie(cookie)
            set_client(client, account.uid)
            logger.info("Restored 115 client from stored cookie (uid=%s)", account.uid)
            return client
    except (asyncio.TimeoutError, TimeoutError):
        logger.warning("115 client init timed out at startup")
        return None
    except ValueError:
        # Invalid or expired cookie — expected, user needs to re-login
        logger.warning("Stored 115 cookie is invalid or expired, please re-login")
        return None
    except Exception:
        # Unexpected error — log at ERROR level so it's visible
        logger.exception("Unexpected error restoring 115 client from DB")
        return None


# QR code login helpers (using p115client)
async def get_qrcode_token() -> dict[str, Any]:
    """Generate a QR code token for 115 login.

    Returns dict with keys: 'uid' (str), 'time' (int), 'sign' (str),
    plus 'qrcode_url' (str) — the scan URL for the 115 app,
    and 'qrcode_img_url' (str) — the QR image download URL.
    Raises RuntimeError if generation fails.
    """
    from p115client import P115Client
    try:
        result = await P115Client.login_qrcode_token(app="web", async_=True)
        if not isinstance(result, dict) or not result.get("state"):
            raise RuntimeError(f"Invalid response: {result}")
        data = result["data"]
        uid = data["uid"]
        data["qrcode_url"] = f"https://115.com/scan/dg-{uid}"
        data["qrcode_img_url"] = f"https://qrcodeapi.115.com/api/1.0/web/1.0/qrcode?uid={uid}"
        return data
    except Exception as e:
        raise RuntimeError(f"Failed to generate QR code token: {e}")


async def check_qrcode_status(uid: str, time: int | str | None = None, sign: str | None = None) -> dict[str, Any]:
    """Check the status of a QR code login.

    Args:
        uid: The 'uid' value returned by get_qrcode_token().
        time: The 'time' value from get_qrcode_token (required by 115 API).
        sign: The 'sign' value from get_qrcode_token (required by 115 API).

    Returns:
        dict with keys:
            'status' (str): 'scanning' | 'scanned' | 'confirmed' | 'expired'
            'cookies' (dict | None): available only when status='confirmed'
    """
    from p115client import P115Client

    try:
        payload = {"uid": uid}
        if time is not None:
            payload["time"] = time
        if sign is not None:
            payload["sign"] = sign
        result = await P115Client.login_qrcode_scan_status(payload, async_=True)
        if not isinstance(result, dict) or not result.get("state"):
            # 50199004 often means the QR code has been consumed or expired
            err_code = result.get("code") if isinstance(result, dict) else None
            if err_code == 50199004:
                return {"status": "expired", "error": "QR code expired or already used"}
            logger.warning("QR code status check returned invalid response: %s", result)
            return {"status": "scanning"}

        status_code = result.get("data", {}).get("status", 0)
        # status is numeric: 0=waiting, 1=scanned, 2=sigined, -1=expired
        if status_code == 2:  # sigined = user confirmed
            apps_to_try = (
                "web", "android", "115android", "qandroid",
                "ios", "115ios", "alipaymini", "wechatmini",
            )
            last_error = None
            for app in apps_to_try:
                try:
                    cookies_resp = await P115Client.login_qrcode_scan_result(uid, app=app, async_=True)
                    if isinstance(cookies_resp, dict) and cookies_resp.get("state"):
                        data = cookies_resp.get("data", {})
                        raw_cookie = data.get("cookie")
                        if data and raw_cookie:
                            # cookie may be returned as a dict of key-value pairs
                            if isinstance(raw_cookie, dict):
                                cookie_str = "; ".join(f"{k}={v}" for k, v in raw_cookie.items())
                                data["cookie"] = cookie_str
                            logger.info("QR login confirmed via app=%s", app)
                            return {"status": "confirmed", "cookies": data}
                except Exception as e:
                    last_error = str(e)[:200]
                    continue
            logger.warning(
                "QR login confirmed but qrcode_result failed for all apps: %s",
                last_error,
            )
            return {"status": "expired", "error": f"cookie extraction failed: {last_error}"}
        elif status_code == 1:
            return {"status": "scanned"}
        elif status_code == -1:
            return {"status": "expired"}
        elif status_code == -2:
            return {"status": "cancelled"}
        return {"status": "scanning"}
    except Exception as e:
        logger.warning("QR code status check failed: %s", e)
        return {"status": "scanning"}


async def reset_event_cursor() -> None:
    """Reset the 115 life event cursor, forcing a full re-sync on next poll."""
    global _event_last_id
    _event_last_id = None
