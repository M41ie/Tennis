import csv
import datetime
from pathlib import Path

from tennis import cli, rating, storage

# Mapping from Chinese format names to rating weights
FORMAT_MAP = {
    "6局": rating.FORMAT_6_GAME,
    "4局": rating.FORMAT_4_GAME,
    "抢11": rating.FORMAT_TB11,
    "抢10": rating.FORMAT_TB10,
    "抢7": rating.FORMAT_TB7,
}

CLUB_ID = "weekday_warriors"
CLUB_NAME = "工作日战神"
ADMIN_ID = "admin"


def parse_csv(path: str):
    """Return (player_rows, match_rows) from the csv file."""
    player_rows = []
    match_rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        section = "players"
        for row in reader:
            if not row or not row[0].strip():
                section = "matches"
                continue
            if section == "players":
                if row[0] == "姓名":
                    continue
                player_rows.append(row)
            else:
                if row[0] == "时间":
                    continue
                match_rows.append(row)
    return player_rows, match_rows


def main(csv_path="est_data.csv"):
    clubs = storage.load_data()
    users = storage.load_users()

    # create admin account
    if ADMIN_ID not in users:
        cli.register_user(users, ADMIN_ID, "Admin", "admin", allow_create=True)

    # create club
    if CLUB_ID not in clubs:
        cli.create_club(users, clubs, ADMIN_ID, CLUB_ID, CLUB_NAME, None, None)

    player_rows, match_rows = parse_csv(csv_path)

    # add players
    for row in player_rows:
        name = row[0]
        try:
            rating_value = float(row[1])
        except ValueError:
            continue
        if name not in users:
            cli.register_user(users, name, name, "123")
        if name not in clubs[CLUB_ID].members:
            cli.add_player(clubs, CLUB_ID, name, name)
        p = clubs[CLUB_ID].members[name]
        p.singles_rating = rating_value
        p.doubles_rating = rating_value

    # record matches
    for row in match_rows:
        date_str, a, b, location, fmt_name, score = row[:6]
        try:
            date = datetime.datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()
        except ValueError:
            date = datetime.date.today()
        try:
            score_a, score_b = [int(s) for s in score.split("-")]
        except Exception:
            continue
        weight = FORMAT_MAP.get(fmt_name, rating.FORMAT_6_GAME)
        cli.record_match(
            clubs,
            CLUB_ID,
            a,
            b,
            score_a,
            score_b,
            date,
            weight,
            location=location,
            format_name=fmt_name,
        )

    storage.save_data(clubs)
    storage.save_users(users)


if __name__ == "__main__":
    path = "est_data.csv"
    if not Path(path).exists():
        print(f"CSV file '{path}' not found")
    else:
        main(path)

