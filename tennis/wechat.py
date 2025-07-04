import os
import json
import asyncio
import httpx
import redis

from .config import get_wechat_appid, get_wechat_secret, get_redis_url
from .storage import consume_subscribe_quota, log_subscribe_error

TEMPLATE_ID = "uqaaIKXK918Yz4FGODyiuB4uJgMFkXC_63vTGq-0G2c_"

REDIS_URL = get_redis_url()
_redis = None
if REDIS_URL:
    try:
        _redis = redis.from_url(REDIS_URL)
    except Exception:
        _redis = None

TOKEN_KEY = "tennis:wx_token"


async def _get_access_token() -> str | None:
    """Return a cached WeChat access token or fetch a new one."""
    if _redis:
        try:
            token = _redis.get(TOKEN_KEY)
            if token:
                return token.decode() if isinstance(token, bytes) else token
        except Exception:
            pass

    appid = get_wechat_appid()
    secret = get_wechat_secret()
    if not appid or not secret:
        return None

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.weixin.qq.com/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": appid,
                    "secret": secret,
                },
                timeout=5,
            )
            data = resp.json()
        except Exception:
            return None

    token = data.get("access_token")
    if not token:
        return None
    expires = int(data.get("expires_in", 0))
    if _redis:
        try:
            _redis.setex(TOKEN_KEY, expires - 60, token)
        except Exception:
            pass
    return token


async def _send(openid: str, audit_type: str, audit_status: str, page: str) -> dict:
    token = await _get_access_token()
    if not token or not openid:
        return {"errcode": -1, "errmsg": "no token"}

    payload = {
        "touser": openid,
        "template_id": TEMPLATE_ID,
        "page": page,
        "data": {
            "thing18": {"value": audit_type[:20]},
            "thing17": {"value": audit_status[:20]},
        },
    }
    url = "https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token=" + token
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=5)
            result = resp.json()
    except Exception as exc:
        return {"errcode": -1, "errmsg": str(exc)}
    return result


def send_audit_message(user_id: str, openid: str, scene: str, audit_type: str, audit_status: str, page: str) -> None:
    """Send an audit result message and manage quota."""
    if not consume_subscribe_quota(user_id, scene):
        return
    data = asyncio.run(_send(openid, audit_type, audit_status, page))
    errcode = data.get("errcode", 0)
    if errcode == 0:
        return
    if errcode == 43101:
        log_subscribe_error(user_id, scene, errcode, data.get("errmsg", ""))
    elif errcode == 40001 and _redis:
        try:
            _redis.delete(TOKEN_KEY)
        except Exception:
            pass
    else:
        log_subscribe_error(user_id, scene, errcode, data.get("errmsg", ""))
