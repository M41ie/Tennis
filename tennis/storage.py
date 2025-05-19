import json
import datetime
import sqlite3
from pathlib import Path
from typing import Dict

from .models import Player, Club, Match, DoublesMatch

DB_FILE = Path("tennis.db")


def _connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS clubs (club_id TEXT PRIMARY KEY, name TEXT, logo TEXT, region TEXT, leader TEXT, admins TEXT)"
    )
    # add new columns if database already existed without them
    cols = [r[1] for r in cur.execute("PRAGMA table_info(clubs)")]
    if "leader" not in cols:
        cur.execute("ALTER TABLE clubs ADD COLUMN leader TEXT")
    if "admins" not in cols:
        cur.execute("ALTER TABLE clubs ADD COLUMN admins TEXT")
    cur.execute(
        """CREATE TABLE IF NOT EXISTS players (
        club_id TEXT,
        user_id TEXT,
        name TEXT,
        singles_rating REAL,
        doubles_rating REAL,
        experience REAL,
        pre_ratings TEXT,
        age INTEGER,
        gender TEXT,
        avatar TEXT,
        PRIMARY KEY (club_id, user_id)
    )"""
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY AUTOINCREMENT, club_id TEXT, type TEXT, date TEXT, data TEXT, confirm_a INTEGER, confirm_b INTEGER, approved INTEGER)"
    )
    cols = [r[1] for r in cur.execute("PRAGMA table_info(matches)")]
    if "confirm_a" not in cols:
        cur.execute("ALTER TABLE matches ADD COLUMN confirm_a INTEGER")
    if "confirm_b" not in cols:
        cur.execute("ALTER TABLE matches ADD COLUMN confirm_b INTEGER")
    if "approved" not in cols:
        cur.execute("ALTER TABLE matches ADD COLUMN approved INTEGER")
    conn.commit()


def load_data() -> Dict[str, Club]:
    conn = _connect()
    cur = conn.cursor()
    clubs: Dict[str, Club] = {}
    for row in cur.execute("SELECT * FROM clubs"):
        keys = row.keys()
        leader = row["leader"] if "leader" in keys else None
        admins = json.loads(row["admins"]) if "admins" in keys and row["admins"] else []
        clubs[row["club_id"]] = Club(
            club_id=row["club_id"],
            name=row["name"],
            logo=row["logo"],
            region=row["region"],
            leader_id=leader,
            admins=admins,
        )

    for row in cur.execute("SELECT * FROM players"):
        club = clubs.get(row["club_id"])
        if not club:
            continue
        p = Player(
            user_id=row["user_id"],
            name=row["name"],
            singles_rating=row["singles_rating"],
            doubles_rating=row["doubles_rating"],
            experience=row["experience"],
            age=row["age"],
            gender=row["gender"],
            avatar=row["avatar"],
        )
        p.pre_ratings.update(json.loads(row["pre_ratings"] or "{}"))
        club.members[p.user_id] = p

    for row in cur.execute("SELECT * FROM matches ORDER BY id"):
        club = clubs.get(row["club_id"])
        if not club:
            continue
        data = json.loads(row["data"])
        date = datetime.date.fromisoformat(row["date"])
        approved = bool(row["approved"])
        confirmed_a = bool(row["confirm_a"])
        confirmed_b = bool(row["confirm_b"])
        if row["type"] == "doubles":
            pa1 = club.members[data["a1"]]
            pa2 = club.members[data["a2"]]
            pb1 = club.members[data["b1"]]
            pb2 = club.members[data["b2"]]
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
            match.rating_a1_before = data.get("rating_a1_before")
            match.rating_a2_before = data.get("rating_a2_before")
            match.rating_b1_before = data.get("rating_b1_before")
            match.rating_b2_before = data.get("rating_b2_before")
            match.rating_a1_after = data.get("rating_a1_after")
            match.rating_a2_after = data.get("rating_a2_after")
            match.rating_b1_after = data.get("rating_b1_after")
            match.rating_b2_after = data.get("rating_b2_after")
            match.initiator = data.get("initiator")
            match.confirmed_a = confirmed_a
            match.confirmed_b = confirmed_b
            match.approved = approved
            target_list = club.matches if approved else club.pending_matches
            target_list.append(match)
            if approved:
                pa1.doubles_matches.append(match)
                pa2.doubles_matches.append(match)
                pb1.doubles_matches.append(match)
                pb2.doubles_matches.append(match)
        else:
            pa = club.members[data["player_a"]]
            pb = club.members[data["player_b"]]
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
            match.rating_a_before = data.get("rating_a_before")
            match.rating_b_before = data.get("rating_b_before")
            match.rating_a_after = data.get("rating_a_after")
            match.rating_b_after = data.get("rating_b_after")
            match.initiator = data.get("initiator")
            match.confirmed_a = confirmed_a
            match.confirmed_b = confirmed_b
            match.approved = approved
            target_list = club.matches if approved else club.pending_matches
            target_list.append(match)
            if approved:
                pa.singles_matches.append(match)
                pb.singles_matches.append(match)
    conn.close()
    return clubs


def save_data(clubs: Dict[str, Club]) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM clubs")
    cur.execute("DELETE FROM players")
    cur.execute("DELETE FROM matches")
    for cid, club in clubs.items():
        cur.execute(
            "INSERT INTO clubs(club_id, name, logo, region, leader, admins) VALUES (?,?,?,?,?,?)",
            (
                cid,
                club.name,
                club.logo,
                club.region,
                club.leader_id,
                json.dumps(club.admins),
            ),
        )
        for p in club.members.values():
            cur.execute(
                """INSERT INTO players
                (club_id, user_id, name, singles_rating, doubles_rating,
                 experience, pre_ratings, age, gender, avatar)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    cid,
                    p.user_id,
                    p.name,
                    p.singles_rating,
                    p.doubles_rating,
                    p.experience,
                    json.dumps(p.pre_ratings),
                    p.age,
                    p.gender,
                    p.avatar,
                ),
            )
        for m in list(club.matches) + list(club.pending_matches):
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
                    "initiator": m.initiator,
                }
                cur.execute(
                    "INSERT INTO matches(club_id, type, date, data, confirm_a, confirm_b, approved) VALUES (?,?,?,?,?,?,?)",
                    (
                        cid,
                        "doubles",
                        m.date.isoformat(),
                        json.dumps(data),
                        int(m.confirmed_a),
                        int(m.confirmed_b),
                        int(m.approved),
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
                    "initiator": m.initiator,
                }
                cur.execute(
                    "INSERT INTO matches(club_id, type, date, data, confirm_a, confirm_b, approved) VALUES (?,?,?,?,?,?,?)",
                    (
                        cid,
                        "singles",
                        m.date.isoformat(),
                        json.dumps(data),
                        int(m.confirmed_a),
                        int(m.confirmed_b),
                        int(m.approved),
                    ),
                )
    conn.commit()
    conn.close()
