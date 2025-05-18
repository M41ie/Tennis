import json
import datetime
from pathlib import Path
from typing import Dict

from .models import Player, Club, Match, DoublesMatch

DATA_FILE = Path('data.json')


def load_data() -> Dict[str, Club]:
    if DATA_FILE.exists():
        text = DATA_FILE.read_text(encoding='utf-8')
        raw = json.loads(text)
        clubs = {}
        for cid, c in raw.get('clubs', {}).items():
            club = Club(club_id=cid, name=c['name'], logo=c.get('logo'), region=c.get('region'))
            for pid, p in c.get('members', {}).items():
                club.members[pid] = Player(
                    user_id=pid,
                    name=p['name'],
                    singles_rating=p.get('singles_rating', 1000.0),
                    doubles_rating=p.get('doubles_rating', 1000.0),
                    experience=p.get('experience', 0.0),
                )
                club.members[pid].pre_ratings.update(p.get('pre_ratings', {}))
            for m in c.get('matches', []):
                date = datetime.date.fromisoformat(m['date'])
                if m.get('type') == 'doubles':
                    ma1 = club.members[m['a1']]
                    ma2 = club.members[m['a2']]
                    mb1 = club.members[m['b1']]
                    mb2 = club.members[m['b2']]
                    match = DoublesMatch(
                        date=date,
                        player_a1=ma1,
                        player_a2=ma2,
                        player_b1=mb1,
                        player_b2=mb2,
                        score_a=m['score_a'],
                        score_b=m['score_b'],
                        format_weight=m.get('weight', 1.0),
                        rating_a1_after=m.get('rating_a1_after'),
                        rating_a2_after=m.get('rating_a2_after'),
                        rating_b1_after=m.get('rating_b1_after'),
                        rating_b2_after=m.get('rating_b2_after'),
                    )
                    club.matches.append(match)
                    ma1.doubles_matches.append(match)
                    ma2.doubles_matches.append(match)
                    mb1.doubles_matches.append(match)
                    mb2.doubles_matches.append(match)
                else:
                    pa = club.members[m['player_a']]
                    pb = club.members[m['player_b']]
                    match = Match(
                        date=date,
                        player_a=pa,
                        player_b=pb,
                        score_a=m['score_a'],
                        score_b=m['score_b'],
                        format_weight=m.get('weight', 1.0),
                        rating_a_after=m.get('rating_a_after'),
                        rating_b_after=m.get('rating_b_after'),
                    )
                    club.matches.append(match)
                    pa.singles_matches.append(match)
                    pb.singles_matches.append(match)
            clubs[cid] = club
        return clubs
    return {}


def save_data(clubs: Dict[str, Club]) -> None:
    raw = {'clubs': {}}
    for cid, club in clubs.items():
        club_raw = {
            'name': club.name,
            'logo': club.logo,
            'region': club.region,
            'members': {pid: {
                'name': p.name,
                'singles_rating': p.singles_rating,
                'doubles_rating': p.doubles_rating,
                'experience': p.experience,
                'pre_ratings': p.pre_ratings,
            } for pid, p in club.members.items()},
            'matches': [],
        }
        for m in club.matches:
            if isinstance(m, DoublesMatch):
                club_raw['matches'].append({
                    'type': 'doubles',
                    'date': m.date.isoformat(),
                    'a1': m.player_a1.user_id,
                    'a2': m.player_a2.user_id,
                    'b1': m.player_b1.user_id,
                    'b2': m.player_b2.user_id,
                    'score_a': m.score_a,
                    'score_b': m.score_b,
                    'weight': m.format_weight,
                    'rating_a1_after': m.rating_a1_after,
                    'rating_a2_after': m.rating_a2_after,
                    'rating_b1_after': m.rating_b1_after,
                    'rating_b2_after': m.rating_b2_after,
                })
            else:
                club_raw['matches'].append({
                    'type': 'singles',
                    'date': m.date.isoformat(),
                    'player_a': m.player_a.user_id,
                    'player_b': m.player_b.user_id,
                    'score_a': m.score_a,
                    'score_b': m.score_b,
                    'weight': m.format_weight,
                    'rating_a_after': m.rating_a_after,
                    'rating_b_after': m.rating_b_after,
                })
        raw['clubs'][cid] = club_raw
    DATA_FILE.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
