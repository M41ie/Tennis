import json
import datetime
import sqlite3
from pathlib import Path
from typing import Dict

# Absolute path to the repository root database file. Using a fixed location
# ensures scripts behave the same regardless of the working directory.
DB_FILE = Path(__file__).resolve().parent.parent / "tennis.db"

from .models import (
    Player,
    Club,
    Match,
    DoublesMatch,
    User,
    Appointment,
    Message,
    players,
)


def _connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
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
        "CREATE TABLE IF NOT EXISTS club_meta (club_id TEXT PRIMARY KEY, banned_ids TEXT, leader_id TEXT, admin_ids TEXT)"
    )
    # add new columns if an older database is missing them
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
    conn.commit()


def load_data() -> Dict[str, Club]:
    conn = _connect()
    cur = conn.cursor()
    from .cli import normalize_gender
    clubs: Dict[str, Club] = {}
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

    players.clear()
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
    return clubs


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
            "INSERT INTO club_meta(club_id, banned_ids, leader_id, admin_ids) VALUES (?,?,?,?)",
            (
                cid,
                json.dumps(list(club.banned_ids)),
                club.leader_id,
                json.dumps(list(club.admin_ids)),
            ),
        )
        for uid in club.members:
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


def load_users() -> Dict[str, User]:
    """Load user accounts from the database."""
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

def create_club(club: Club) -> None:
    """Insert a new club record into the database."""
    with sqlite3.connect(DB_FILE) as conn:
        _init_schema(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clubs(club_id, name, logo, region, slogan) VALUES (?,?,?,?,?)",
            (club.club_id, club.name, club.logo, club.region, club.slogan),
        )
        cur.execute(
            "INSERT INTO club_meta(club_id, banned_ids, leader_id, admin_ids) VALUES (?,?,?,?)",
            (
                club.club_id,
                "[]",
                club.leader_id,
                "[]",
            ),
        )
        conn.commit()


def create_user(user: User) -> None:
    """Insert a new user account."""
    with sqlite3.connect(DB_FILE) as conn:
        _init_schema(conn)
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
        conn.commit()


def create_player(club_id: str, player: Player) -> None:
    """Add a player to a club."""
    with sqlite3.connect(DB_FILE) as conn:
        _init_schema(conn)
        cur = conn.cursor()
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
        conn.commit()


def create_match(club_id: str, match: Match | DoublesMatch, pending: bool = False) -> None:
    """Insert a match record."""
    with sqlite3.connect(DB_FILE) as conn:
        _init_schema(conn)
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
        conn.commit()


def update_match_record(table: str, match_id: int, data: dict) -> None:
    """Update a match JSON data by id."""
    with sqlite3.connect(DB_FILE) as conn:
        _init_schema(conn)
        cur = conn.cursor()
        cur.execute(
            f"UPDATE {table} SET data = ? WHERE id = ?",
            (json.dumps(data), match_id),
        )
        conn.commit()


# --- Token management helpers ---

def insert_token(token: str, user_id: str) -> None:
    """Persist a newly generated auth token."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO auth_tokens(token, user_id, ts) VALUES (?,?,?)",
            (token, user_id, datetime.datetime.utcnow().isoformat()),
        )
        conn.commit()


def delete_token(token: str) -> None:
    """Remove an auth token."""
    with _connect() as conn:
        conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        conn.commit()


def get_token(token: str) -> tuple[str, datetime.datetime] | None:
    """Return ``(user_id, timestamp)`` if token exists, else ``None``."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT user_id, ts FROM auth_tokens WHERE token = ?",
            (token,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return row["user_id"], datetime.datetime.fromisoformat(row["ts"])


# --- User and club helpers ---

def get_user(user_id: str) -> User | None:
    """Fetch a single user record from the database."""
    with _connect() as conn:
        cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        wechat_openid = row["wechat_openid"] if "wechat_openid" in row.keys() else None
        user = User(
            user_id=row["user_id"],
            name=row["name"],
            password_hash=row["password_hash"],
            wechat_openid=wechat_openid,
            can_create_club=bool(row["can_create_club"]),
            is_sys_admin=bool(row["is_sys_admin"]) if "is_sys_admin" in row.keys() else False,
            created_clubs=row["created_clubs"],
            joined_clubs=row["joined_clubs"],
            max_creatable_clubs=row["max_creatable_clubs"] if "max_creatable_clubs" in row.keys() else 0,
            max_joinable_clubs=row["max_joinable_clubs"] if "max_joinable_clubs" in row.keys() else 5,
        )
        for m in conn.execute(
            "SELECT date, text, read FROM messages WHERE user_id = ? ORDER BY id",
            (user_id,),
        ):
            msg = Message(
                date=datetime.date.fromisoformat(m["date"]),
                text=m["text"],
                read=bool(m["read"]),
            )
            user.messages.append(msg)
        return user


def update_user(user_id: str, **fields) -> None:
    """Update columns in the users table."""
    if not fields:
        return
    allowed = {
        "name",
        "password_hash",
        "wechat_openid",
        "can_create_club",
        "is_sys_admin",
        "created_clubs",
        "joined_clubs",
        "max_creatable_clubs",
        "max_joinable_clubs",
    }
    assignments = []
    values = []
    for k, v in fields.items():
        if k not in allowed:
            continue
        assignments.append(f"{k}=?")
        values.append(v)
    if not assignments:
        return
    values.append(user_id)
    with _connect() as conn:
        conn.execute(
            f"UPDATE users SET {', '.join(assignments)} WHERE user_id = ?",
            values,
        )
        conn.commit()


def get_club(club_id: str) -> Club | None:
    """Fetch a club without loading the entire dataset."""
    from .cli import normalize_gender

    with _connect() as conn:
        cur = conn.execute("SELECT * FROM clubs WHERE club_id = ?", (club_id,))
        row = cur.fetchone()
        if not row:
            return None
        club = Club(
            club_id=row["club_id"],
            name=row["name"],
            logo=row["logo"],
            region=row["region"],
            slogan=row["slogan"],
        )
        meta = conn.execute(
            "SELECT banned_ids, leader_id, admin_ids FROM club_meta WHERE club_id = ?",
            (club_id,),
        ).fetchone()
        if meta:
            club.banned_ids.update(json.loads(meta["banned_ids"] or "[]"))
            club.leader_id = meta["leader_id"]
            club.admin_ids.update(json.loads(meta["admin_ids"] or "[]"))
        for row in conn.execute(
            """
            SELECT p.* FROM club_members m JOIN players p ON m.user_id = p.user_id
            WHERE m.club_id = ?
            """,
            (club_id,),
        ):
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
            club.members[p.user_id] = p
        return club


def update_club(club_id: str, **fields) -> None:
    """Update club or club_meta columns."""
    if not fields:
        return
    club_fields = {}
    meta_fields = {}
    for k, v in fields.items():
        if k in {"name", "logo", "region", "slogan"}:
            club_fields[k] = v
        elif k in {"leader_id", "admin_ids", "banned_ids"}:
            meta_fields[k] = v
    with _connect() as conn:
        if club_fields:
            sets = ", ".join(f"{k}=?" for k in club_fields)
            values = list(club_fields.values()) + [club_id]
            conn.execute(
                f"UPDATE clubs SET {sets} WHERE club_id = ?",
                values,
            )
        if meta_fields:
            if "admin_ids" in meta_fields and isinstance(meta_fields["admin_ids"], set):
                meta_fields["admin_ids"] = json.dumps(list(meta_fields["admin_ids"]))
            if "banned_ids" in meta_fields and isinstance(meta_fields["banned_ids"], set):
                meta_fields["banned_ids"] = json.dumps(list(meta_fields["banned_ids"]))
            sets = ", ".join(f"{k}=?" for k in meta_fields)
            values = list(meta_fields.values()) + [club_id]
            conn.execute(
                f"UPDATE club_meta SET {sets} WHERE club_id = ?",
                values,
            )
        conn.commit()

