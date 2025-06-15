from __future__ import annotations
import datetime
import tennis.storage as storage
from ..storage import load_data, load_users

# persistent data
clubs = load_data()
users = load_users()
if "A" in users:
    users["A"].is_sys_admin = True

TOKEN_TTL = datetime.timedelta(hours=24)

# token state is now stored in the database; these helpers remain for
# backward compatibility but do nothing.

def _save_tokens() -> None:
    """Deprecated: token persistence handled by storage layer."""
    pass

tokens: dict[str, tuple[str, datetime.datetime]] = {}
