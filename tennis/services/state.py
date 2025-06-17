from __future__ import annotations
import datetime
from .. import storage

# reset caches when state module is reloaded (test setup)
storage.invalidate_cache()

# ``TOKEN_TTL`` is retained for use by authentication helpers. Runtime data
# such as ``clubs`` or ``users`` used to live in this module but are now loaded
# directly by callers from the storage layer.

TOKEN_TTL = datetime.timedelta(hours=24)
