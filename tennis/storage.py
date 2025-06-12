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
        can_create_club INTEGER,
        created_clubs INTEGER DEFAULT 0,
        joined_clubs INTEGER DEFAULT 0
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
    conn.commit()


def load_data() -> Dict[str, Club]:
    conn = _connect()
    cur = conn.cursor()
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
            gender=row["gender"],
            avatar=row["avatar"],
            birth=row["birth"],
            handedness=row["handedness"],
            backhand=row["backhand"],
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
             age, gender, avatar, birth, handedness, backhand, joined)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
            can_create_club=bool(row["can_create_club"]),
            created_clubs=row["created_clubs"],
            joined_clubs=row["joined_clubs"],
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
            "INSERT INTO users(user_id, name, password_hash, wechat_openid, can_create_club, created_clubs, joined_clubs) VALUES (?,?,?,?,?,?,?)",
            (
                u.user_id,
                u.name,
                u.password_hash,
                u.wechat_openid,
                int(u.can_create_club),
                u.created_clubs,
                u.joined_clubs,
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
