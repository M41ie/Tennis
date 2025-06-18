import json
import datetime
import pickle
import sqlite3
from pathlib import Path
from typing import Dict, Generator
from contextlib import contextmanager
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras


from .config import (
    DB_FILE,
    get_database_url,
    get_redis_url,
    get_cache_ttl,
)


# Absolute path to the repository root database file. Using a fixed location
# ensures scripts behave the same regardless of the working directory.
# ``DB_FILE`` is imported from ``tennis.config`` so tests can monkeypatch it.
DATABASE_URL = get_database_url()
IS_PG = DATABASE_URL.startswith("postgres")

# Optional Redis cache
REDIS_URL = get_redis_url()
CACHE_TTL = get_cache_ttl()
_redis = None
if REDIS_URL:
    try:
        import redis  # type: ignore
        _redis = redis.from_url(REDIS_URL)
    except Exception:
        _redis = None


class _PgCursor:
    def __init__(self, cursor):
        self._c = cursor

    def execute(self, query, params=None):
        q = query.replace("?", "%s")
        self._c.execute(q, params or [])
        return self

    def executemany(self, query, seq):
        q = query.replace("?", "%s")
        self._c.executemany(q, seq)
        return self

    def fetchone(self):
        return self._c.fetchone()

    def fetchall(self):
        return self._c.fetchall()

    def __iter__(self):
        return iter(self._c)

    def __getattr__(self, name):
        return getattr(self._c, name)


class _PgConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, *a, **kw):
        return _PgCursor(self._conn.cursor(*a, **kw))

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)

# track which database file the caches were loaded from
_db_file: Path | None = None

from .models import (
    Player,
    Club,
    Match,
    DoublesMatch,
    User,
    Appointment,
    Message,
    JoinApplication,
    players,
)

# in-memory store used when loading player data
_players_cache: Dict[str, Player] = {}
# caches for loaded clubs and users
_clubs_cache: Dict[str, Club] | None = None
_users_cache: Dict[str, User] | None = None

# pending objects to refresh after a transactional commit
_pending_clubs: Dict[str, Club | None] = {}
_pending_users: Dict[str, User | None] = {}
_pending_players: Dict[str, Player | None] = {}


def _load_cache(key: str):
    if not _redis:
        return None
    try:
        data = _redis.get(key)
        if data is not None:
            return pickle.loads(data)
    except Exception:
        return None
    return None


def _save_cache(key: str, value: object) -> None:
    if not _redis:
        return
    try:
        _redis.setex(key, CACHE_TTL, pickle.dumps(value))
    except Exception:
        pass


def _refresh_after_write() -> None:
    """Flush pending objects to the in-memory and Redis caches."""
    for club_id, club in list(_pending_clubs.items()):
        if club is None:
            _clubs_cache.pop(club_id, None)
            if _redis:
                try:
                    _redis.delete(f"tennis:club:{club_id}")
                except Exception:
                    pass
        else:
            set_club(club)
    for user_id, user in list(_pending_users.items()):
        if user is None:
            if _users_cache is not None:
                _users_cache.pop(user_id, None)
            if _redis:
                try:
                    _redis.delete(f"tennis:user:{user_id}")
                except Exception:
                    pass
        else:
            set_user(user)
    for pid, player in list(_pending_players.items()):
        if player is None:
            _players_cache.pop(pid, None)
            if _redis:
                try:
                    _redis.delete(f"tennis:player:{pid}")
                except Exception:
                    pass
        else:
            set_player(player)

    _pending_clubs.clear()
    _pending_users.clear()
    _pending_players.clear()


def invalidate_cache() -> None:
    """Clear cached club, user and player data."""
    global _clubs_cache, _users_cache, _db_file
    _clubs_cache = None
    _users_cache = None
    _players_cache.clear()
    _db_file = None


def _connect():
    """Return a DB connection based on ``DATABASE_URL``."""
    if IS_PG:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        _init_schema(conn)
        return _PgConnection(conn)
    else:
        path = DB_FILE
        if DATABASE_URL.startswith("sqlite://"):
            path = Path(urlparse(DATABASE_URL).path)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        _init_schema(conn)
        return conn


@contextmanager
def transaction() -> Generator[object, None, None]:
    """Context manager yielding a connection with an active transaction."""
    conn = _connect()
    assert not (_pending_clubs or _pending_users or _pending_players)
    try:
        yield conn
        conn.commit()
        _refresh_after_write()
    except Exception:
        conn.rollback()
        _pending_clubs.clear()
        _pending_users.clear()
        _pending_players.clear()
        raise
    finally:
        conn.close()


def _init_schema(conn) -> None:
    cur = conn.cursor()
    if IS_PG:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS clubs (club_id TEXT PRIMARY KEY, name TEXT, logo TEXT, region TEXT, slogan TEXT)"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            password_hash TEXT,
            wechat_openid TEXT,
            can_create_club INTEGER DEFAULT 1,
            is_sys_admin INTEGER DEFAULT 0,
            created_clubs INTEGER DEFAULT 0,
            joined_clubs INTEGER DEFAULT 0,
            max_creatable_clubs INTEGER DEFAULT 0,
            max_joinable_clubs INTEGER DEFAULT 5
        )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            singles_rating REAL,
            doubles_rating REAL,
            experience REAL,
            pre_ratings JSONB,
            age INTEGER,
            gender TEXT,
            avatar TEXT,
            birth TEXT,
            handedness TEXT,
            backhand TEXT,
            region TEXT,
            joined TEXT
        )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS club_members (
            club_id TEXT,
            user_id TEXT,
            PRIMARY KEY (club_id, user_id)
        )"""
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS matches (id SERIAL PRIMARY KEY, club_id TEXT, type TEXT, date TEXT, data JSONB)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS pending_matches (id SERIAL PRIMARY KEY, club_id TEXT, type TEXT, date TEXT, data JSONB)"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            club_id TEXT,
            date TEXT,
            creator TEXT,
            location TEXT,
            info TEXT,
            signups JSONB
        )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS club_meta (
            club_id TEXT PRIMARY KEY,
            banned_ids JSONB,
            leader_id TEXT,
            admin_ids JSONB,
            pending_members JSONB,
            rejected_members JSONB
        )"""
        )
    else:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS clubs (club_id TEXT PRIMARY KEY, name TEXT, logo TEXT, region TEXT, slogan TEXT)"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            password_hash TEXT,
            wechat_openid TEXT,
            can_create_club INTEGER DEFAULT 1,
            is_sys_admin INTEGER DEFAULT 0,
            created_clubs INTEGER DEFAULT 0,
            joined_clubs INTEGER DEFAULT 0,
            max_creatable_clubs INTEGER DEFAULT 0,
            max_joinable_clubs INTEGER DEFAULT 5
        )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            singles_rating REAL,
            doubles_rating REAL,
            experience REAL,
            pre_ratings TEXT,
            age INTEGER,
            gender TEXT,
            avatar TEXT,
            birth TEXT,
            handedness TEXT,
            backhand TEXT,
            region TEXT,
            joined TEXT
        )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS club_members (
            club_id TEXT,
            user_id TEXT,
            PRIMARY KEY (club_id, user_id)
        )"""
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY AUTOINCREMENT, club_id TEXT, type TEXT, date TEXT, data TEXT)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS pending_matches (id INTEGER PRIMARY KEY AUTOINCREMENT, club_id TEXT, type TEXT, date TEXT, data TEXT)"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id TEXT,
            date TEXT,
            creator TEXT,
            location TEXT,
            info TEXT,
            signups TEXT
        )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS club_meta (
            club_id TEXT PRIMARY KEY,
            banned_ids TEXT,
            leader_id TEXT,
            admin_ids TEXT,
            pending_members TEXT,
            rejected_members TEXT
        )"""
        )
    # add new columns if an older database is missing them
    if not IS_PG:
        cols = {row[1] for row in cur.execute("PRAGMA table_info('clubs')")}
        if 'slogan' not in cols:
            cur.execute("ALTER TABLE clubs ADD COLUMN slogan TEXT")
        cols = {row[1] for row in cur.execute("PRAGMA table_info('users')")}
        if 'is_sys_admin' not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN is_sys_admin INTEGER DEFAULT 0")
        if 'max_creatable_clubs' not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN max_creatable_clubs INTEGER DEFAULT 0")
        if 'max_joinable_clubs' not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN max_joinable_clubs INTEGER DEFAULT 5")
        cols = {row[1] for row in cur.execute("PRAGMA table_info('club_meta')")}
        if 'leader_id' not in cols:
            cur.execute("ALTER TABLE club_meta ADD COLUMN leader_id TEXT")
        if 'admin_ids' not in cols:
            cur.execute("ALTER TABLE club_meta ADD COLUMN admin_ids TEXT")
        if 'pending_members' not in cols:
            cur.execute("ALTER TABLE club_meta ADD COLUMN pending_members TEXT")
        if 'rejected_members' not in cols:
            cur.execute("ALTER TABLE club_meta ADD COLUMN rejected_members TEXT")
        cols = {row[1] for row in cur.execute("PRAGMA table_info('players')")}
        if 'birth' not in cols:
            cur.execute("ALTER TABLE players ADD COLUMN birth TEXT")
        if 'handedness' not in cols:
            cur.execute("ALTER TABLE players ADD COLUMN handedness TEXT")
        if 'backhand' not in cols:
            cur.execute("ALTER TABLE players ADD COLUMN backhand TEXT")
        if 'region' not in cols:
            cur.execute("ALTER TABLE players ADD COLUMN region TEXT")
        if 'joined' not in cols:
            cur.execute("ALTER TABLE players ADD COLUMN joined TEXT")
    cur.execute(
        """CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        date TEXT,
        text TEXT,
        read INTEGER
    )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS auth_tokens (
        token TEXT PRIMARY KEY,
        user_id TEXT,
        ts TEXT
    )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS refresh_tokens (
        user_id TEXT PRIMARY KEY,
        token TEXT,
        expires TEXT
    )"""
    )
    conn.commit()


def load_data() -> tuple[Dict[str, Club], Dict[str, Player]]:
    """Load all clubs and players, using cached data when available."""
    global _clubs_cache, _db_file
    if _clubs_cache is not None and _db_file == DATABASE_URL:
        return _clubs_cache, _players_cache
    if _redis:
        cached = _load_cache("tennis:data")
        if cached:
            _clubs_cache, _players_cache = cached
            _db_file = DATABASE_URL
            return _clubs_cache, _players_cache
    _db_file = DATABASE_URL

    conn = _connect()
    cur = conn.cursor()
    from .cli import normalize_gender
    clubs: Dict[str, Club] = {}
    players = _players_cache
    players.clear()
    for row in cur.execute("SELECT * FROM clubs"):
        clubs[row["club_id"]] = Club(
            club_id=row["club_id"],
            name=row["name"],
            logo=row["logo"],
            region=row["region"],
            slogan=row["slogan"],
        )

    for row in cur.execute("SELECT * FROM club_meta"):
        club = clubs.get(row["club_id"])
        if not club:
            continue
        club.banned_ids.update(json.loads(row["banned_ids"] or "[]"))
        club.leader_id = row["leader_id"]
        club.admin_ids.update(json.loads(row["admin_ids"] or "[]"))
        pending = json.loads(row["pending_members"] or "{}")
        for uid, info in pending.items():
            club.pending_members[uid] = JoinApplication(
                reason=info.get("reason"),
                singles_rating=info.get("singles_rating"),
                doubles_rating=info.get("doubles_rating"),
            )
        rejected = json.loads(row["rejected_members"] or "{}")
        club.rejected_members.update(rejected)

    for row in cur.execute("SELECT * FROM players"):
        p = Player(
            user_id=row["user_id"],
            name=row["name"],
            singles_rating=row["singles_rating"],
            doubles_rating=row["doubles_rating"],
            experience=row["experience"],
            age=row["age"],
            gender=normalize_gender(row["gender"]),
            avatar=row["avatar"],
            birth=row["birth"],
            handedness=row["handedness"],
            backhand=row["backhand"],
            region=row["region"],
            joined=datetime.date.fromisoformat(row["joined"]) if row["joined"] else datetime.date.today(),
        )
        p.pre_ratings.update(json.loads(row["pre_ratings"] or "{}"))
        players[p.user_id] = p

    for row in cur.execute("SELECT * FROM club_members"):
        club = clubs.get(row["club_id"])
        p = players.get(row["user_id"])
        if club and p:
            club.members[p.user_id] = p

    for row in cur.execute("SELECT * FROM matches ORDER BY id"):
        club = clubs.get(row["club_id"])
        if not club:
            continue
        data = json.loads(row["data"])
        date = datetime.date.fromisoformat(row["date"])
        created_ts_str = data.get("created_ts")
        created_ts = (
            datetime.datetime.fromisoformat(created_ts_str)
            if created_ts_str
            else datetime.datetime.combine(date, datetime.time())
        )
        if row["type"] == "doubles":
            pa1 = players[data["a1"]]
            pa2 = players[data["a2"]]
            pb1 = players[data["b1"]]
            pb2 = players[data["b2"]]
            match = DoublesMatch(
                date=date,
                player_a1=pa1,
                player_a2=pa2,
                player_b1=pb1,
                player_b2=pb2,
                score_a=data["score_a"],
                score_b=data["score_b"],
                format_weight=data.get("weight", 1.0),
                location=data.get("location"),
                format_name=data.get("format_name"),
            )
            match.created_ts = created_ts
            match.rating_a1_before = data.get("rating_a1_before")
            match.rating_a2_before = data.get("rating_a2_before")
            match.rating_b1_before = data.get("rating_b1_before")
            match.rating_b2_before = data.get("rating_b2_before")
            match.rating_a1_after = data.get("rating_a1_after")
            match.rating_a2_after = data.get("rating_a2_after")
            match.rating_b1_after = data.get("rating_b1_after")
            match.rating_b2_after = data.get("rating_b2_after")
            club.matches.append(match)
            pa1.doubles_matches.append(match)
            pa2.doubles_matches.append(match)
            pb1.doubles_matches.append(match)
            pb2.doubles_matches.append(match)
        else:
            pa = players[data["player_a"]]
            pb = players[data["player_b"]]
            match = Match(
                date=date,
                player_a=pa,
                player_b=pb,
                score_a=data["score_a"],
                score_b=data["score_b"],
                format_weight=data.get("weight", 1.0),
                location=data.get("location"),
                format_name=data.get("format_name"),
            )
            match.created_ts = created_ts
            match.rating_a_before = data.get("rating_a_before")
            match.rating_b_before = data.get("rating_b_before")
            match.rating_a_after = data.get("rating_a_after")
            match.rating_b_after = data.get("rating_b_after")
            club.matches.append(match)
            pa.singles_matches.append(match)
            pb.singles_matches.append(match)
    for row in cur.execute("SELECT * FROM pending_matches ORDER BY id"):
        club = clubs.get(row["club_id"])
        if not club:
            continue
        data = json.loads(row["data"])
        date = datetime.date.fromisoformat(row["date"])
        if row["type"] == "doubles":
            pa1 = players[data["a1"]]
            pa2 = players[data["a2"]]
            pb1 = players[data["b1"]]
            pb2 = players[data["b2"]]
            match = DoublesMatch(
                date=date,
                player_a1=pa1,
                player_a2=pa2,
                player_b1=pb1,
                player_b2=pb2,
                score_a=data["score_a"],
                score_b=data["score_b"],
                format_weight=data.get("weight", 1.0),
                location=data.get("location"),
                format_name=data.get("format_name"),
                initiator=data.get("initiator"),
            )
            match.confirmed_a = data.get("confirmed_a", False)
            match.confirmed_b = data.get("confirmed_b", False)
            if "created" in data:
                match.created = datetime.date.fromisoformat(data["created"])
            if "created_ts" in data:
                match.created_ts = datetime.datetime.fromisoformat(data["created_ts"])
            if data.get("confirmed_on"):
                match.confirmed_on = datetime.date.fromisoformat(data["confirmed_on"])
            match.status = data.get("status")
            if data.get("status_date"):
                match.status_date = datetime.date.fromisoformat(data["status_date"])
            club.pending_matches.append(match)
        else:
            pa = players[data["player_a"]]
            pb = players[data["player_b"]]
            match = Match(
                date=date,
                player_a=pa,
                player_b=pb,
                score_a=data["score_a"],
                score_b=data["score_b"],
                format_weight=data.get("weight", 1.0),
                location=data.get("location"),
                format_name=data.get("format_name"),
                initiator=data.get("initiator"),
            )
            match.confirmed_a = data.get("confirmed_a", False)
            match.confirmed_b = data.get("confirmed_b", False)
            if "created" in data:
                match.created = datetime.date.fromisoformat(data["created"])
            if "created_ts" in data:
                match.created_ts = datetime.datetime.fromisoformat(data["created_ts"])
            if data.get("confirmed_on"):
                match.confirmed_on = datetime.date.fromisoformat(data["confirmed_on"])
            match.status = data.get("status")
            if data.get("status_date"):
                match.status_date = datetime.date.fromisoformat(data["status_date"])
            club.pending_matches.append(match)
    for row in cur.execute("SELECT * FROM appointments ORDER BY id"):
        club = clubs.get(row["club_id"])
        if not club:
            continue
        appt = Appointment(
            date=datetime.date.fromisoformat(row["date"]),
            creator=row["creator"],
            location=row["location"],
            info=row["info"],
        )
        appt.signups.update(json.loads(row["signups"] or "[]"))
        club.appointments.append(appt)
    conn.close()
    _clubs_cache = clubs
    _save_cache("tennis:data", (clubs, players))
    return clubs, players


def save_data(clubs: Dict[str, Club]) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM clubs")
    cur.execute("DELETE FROM players")
    cur.execute("DELETE FROM club_members")
    cur.execute("DELETE FROM matches")
    cur.execute("DELETE FROM pending_matches")
    cur.execute("DELETE FROM appointments")
    cur.execute("DELETE FROM club_meta")
    for p in players.values():
        cur.execute(
            """INSERT INTO players
            (user_id, name, singles_rating, doubles_rating, experience, pre_ratings,
             age, gender, avatar, birth, handedness, backhand, region, joined)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                p.user_id,
                p.name,
                p.singles_rating,
                p.doubles_rating,
                p.experience,
                json.dumps(p.pre_ratings),
                p.age,
                p.gender,
                p.avatar,
                p.birth,
                p.handedness,
                p.backhand,
                p.region,
                p.joined.isoformat(),
            ),
        )

    for cid, club in clubs.items():
        cur.execute(
            "INSERT INTO clubs(club_id, name, logo, region, slogan) VALUES (?,?,?,?,?)",
            (cid, club.name, club.logo, club.region, club.slogan),
        )
        cur.execute(
            "INSERT INTO club_meta(club_id, banned_ids, leader_id, admin_ids, pending_members, rejected_members) VALUES (?,?,?,?,?,?)",
            (
                cid,
                json.dumps(list(club.banned_ids)),
                club.leader_id,
                json.dumps(list(club.admin_ids)),
                json.dumps({uid: vars(pm) for uid, pm in club.pending_members.items()}),
                json.dumps(club.rejected_members),
            ),
        )
        for uid in club.members:
            if IS_PG:
                cur.execute(
                    "INSERT INTO club_members(club_id, user_id) VALUES (?,?) ON CONFLICT DO NOTHING",
                    (cid, uid),
                )
            else:
                cur.execute(
                    "INSERT INTO club_members(club_id, user_id) VALUES (?,?)",
                    (cid, uid),
                )
        for m in club.matches:
            if isinstance(m, DoublesMatch):
                data = {
                    "a1": m.player_a1.user_id,
                    "a2": m.player_a2.user_id,
                    "b1": m.player_b1.user_id,
                    "b2": m.player_b2.user_id,
                    "score_a": m.score_a,
                    "score_b": m.score_b,
                    "weight": m.format_weight,
                    "location": m.location,
                    "format_name": m.format_name,
                    "rating_a1_before": m.rating_a1_before,
                    "rating_a2_before": m.rating_a2_before,
                    "rating_b1_before": m.rating_b1_before,
                    "rating_b2_before": m.rating_b2_before,
                    "rating_a1_after": m.rating_a1_after,
                    "rating_a2_after": m.rating_a2_after,
                    "rating_b1_after": m.rating_b1_after,
                    "rating_b2_after": m.rating_b2_after,
                    "created": m.created.isoformat(),
                    "created_ts": m.created_ts.isoformat(),
                }
                cur.execute(
                    "INSERT INTO matches(club_id, type, date, data) VALUES (?,?,?,?)",
                    (
                        cid,
                        "doubles",
                        m.date.isoformat(),
                        json.dumps(data),
                    ),
                )
            else:
                data = {
                    "player_a": m.player_a.user_id,
                    "player_b": m.player_b.user_id,
                    "score_a": m.score_a,
                    "score_b": m.score_b,
                    "weight": m.format_weight,
                    "location": m.location,
                    "format_name": m.format_name,
                    "rating_a_before": m.rating_a_before,
                    "rating_b_before": m.rating_b_before,
                    "rating_a_after": m.rating_a_after,
                    "rating_b_after": m.rating_b_after,
                    "created": m.created.isoformat(),
                    "created_ts": m.created_ts.isoformat(),
                }
                cur.execute(
                    "INSERT INTO matches(club_id, type, date, data) VALUES (?,?,?,?)",
                    (
                        cid,
                        "singles",
                        m.date.isoformat(),
                        json.dumps(data),
                    ),
                )
        for m in club.pending_matches:
            if isinstance(m, DoublesMatch):
                data = {
                    "a1": m.player_a1.user_id,
                    "a2": m.player_a2.user_id,
                    "b1": m.player_b1.user_id,
                    "b2": m.player_b2.user_id,
                    "score_a": m.score_a,
                    "score_b": m.score_b,
                    "weight": m.format_weight,
                    "location": m.location,
                    "format_name": m.format_name,
                    "initiator": m.initiator,
                    "confirmed_a": m.confirmed_a,
                    "confirmed_b": m.confirmed_b,
                    "created": m.created.isoformat(),
                    "created_ts": m.created_ts.isoformat(),
                    "confirmed_on": m.confirmed_on.isoformat() if m.confirmed_on else None,
                    "status": m.status,
                    "status_date": m.status_date.isoformat() if m.status_date else None,
                }
                cur.execute(
                    "INSERT INTO pending_matches(club_id, type, date, data) VALUES (?,?,?,?)",
                    (
                        cid,
                        "doubles",
                        m.date.isoformat(),
                        json.dumps(data),
                    ),
                )
            else:
                data = {
                    "player_a": m.player_a.user_id,
                    "player_b": m.player_b.user_id,
                    "score_a": m.score_a,
                    "score_b": m.score_b,
                    "weight": m.format_weight,
                    "location": m.location,
                    "format_name": m.format_name,
                    "initiator": m.initiator,
                    "confirmed_a": m.confirmed_a,
                    "confirmed_b": m.confirmed_b,
                    "created": m.created.isoformat(),
                    "created_ts": m.created_ts.isoformat(),
                    "confirmed_on": m.confirmed_on.isoformat() if m.confirmed_on else None,
                    "status": m.status,
                    "status_date": m.status_date.isoformat() if m.status_date else None,
                }
                cur.execute(
                    "INSERT INTO pending_matches(club_id, type, date, data) VALUES (?,?,?,?)",
                    (
                        cid,
                        "singles",
                        m.date.isoformat(),
                        json.dumps(data),
                    ),
                )
        for a in club.appointments:
            cur.execute(
                "INSERT INTO appointments(club_id, date, creator, location, info, signups) VALUES (?,?,?,?,?,?)",
                (
                    cid,
                    a.date.isoformat(),
                    a.creator,
                    a.location,
                    a.info,
                    json.dumps(list(a.signups)),
                ),
            )
    conn.commit()
    conn.close()
    for cid, club in clubs.items():
        _pending_clubs[cid] = club
        for p in club.members.values():
            _pending_players[p.user_id] = p
    _refresh_after_write()


def load_users() -> Dict[str, User]:
    """Load user accounts from the database using a cache."""
    global _users_cache, _db_file
    if _users_cache is not None and _db_file == DATABASE_URL:
        return _users_cache
    if _redis:
        cached = _load_cache("tennis:users")
        if cached:
            _users_cache = cached
            _db_file = DATABASE_URL
            return _users_cache
    _db_file = DATABASE_URL

    conn = _connect()
    cur = conn.cursor()
    users: Dict[str, User] = {}
    for row in cur.execute("SELECT * FROM users"):
        wechat_openid = None
        if "wechat_openid" in row.keys():
            wechat_openid = row["wechat_openid"]
        users[row["user_id"]] = User(
            user_id=row["user_id"],
            name=row["name"],
            password_hash=row["password_hash"],
            wechat_openid=wechat_openid,
            # ignore stored can_create_club flag; always load as True
            can_create_club=True,
            is_sys_admin=bool(row["is_sys_admin"]) if "is_sys_admin" in row.keys() else False,
            created_clubs=row["created_clubs"],
            joined_clubs=row["joined_clubs"],
            max_creatable_clubs=row["max_creatable_clubs"] if "max_creatable_clubs" in row.keys() else 0,
            max_joinable_clubs=row["max_joinable_clubs"] if "max_joinable_clubs" in row.keys() else 5,
        )
    for row in cur.execute("SELECT * FROM messages ORDER BY id"):
        msg = Message(
            date=datetime.date.fromisoformat(row["date"]),
            text=row["text"],
            read=bool(row["read"]),
        )
        user = users.get(row["user_id"])
        if user:
            user.messages.append(msg)
    conn.close()
    _users_cache = users
    _save_cache("tennis:users", users)
    return users


def save_users(users: Dict[str, User]) -> None:
    """Persist user accounts to the database."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM users")
    cur.execute("DELETE FROM messages")
    for u in users.values():
        cur.execute(
            "INSERT INTO users(user_id, name, password_hash, wechat_openid, can_create_club, is_sys_admin, created_clubs, joined_clubs, max_creatable_clubs, max_joinable_clubs) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                u.user_id,
                u.name,
                u.password_hash,
                u.wechat_openid,
                int(u.can_create_club),
                int(getattr(u, 'is_sys_admin', False)),
                u.created_clubs,
                u.joined_clubs,
                getattr(u, 'max_creatable_clubs', 0),
                getattr(u, 'max_joinable_clubs', 5),
            ),
        )
        for msg in u.messages:
            cur.execute(
                "INSERT INTO messages(user_id, date, text, read) VALUES (?,?,?,?)",
                (
                    u.user_id,
                    msg.date.isoformat(),
                    msg.text,
                    int(msg.read),
                ),
            )
    conn.commit()
    conn.close()


# --- New transactional helper APIs ---

def create_club(club: Club, conn: sqlite3.Connection | None = None) -> None:
    """Insert a new club record into the database."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clubs(club_id, name, logo, region, slogan) VALUES (?,?,?,?,?)",
        (club.club_id, club.name, club.logo, club.region, club.slogan),
    )
    cur.execute(
        "INSERT INTO club_meta(club_id, banned_ids, leader_id, admin_ids, pending_members, rejected_members) VALUES (?,?,?,?,?,?)",
        (
            club.club_id,
            "[]",
            club.leader_id,
            "[]",
            "{}",
            "{}",
        ),
    )
    if close:
        conn.commit()
        conn.close()
        set_club(club)
        _pending_clubs.pop(club.club_id, None)
    else:
        _pending_clubs[club.club_id] = club


def create_user(user: User, conn: sqlite3.Connection | None = None) -> None:
    """Insert a new user account."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users(
            user_id, name, password_hash, wechat_openid, can_create_club,
            is_sys_admin, created_clubs, joined_clubs, max_creatable_clubs,
            max_joinable_clubs
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            user.user_id,
            user.name,
            user.password_hash,
            user.wechat_openid,
            int(user.can_create_club),
            int(getattr(user, "is_sys_admin", False)),
            user.created_clubs,
            user.joined_clubs,
            getattr(user, "max_creatable_clubs", 0),
            getattr(user, "max_joinable_clubs", 5),
        ),
    )
    if close:
        conn.commit()
        conn.close()
        set_user(user)
        _pending_users.pop(user.user_id, None)
    else:
        _pending_users[user.user_id] = user


def create_player(club_id: str, player: Player, conn: sqlite3.Connection | None = None) -> None:
    """Add a player to a club."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    if IS_PG:
        cur.execute(
            """
            INSERT INTO players(
                user_id, name, singles_rating, doubles_rating, experience,
                pre_ratings, age, gender, avatar, birth, handedness, backhand,
                region, joined
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (
                player.user_id,
                player.name,
                player.singles_rating,
                player.doubles_rating,
                player.experience,
                "{}",
                player.age,
                player.gender,
                player.avatar,
                player.birth,
                player.handedness,
                player.backhand,
                player.region,
                player.joined.isoformat(),
            ),
        )
        cur.execute(
            "INSERT INTO club_members(club_id, user_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
            (club_id, player.user_id),
        )
    else:
        cur.execute(
            """
            INSERT OR IGNORE INTO players(
                user_id, name, singles_rating, doubles_rating, experience,
                pre_ratings, age, gender, avatar, birth, handedness, backhand,
                region, joined
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                player.user_id,
                player.name,
                player.singles_rating,
                player.doubles_rating,
                player.experience,
                "{}",
                player.age,
                player.gender,
                player.avatar,
                player.birth,
                player.handedness,
                player.backhand,
                player.region,
                player.joined.isoformat(),
            ),
        )
        cur.execute(
            "INSERT OR IGNORE INTO club_members(club_id, user_id) VALUES (?, ?)",
            (club_id, player.user_id),
        )
    if close:
        conn.commit()
        conn.close()
        set_player(player)
        _pending_players.pop(player.user_id, None)
    else:
        _pending_players[player.user_id] = player

def create_match(
    club_id: str,
    match: Match | DoublesMatch,
    pending: bool = False,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Insert a match record."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    table = "pending_matches" if pending else "matches"
    if isinstance(match, DoublesMatch):
        data = {
            "a1": match.player_a1.user_id,
            "a2": match.player_a2.user_id,
            "b1": match.player_b1.user_id,
            "b2": match.player_b2.user_id,
            "score_a": match.score_a,
                "score_b": match.score_b,
                "weight": match.format_weight,
                "location": match.location,
                "format_name": match.format_name,
                "initiator": match.initiator,
                "confirmed_a": match.confirmed_a,
                "confirmed_b": match.confirmed_b,
                "created": match.created.isoformat(),
                "created_ts": match.created_ts.isoformat(),
                "confirmed_on": match.confirmed_on.isoformat() if match.confirmed_on else None,
                "status": match.status,
                "status_date": match.status_date.isoformat() if match.status_date else None,
            }
        cur.execute(
            f"INSERT INTO {table}(club_id, type, date, data) VALUES (?,?,?,?)",
            (
                club_id,
                "doubles",
                match.date.isoformat(),
                json.dumps(data),
            ),
        )
    else:
        data = {
            "player_a": match.player_a.user_id,
            "player_b": match.player_b.user_id,
            "score_a": match.score_a,
            "score_b": match.score_b,
            "weight": match.format_weight,
                "location": match.location,
                "format_name": match.format_name,
                "initiator": match.initiator,
                "confirmed_a": match.confirmed_a,
                "confirmed_b": match.confirmed_b,
                "created": match.created.isoformat(),
                "created_ts": match.created_ts.isoformat(),
                "confirmed_on": match.confirmed_on.isoformat() if match.confirmed_on else None,
                "status": match.status,
                "status_date": match.status_date.isoformat() if match.status_date else None,
            }
        cur.execute(
            f"INSERT INTO {table}(club_id, type, date, data) VALUES (?,?,?,?)",
            (
                club_id,
                "singles",
                match.date.isoformat(),
                json.dumps(data),
            ),
        )
    if close:
        conn.commit()
        conn.close()


def update_match_record(
    table: str, match_id: int, data: dict, conn: sqlite3.Connection | None = None
) -> None:
    """Update a match JSON data by id."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE {table} SET data = ? WHERE id = ?",
        (json.dumps(data), match_id),
    )
    if close:
        conn.commit()
        conn.close()


def add_club_member(club_id: str, user_id: str, conn: sqlite3.Connection | None = None) -> None:
    """Insert a user into ``club_members``."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    if IS_PG:
        cur.execute(
            "INSERT INTO club_members(club_id, user_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
            (club_id, user_id),
        )
    else:
        cur.execute(
            "INSERT OR IGNORE INTO club_members(club_id, user_id) VALUES (?, ?)",
            (club_id, user_id),
        )
    if close:
        conn.commit()
        conn.close()


def get_club_member(club_id: str, user_id: str) -> bool:
    """Return ``True`` if the user is a member of the club."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM club_members WHERE club_id = ? AND user_id = ?",
        (club_id, user_id),
    )
    result = cur.fetchone() is not None
    conn.close()
    return result


def remove_club_member(club_id: str, user_id: str, conn: sqlite3.Connection | None = None) -> None:
    """Delete a membership record."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM club_members WHERE club_id = ? AND user_id = ?",
        (club_id, user_id),
    )
    if close:
        conn.commit()
        conn.close()


def get_player_record(user_id: str) -> Player | None:
    """Load a single player from the ``players`` table."""
    conn = _connect()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT * FROM players WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        conn.close()
        return None
    from .cli import normalize_gender

    p = Player(
        user_id=row["user_id"],
        name=row["name"],
        singles_rating=row["singles_rating"],
        doubles_rating=row["doubles_rating"],
        experience=row["experience"],
        age=row["age"],
        gender=normalize_gender(row["gender"]),
        avatar=row["avatar"],
        birth=row["birth"],
        handedness=row["handedness"],
        backhand=row["backhand"],
        region=row["region"],
        joined=datetime.date.fromisoformat(row["joined"])
        if row["joined"]
        else datetime.date.today(),
    )
    p.pre_ratings.update(json.loads(row["pre_ratings"] or "{}"))
    conn.close()
    return p


def get_player(user_id: str) -> Player | None:
    """Return a single :class:`Player` by id using caches when possible."""
    global _players_cache, _db_file
    if _players_cache and _db_file == DATABASE_URL:
        player = _players_cache.get(user_id)
        if player:
            return player
    if _redis:
        cached = _load_cache(f"tennis:player:{user_id}")
        if cached:
            _players_cache[user_id] = cached
            _db_file = DATABASE_URL
            return cached
    player = get_player_record(user_id)
    if player:
        set_player(player)
    return player


def update_player_record(player: Player, conn: sqlite3.Connection | None = None) -> None:
    """Update a player's information."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute(
            """
            UPDATE players SET
                name = ?,
                singles_rating = ?,
                doubles_rating = ?,
                experience = ?,
                pre_ratings = ?,
                age = ?,
                gender = ?,
                avatar = ?,
                birth = ?,
                handedness = ?,
                backhand = ?,
                region = ?,
                joined = ?
            WHERE user_id = ?
            """,
            (
                player.name,
                player.singles_rating,
                player.doubles_rating,
                player.experience,
                json.dumps(player.pre_ratings),
                player.age,
                player.gender,
                player.avatar,
                player.birth,
                player.handedness,
                player.backhand,
                player.region,
            player.joined.isoformat(),
            player.user_id,
        ),
    )
    if close:
        conn.commit()
        conn.close()
        set_player(player)
        _pending_players.pop(player.user_id, None)
    else:
        _pending_players[player.user_id] = player

def set_player(player: Player) -> None:
    """Cache a single :class:`Player` object."""
    global _db_file
    _players_cache[player.user_id] = player
    _db_file = DATABASE_URL
    _save_cache(f"tennis:player:{player.user_id}", player)


def set_user(user: User) -> None:
    """Cache a single :class:`User` object."""
    global _users_cache, _db_file
    if _users_cache is None:
        _users_cache = {}
    _users_cache[user.user_id] = user
    _db_file = DATABASE_URL
    _save_cache(f"tennis:user:{user.user_id}", user)


def set_club(club: Club) -> None:
    """Cache a single :class:`Club` object."""
    global _clubs_cache, _db_file
    if _clubs_cache is None:
        _clubs_cache = {}
    _clubs_cache[club.club_id] = club
    _db_file = DATABASE_URL
    _save_cache(f"tennis:club:{club.club_id}", club)

def update_user_record(user: User, conn: sqlite3.Connection | None = None) -> None:
    """Update fields of a :class:`User` record."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users SET
            name = ?,
            password_hash = ?,
            wechat_openid = ?,
            can_create_club = ?,
            is_sys_admin = ?,
            created_clubs = ?,
            joined_clubs = ?,
            max_creatable_clubs = ?,
            max_joinable_clubs = ?
        WHERE user_id = ?
        """,
        (
            user.name,
            user.password_hash,
            user.wechat_openid,
            int(user.can_create_club),
            int(getattr(user, "is_sys_admin", False)),
            user.created_clubs,
            user.joined_clubs,
            getattr(user, "max_creatable_clubs", 0),
            getattr(user, "max_joinable_clubs", 5),
            user.user_id,
        ),
    )
    if close:
        conn.commit()
        conn.close()
        set_user(user)
        _pending_users.pop(user.user_id, None)
    else:
        _pending_users[user.user_id] = user


def delete_player(user_id: str, conn: sqlite3.Connection | None = None) -> None:
    """Remove a player from the ``players`` table."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM club_members WHERE user_id = ?", (user_id,))
    if close:
        conn.commit()
        conn.close()
        _players_cache.pop(user_id, None)
        if _redis:
            try:
                _redis.delete(f"tennis:player:{user_id}")
            except Exception:
                pass
    else:
        _pending_players[user_id] = None


def get_match_record(table: str, match_id: int) -> sqlite3.Row | None:
    """Fetch a single match or pending match row."""
    conn = _connect()
    cur = conn.cursor()
    row = cur.execute(
        f"SELECT * FROM {table} WHERE id = ?",
        (match_id,),
    ).fetchone()
    conn.close()
    return row


def delete_match_record(table: str, match_id: int, conn: sqlite3.Connection | None = None) -> None:
    """Delete a match or pending match by ID."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE id = ?", (match_id,))
    if close:
        conn.commit()
        conn.close()


def create_appointment_record(club_id: str, appt: Appointment, conn: sqlite3.Connection | None = None) -> int:
    """Insert an appointment and return the new row id."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute(
            """
            INSERT INTO appointments(
                club_id, date, creator, location, info, signups
            ) VALUES (?,?,?,?,?,?)
            """,
            (
                club_id,
                appt.date.isoformat(),
                appt.creator,
                appt.location,
                appt.info,
                json.dumps(list(appt.signups)),
            ),
    )
    row_id = cur.lastrowid
    if close:
        conn.commit()
        conn.close()
        _refresh_after_write()
    else:
        conn.commit()
    return row_id


def get_appointment_record(app_id: int) -> sqlite3.Row | None:
    """Retrieve an appointment by ID."""
    conn = _connect()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT * FROM appointments WHERE id = ?",
        (app_id,),
    ).fetchone()
    conn.close()
    return row


def update_appointment_record(app_id: int, conn: sqlite3.Connection | None = None, **fields) -> None:
    """Update fields of an appointment."""
    if not fields:
        return
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cols = []
    values = []
    for k, v in fields.items():
        if k == "signups":
            v = json.dumps(list(v))
        if k == "date" and isinstance(v, datetime.date):
            v = v.isoformat()
        cols.append(f"{k} = ?")
        values.append(v)
    values.append(app_id)
    cur.execute(
        f"UPDATE appointments SET {', '.join(cols)} WHERE id = ?",
        values,
    )
    if close:
        conn.commit()
        conn.close()
        _refresh_after_write()
    else:
        conn.commit()


def delete_appointment_record(app_id: int, conn: sqlite3.Connection | None = None) -> None:
    """Delete an appointment by ID."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointments WHERE id = ?", (app_id,))
    if close:
        conn.commit()
        conn.close()
        _refresh_after_write()
    else:
        conn.commit()


def create_message_record(
    user_id: str,
    text: str,
    *,
    date: datetime.date | None = None,
    read: bool = False,
) -> int:
    """Insert a message for a user and return its row id."""
    conn = _connect()
    cur = conn.cursor()
    if date is None:
        date = datetime.date.today()
    cur.execute(
        "INSERT INTO messages(user_id, date, text, read) VALUES (?,?,?,?)",
        (user_id, date.isoformat(), text, int(read)),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    _refresh_after_write()
    return row_id


def get_message_record(msg_id: int) -> sqlite3.Row | None:
    """Load a message row by ID."""
    conn = _connect()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT * FROM messages WHERE id = ?",
        (msg_id,),
    ).fetchone()
    conn.close()
    return row


def update_message_record(msg_id: int, *, text: str | None = None, read: bool | None = None) -> None:
    """Update the text or read state of a message."""
    if text is None and read is None:
        return
    conn = _connect()
    cur = conn.cursor()
    cols = []
    values = []
    if text is not None:
        cols.append("text = ?")
        values.append(text)
    if read is not None:
        cols.append("read = ?")
        values.append(int(read))
    values.append(msg_id)
    cur.execute(
        f"UPDATE messages SET {', '.join(cols)} WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()
    _refresh_after_write()


def delete_message_record(msg_id: int) -> None:
    """Remove a message from the database."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
    _refresh_after_write()


def insert_token(token: str, user_id: str) -> None:
    """Persist or update an authentication token."""
    conn = _connect()
    cur = conn.cursor()
    if IS_PG:
        cur.execute(
            """
            INSERT INTO auth_tokens(token, user_id, ts) VALUES (?,?,?)
            ON CONFLICT (token) DO UPDATE SET user_id = EXCLUDED.user_id, ts = EXCLUDED.ts
            """,
            (token, user_id, datetime.datetime.utcnow().isoformat()),
        )
    else:
        cur.execute(
            "INSERT OR REPLACE INTO auth_tokens(token, user_id, ts) VALUES (?,?,?)",
            (token, user_id, datetime.datetime.utcnow().isoformat()),
        )
    conn.commit()
    conn.close()
    _refresh_after_write()


def delete_token(token: str) -> None:
    """Remove an authentication token."""
    conn = _connect()
    conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    _refresh_after_write()


def get_token(token: str) -> tuple[str, datetime.datetime] | None:
    """Retrieve a ``(user_id, timestamp)`` tuple for the token."""
    conn = _connect()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT user_id, ts FROM auth_tokens WHERE token = ?",
        (token,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return row["user_id"], datetime.datetime.fromisoformat(row["ts"])


def insert_refresh_token(user_id: str, token: str, expires: datetime.datetime) -> None:
    """Persist or update a refresh token."""
    conn = _connect()
    cur = conn.cursor()
    if IS_PG:
        cur.execute(
            """
            INSERT INTO refresh_tokens(user_id, token, expires) VALUES (?,?,?)
            ON CONFLICT (user_id) DO UPDATE SET token = EXCLUDED.token, expires = EXCLUDED.expires
            """,
            (user_id, token, expires.isoformat()),
        )
    else:
        cur.execute(
            "INSERT OR REPLACE INTO refresh_tokens(user_id, token, expires) VALUES (?,?,?)",
            (user_id, token, expires.isoformat()),
        )
    conn.commit()
    conn.close()
    _refresh_after_write()


def get_refresh_token(token: str) -> tuple[str, datetime.datetime] | None:
    """Return ``(user_id, expires)`` for the refresh token."""
    conn = _connect()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT user_id, expires FROM refresh_tokens WHERE token = ?",
        (token,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return row["user_id"], datetime.datetime.fromisoformat(row["expires"])


def delete_refresh_token(user_id: str) -> None:
    """Remove refresh token for a user."""
    conn = _connect()
    conn.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    _refresh_after_write()


def get_user(user_id: str) -> User | None:
    """Return a single :class:`User` by id or ``None`` if not found."""
    global _users_cache, _db_file
    if _users_cache is not None and _db_file == DATABASE_URL:
        user = _users_cache.get(user_id)
        if user:
            return user
    if _redis:
        cached = _load_cache(f"tennis:user:{user_id}")
        if cached:
            if _users_cache is None:
                _users_cache = {}
            _users_cache[user_id] = cached
            _db_file = DATABASE_URL
            return cached

    conn = _connect()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        conn.close()
        return None
    u = User(
        user_id=row["user_id"],
        name=row["name"],
        password_hash=row["password_hash"],
        wechat_openid=row["wechat_openid"],
        can_create_club=True,
        is_sys_admin=bool(row["is_sys_admin"]) if "is_sys_admin" in row.keys() else False,
        created_clubs=row["created_clubs"],
        joined_clubs=row["joined_clubs"],
        max_creatable_clubs=row["max_creatable_clubs"] if "max_creatable_clubs" in row.keys() else 0,
        max_joinable_clubs=row["max_joinable_clubs"] if "max_joinable_clubs" in row.keys() else 5,
    )
    for m in cur.execute(
        "SELECT id, date, text, read FROM messages WHERE user_id = ? ORDER BY id",
        (user_id,),
    ):
        u.messages.append(
            Message(
                date=datetime.date.fromisoformat(m["date"]),
                text=m["text"],
                read=bool(m["read"]),
            )
        )
    conn.close()

    set_user(u)
    return u


def get_club(club_id: str) -> Club | None:
    """Return a single :class:`Club` by id or ``None`` if not found."""
    global _clubs_cache, _db_file
    if _clubs_cache is not None and _db_file == DATABASE_URL:
        club = _clubs_cache.get(club_id)
        if club:
            return club
    if _redis:
        cached = _load_cache(f"tennis:club:{club_id}")
        if cached:
            if _clubs_cache is None:
                _clubs_cache = {}
            _clubs_cache[club_id] = cached
            _db_file = DATABASE_URL
            return cached

    clubs, _ = load_data()
    club = clubs.get(club_id)
    if club:
        set_club(club)
    return club


def list_user_messages(user_id: str) -> list[tuple[int, Message]]:
    """Return all messages for a user as ``(id, Message)`` tuples."""
    conn = _connect()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, date, text, read FROM messages WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    messages = [
        (
            r["id"],
            Message(
                date=datetime.date.fromisoformat(r["date"]),
                text=r["text"],
                read=bool(r["read"]),
            ),
        )
        for r in rows
    ]
    conn.close()
    return messages


def mark_user_message_read(user_id: str, index: int) -> None:
    """Mark a user's message by list index as read."""
    conn = _connect()
    cur = conn.cursor()
    ids = cur.execute(
        "SELECT id FROM messages WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    if index >= len(ids):
        conn.close()
        raise IndexError("Message not found")
    msg_id = ids[index]["id"]
    cur.execute(
        "UPDATE messages SET read = 1 WHERE id = ?",
        (msg_id,),
    )
    conn.commit()
    conn.close()
    _refresh_after_write()


def save_user(user: User, conn: sqlite3.Connection | None = None) -> None:
    """Persist a single user's data and messages."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = ?", (user.user_id,))
    cur.execute("DELETE FROM messages WHERE user_id = ?", (user.user_id,))
    cur.execute(
        """
        INSERT INTO users(
            user_id, name, password_hash, wechat_openid, can_create_club,
            is_sys_admin, created_clubs, joined_clubs, max_creatable_clubs,
            max_joinable_clubs
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            user.user_id,
            user.name,
            user.password_hash,
            user.wechat_openid,
            int(user.can_create_club),
            int(getattr(user, "is_sys_admin", False)),
            user.created_clubs,
            user.joined_clubs,
            getattr(user, "max_creatable_clubs", 0),
            getattr(user, "max_joinable_clubs", 5),
        ),
    )
    for msg in user.messages:
        cur.execute(
            "INSERT INTO messages(user_id, date, text, read) VALUES (?,?,?,?)",
            (user.user_id, msg.date.isoformat(), msg.text, int(msg.read)),
        )
    if close:
        conn.commit()
        conn.close()
        set_user(user)
    else:
        _pending_users[user.user_id] = user

def save_club(club: Club, conn: sqlite3.Connection | None = None) -> None:
    """Persist a single club's records."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM clubs WHERE club_id = ?", (club.club_id,))
    cur.execute("DELETE FROM club_meta WHERE club_id = ?", (club.club_id,))
    cur.execute("DELETE FROM club_members WHERE club_id = ?", (club.club_id,))
    cur.execute("DELETE FROM matches WHERE club_id = ?", (club.club_id,))
    cur.execute("DELETE FROM pending_matches WHERE club_id = ?", (club.club_id,))
    cur.execute("DELETE FROM appointments WHERE club_id = ?", (club.club_id,))
    cur.execute(
        "INSERT INTO clubs(club_id, name, logo, region, slogan) VALUES (?,?,?,?,?)",
        (club.club_id, club.name, club.logo, club.region, club.slogan),
    )
    cur.execute(
        "INSERT INTO club_meta(club_id, banned_ids, leader_id, admin_ids, pending_members, rejected_members) VALUES (?,?,?,?,?,?)",
        (
            club.club_id,
            json.dumps(list(club.banned_ids)),
            club.leader_id,
            json.dumps(list(club.admin_ids)),
            json.dumps({uid: vars(pm) for uid, pm in club.pending_members.items()}),
            json.dumps(club.rejected_members),
        ),
    )
    for player in club.members.values():
        create_player(club.club_id, player, conn=conn)
        update_player_record(player, conn=conn)
    for m in club.matches:
        create_match(club.club_id, m, pending=False, conn=conn)
    for m in club.pending_matches:
        create_match(club.club_id, m, pending=True, conn=conn)
    for a in club.appointments:
        create_appointment_record(club.club_id, a, conn=conn)
    if close:
        conn.commit()
        conn.close()
        set_club(club)
        _pending_clubs.pop(club.club_id, None)
        for player in club.members.values():
            set_player(player)
            _pending_players.pop(player.user_id, None)
    else:
        _pending_clubs[club.club_id] = club

def delete_club(club_id: str, conn: sqlite3.Connection | None = None) -> None:
    """Remove all records associated with a club."""
    close = conn is None
    if conn is None:
        conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM clubs WHERE club_id = ?", (club_id,))
    cur.execute("DELETE FROM club_meta WHERE club_id = ?", (club_id,))
    cur.execute("DELETE FROM club_members WHERE club_id = ?", (club_id,))
    cur.execute("DELETE FROM matches WHERE club_id = ?", (club_id,))
    cur.execute("DELETE FROM pending_matches WHERE club_id = ?", (club_id,))
    cur.execute("DELETE FROM appointments WHERE club_id = ?", (club_id,))
    if close:
        conn.commit()
        conn.close()
        if _clubs_cache is not None:
            _clubs_cache.pop(club_id, None)
        if _redis:
            try:
                _redis.delete(f"tennis:club:{club_id}")
            except Exception:
                pass
    else:
        _pending_clubs[club_id] = None

