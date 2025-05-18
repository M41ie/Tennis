import json
from pathlib import Path
from typing import Dict

from .models import Player, Club

DATA_FILE = Path('data.json')


def load_data() -> Dict[str, Club]:
    if DATA_FILE.exists():
        text = DATA_FILE.read_text(encoding='utf-8')
        raw = json.loads(text)
        clubs = {}
        for cid, c in raw.get('clubs', {}).items():
            club = Club(club_id=cid, name=c['name'], logo=c.get('logo'), region=c.get('region'))
            for pid, p in c.get('members', {}).items():
                club.members[pid] = Player(user_id=pid, name=p['name'], singles_rating=p.get('singles_rating', 1000.0), doubles_rating=p.get('doubles_rating', 1000.0))
            clubs[cid] = club
        return clubs
    return {}


def save_data(clubs: Dict[str, Club]) -> None:
    raw = {'clubs': {}}
    for cid, club in clubs.items():
        raw['clubs'][cid] = {
            'name': club.name,
            'logo': club.logo,
            'region': club.region,
            'members': {pid: {
                'name': p.name,
                'singles_rating': p.singles_rating,
                'doubles_rating': p.doubles_rating
            } for pid, p in club.members.items()}
        }
    DATA_FILE.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
