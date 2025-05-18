import argparse
import datetime
from typing import Optional

from .models import Player, Club, Match
from .rating import update_ratings, weighted_rating
from .storage import load_data, save_data


def create_club(clubs, club_id: str, name: str, logo: Optional[str], region: Optional[str]):
    if club_id in clubs:
        raise ValueError('Club already exists')
    clubs[club_id] = Club(club_id=club_id, name=name, logo=logo, region=region)


def add_player(clubs, club_id: str, user_id: str, name: str):
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    if user_id in club.members:
        raise ValueError('Player already in club')
    club.members[user_id] = Player(user_id=user_id, name=name)


def record_match(clubs, club_id: str, user_a: str, user_b: str, score_a: int, score_b: int, date: datetime.date, weight: float):
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    pa = club.members.get(user_a)
    pb = club.members.get(user_b)
    if not pa or not pb:
        raise ValueError('Both players must be in club')
    match = Match(date=date, player_a=pa, player_b=pb, score_a=score_a, score_b=score_b, format_weight=weight)
    update_ratings(match)


def main():
    parser = argparse.ArgumentParser(description='Tennis Rating CLI')
    sub = parser.add_subparsers(dest='cmd')

    cclub = sub.add_parser('create_club')
    cclub.add_argument('club_id')
    cclub.add_argument('name')
    cclub.add_argument('--logo')
    cclub.add_argument('--region')

    aplayer = sub.add_parser('add_player')
    aplayer.add_argument('club_id')
    aplayer.add_argument('user_id')
    aplayer.add_argument('name')

    rmatch = sub.add_parser('record_match')
    rmatch.add_argument('club_id')
    rmatch.add_argument('user_a')
    rmatch.add_argument('user_b')
    rmatch.add_argument('score_a', type=int)
    rmatch.add_argument('score_b', type=int)
    rmatch.add_argument('--date', type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(), default=datetime.date.today())
    rmatch.add_argument('--weight', type=float, default=1.0)

    args = parser.parse_args()
    clubs = load_data()

    if args.cmd == 'create_club':
        create_club(clubs, args.club_id, args.name, args.logo, args.region)
    elif args.cmd == 'add_player':
        add_player(clubs, args.club_id, args.user_id, args.name)
    elif args.cmd == 'record_match':
        record_match(clubs, args.club_id, args.user_a, args.user_b, args.score_a, args.score_b, args.date, args.weight)
        pa = clubs[args.club_id].members[args.user_a]
        pb = clubs[args.club_id].members[args.user_b]
        print(f"New ratings: {pa.name} {pa.singles_rating:.1f}, {pb.name} {pb.singles_rating:.1f}")
    else:
        parser.print_help()
        return

    save_data(clubs)


if __name__ == '__main__':
    main()
