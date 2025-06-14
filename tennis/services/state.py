from __future__ import annotations
import datetime
import json
from pathlib import Path
import tennis.storage as storage
from ..storage import load_data, load_users

# persistent data
clubs = load_data()
users = load_users()
if "A" in users:
    users["A"].is_sys_admin = True

# token persistence
TOKENS_FILE = Path(str(storage.DB_FILE)).with_name("tokens.json")
TOKEN_TTL = datetime.timedelta(hours=24)

def _load_tokens() -> dict[str, tuple[str, datetime.datetime]]:
    try:
        text = TOKENS_FILE.read_text()
    except FileNotFoundError:
        return {}
    except OSError:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    now = datetime.datetime.utcnow()
    result: dict[str, tuple[str, datetime.datetime]] = {}
    for tok, (uid, ts) in data.items():
        ts_dt = datetime.datetime.fromisoformat(ts)
        if now - ts_dt < TOKEN_TTL:
            result[tok] = (uid, ts_dt)
    return result

def _save_tokens() -> None:
    try:
        TOKENS_FILE.write_text(
            json.dumps({t: (uid, ts.isoformat()) for t, (uid, ts) in tokens.items()})
        )
    except OSError:
        pass

# load tokens on import
tokens: dict[str, tuple[str, datetime.datetime]] = _load_tokens()
