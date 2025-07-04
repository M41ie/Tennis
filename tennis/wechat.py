import json
import time
import urllib.request
import urllib.parse

from .config import get_wechat_appid, get_wechat_secret

TEMPLATE_ID = "uqaaIKXK918Yz4FGODyiuB4uJgMFkXC_63vTGq-0G2c_"

_ACCESS_TOKEN = None
_EXPIRES_AT = 0.0


def _get_access_token() -> str | None:
    """Return a cached WeChat access token or fetch a new one."""
    global _ACCESS_TOKEN, _EXPIRES_AT
    if _ACCESS_TOKEN and time.time() < _EXPIRES_AT:
        return _ACCESS_TOKEN

    appid = get_wechat_appid()
    secret = get_wechat_secret()
    if not appid or not secret:
        return None

    params = urllib.parse.urlencode({
        "grant_type": "client_credential",
        "appid": appid,
        "secret": secret,
    })
    try:
        with urllib.request.urlopen(
            "https://api.weixin.qq.com/cgi-bin/token?" + params
        ) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return None

    token = data.get("access_token")
    if not token:
        return None
    expires = int(data.get("expires_in", 0))
    _ACCESS_TOKEN = token
    _EXPIRES_AT = time.time() + expires - 60
    return token


def send_audit_message(openid: str, audit_type: str, audit_status: str, page: str) -> None:
    """Send an audit result subscription message if credentials are available."""
    token = _get_access_token()
    if not token or not openid:
        return

    payload = {
        "touser": openid,
        "template_id": TEMPLATE_ID,
        "page": page,
        "data": {
            "thing18": {"value": audit_type[:20]},
            "thing17": {"value": audit_status[:20]},
        },
    }
    url = (
        "https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token="
        + token
    )
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            resp.read()
    except Exception:
        pass
