import sqlite3
import json
from tennis.storage import DB_FILE


def migrate(db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {row[1] for row in cur.execute("PRAGMA table_info('players')")}
    if 'club_id' not in cols:
        print('Database already migrated')
        return

    rows = list(cur.execute("SELECT * FROM players"))

    cur.execute("ALTER TABLE players RENAME TO players_old")

    cur.execute(
        """CREATE TABLE players (
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
        """CREATE TABLE club_members (
        club_id TEXT,
        user_id TEXT,
        PRIMARY KEY (club_id, user_id)
    )"""
    )

    seen = set()
    for r in rows:
        if r["user_id"] not in seen:
            cur.execute(
                "INSERT INTO players(user_id, name, singles_rating, doubles_rating, experience, pre_ratings, age, gender, avatar, birth, handedness, backhand, joined) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r["user_id"],
                    r["name"],
                    r["singles_rating"],
                    r["doubles_rating"],
                    r["experience"],
                    r["pre_ratings"],
                    r["age"],
                    r["gender"],
                    r["avatar"],
                    r["birth"],
                    r["handedness"],
                    r["backhand"],
                    r["joined"],
                ),
            )
            seen.add(r["user_id"])
        cur.execute(
            "INSERT INTO club_members(club_id, user_id) VALUES (?,?)",
            (r["club_id"], r["user_id"]),
        )

    cur.execute("DROP TABLE players_old")
    conn.commit()
    conn.close()


if __name__ == '__main__':
    migrate()
