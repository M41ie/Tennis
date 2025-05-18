import datetime
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

from tennis.models import Player, Match
from tennis.rating import (
    update_ratings,
    FORMAT_6_GAME,
    FORMAT_4_GAME,
    FORMAT_TB11,
    FORMAT_TB10,
    FORMAT_TB7,
)

FORMAT_MAP = {
    "6局": FORMAT_6_GAME,
    "4局": FORMAT_4_GAME,
    "抢11": FORMAT_TB11,
    "抢10": FORMAT_TB10,
    "抢7": FORMAT_TB7,
}

BASE_DATE = datetime.date(1899, 12, 30)


def excel_date(serial):
    return BASE_DATE + datetime.timedelta(days=int(float(serial)))


def load_matches(path="业余网球评分系统.xlsx"):
    z = zipfile.ZipFile(path)
    with z.open("xl/sharedStrings.xml") as f:
        ss_root = ET.fromstring(f.read())
    shared = [t.text or "" for t in ss_root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")]
    with z.open("xl/worksheets/sheet2.xml") as f:
        sheet = ET.fromstring(f.read())
    for row in sheet.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
        cells = []
        for c in row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
            v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
            if v is None:
                cells.append("")
            else:
                val = v.text
                if c.attrib.get("t") == "s":
                    val = shared[int(val)]
                cells.append(val)
        if cells and cells[0] != "比赛日期":
            yield cells


def main(limit=20):
    players = {}
    match_count = defaultdict(int)
    for i, row in enumerate(load_matches()):
        if limit and i >= limit:
            break
        date = excel_date(row[0])
        name_a = row[1]
        rating_a = float(row[2])
        name_b = row[3]
        rating_b = float(row[4])
        fmt = FORMAT_MAP.get(row[5], FORMAT_6_GAME)
        score_a = int(float(row[6]))
        score_b = int(float(row[7]))

        pa = players.setdefault(name_a, Player(user_id=name_a, name=name_a, singles_rating=rating_a))
        pb = players.setdefault(name_b, Player(user_id=name_b, name=name_b, singles_rating=rating_b))
        pa.singles_rating = rating_a
        pb.singles_rating = rating_b

        match = Match(date=date, player_a=pa, player_b=pb, score_a=score_a, score_b=score_b, format_weight=fmt)
        update_ratings(match)
        match_count[name_a] += 1
        match_count[name_b] += 1
        print(f"{date.isoformat()} {name_a} vs {name_b}: {pa.singles_rating:.3f}, {pb.singles_rating:.3f}")

    print("\nFinal ratings:")
    for name, player in players.items():
        print(f"{name}: {player.singles_rating:.3f} ({match_count[name]} matches)")


if __name__ == "__main__":
    main()
