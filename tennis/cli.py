import argparse
import datetime
from typing import Optional

from .models import Player, Club, Match, DoublesMatch
from .rating import (
    update_ratings,
    update_doubles_ratings,
    weighted_rating,
    weighted_doubles_rating,
    initial_rating_from_votes,
    format_weight_from_name,
    FORMAT_WEIGHTS,
)
from .storage import load_data, save_data


def create_club(clubs, club_id: str, name: str, logo: Optional[str], region: Optional[str]):
    if club_id in clubs:
        raise ValueError('Club already exists')
    clubs[club_id] = Club(club_id=club_id, name=name, logo=logo, region=region)


def add_player(
    clubs,
    club_id: str,
    user_id: str,
    name: str,
    age: int | None = None,
    gender: str | None = None,
    avatar: str | None = None,
):
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    if user_id in club.members:
        raise ValueError('Player already in club')
    club.members[user_id] = Player(
        user_id=user_id,
        name=name,
        age=age,
        gender=gender,
        avatar=avatar,
    )


def pre_rate(clubs, club_id: str, rater_id: str, target_id: str, rating: float):
    """Record a pre-rating for ``target_id`` from ``rater_id``."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    rater = club.members.get(rater_id)
    target = club.members.get(target_id)
    if not rater or not target:
        raise ValueError('Both rater and target must be in club')

    target.pre_ratings[rater_id] = rating
    new_rating = initial_rating_from_votes(target, club)
    target.singles_rating = new_rating
    target.doubles_rating = new_rating


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
    clubs[club_id].matches.append(match)

    rating_a = weighted_rating(pa, date)
    rating_b = weighted_rating(pb, date)
    pa.singles_rating = rating_a
    pb.singles_rating = rating_b
    print(f"New ratings: {pa.name} {rating_a:.1f}, {pb.name} {rating_b:.1f}")


def record_doubles(clubs, club_id: str, a1: str, a2: str, b1: str, b2: str, score_a: int, score_b: int, date: datetime.date, weight: float):
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    pa1 = club.members.get(a1)
    pa2 = club.members.get(a2)
    pb1 = club.members.get(b1)
    pb2 = club.members.get(b2)
    if not all([pa1, pa2, pb1, pb2]):
        raise ValueError('All players must be in club')
    match = DoublesMatch(
        date=date,
        player_a1=pa1,
        player_a2=pa2,
        player_b1=pb1,
        player_b2=pb2,
        score_a=score_a,
        score_b=score_b,
        format_weight=weight,
    )
    update_doubles_ratings(match)
    clubs[club_id].matches.append(match)
    rating_a1 = weighted_doubles_rating(pa1, date)
    rating_a2 = weighted_doubles_rating(pa2, date)
    rating_b1 = weighted_doubles_rating(pb1, date)
    rating_b2 = weighted_doubles_rating(pb2, date)
    pa1.doubles_rating = rating_a1
    pa2.doubles_rating = rating_a2
    pb1.doubles_rating = rating_b1
    pb2.doubles_rating = rating_b2
    print(
        f"New doubles ratings: {pa1.name} {rating_a1:.1f}, {pa2.name} {rating_a2:.1f}, "
        f"{pb1.name} {rating_b1:.1f}, {pb2.name} {rating_b2:.1f}"
    )


def get_leaderboard(
    clubs,
    club_id: str | None,
    doubles: bool,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    gender: str | None = None,
):
    """Collect leaderboard data with optional filters."""

    today = datetime.date.today()
    if club_id is not None:
        club = clubs.get(club_id)
        if not club:
            raise ValueError("Club not found")
        clubs_to_iter = [club]
    else:
        clubs_to_iter = list(clubs.values())

    players = []
    for club in clubs_to_iter:
        for p in club.members.values():
            rating = (
                weighted_doubles_rating(p, today)
                if doubles
                else weighted_rating(p, today)
            )
            if min_rating is not None and rating < min_rating:
                continue
            if max_rating is not None and rating > max_rating:
                continue
            if min_age is not None and (p.age is None or p.age < min_age):
                continue
            if max_age is not None and (p.age is None or p.age > max_age):
                continue
            if gender is not None and p.gender != gender:
                continue
            players.append((p, rating))

    players.sort(key=lambda x: x[1], reverse=True)
    return players


def leaderboard(
    clubs,
    club_id: str,
    doubles: bool,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    gender: str | None = None,
):
    data = get_leaderboard(
        clubs,
        club_id,
        doubles,
        min_rating=min_rating,
        max_rating=max_rating,
        min_age=min_age,
        max_age=max_age,
        gender=gender,
    )
    for p, rating in data:
        avatar = p.avatar or "-"
        print(f"{avatar} {p.name}: {rating:.1f}")


def player_history(clubs, club_id: str, user_id: str, doubles: bool):
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    player = club.members.get(user_id)
    if not player:
        raise ValueError('Player not found')
    matches = player.doubles_matches if doubles else player.singles_matches
    for m in matches:
        if doubles:
            if m.player_a1 == player:
                rating = m.rating_a1_after
            elif m.player_a2 == player:
                rating = m.rating_a2_after
            elif m.player_b1 == player:
                rating = m.rating_b1_after
            else:
                rating = m.rating_b2_after
            opponents = f"{m.player_b1.name}/{m.player_b2.name}" if m.player_a1 == player or m.player_a2 == player else f"{m.player_a1.name}/{m.player_a2.name}"
        else:
            rating = m.rating_a_after if m.player_a == player else m.rating_b_after
            opponents = m.player_b.name if m.player_a == player else m.player_a.name
        print(f"{m.date.isoformat()} vs {opponents}: {rating:.1f}")


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
    aplayer.add_argument('--age', type=int)
    aplayer.add_argument('--gender')
    aplayer.add_argument('--avatar')

    pre = sub.add_parser('pre_rate')
    pre.add_argument('club_id')
    pre.add_argument('rater_id')
    pre.add_argument('target_id')
    pre.add_argument('rating', type=float)

    rmatch = sub.add_parser('record_match')
    rmatch.add_argument('club_id')
    rmatch.add_argument('user_a')
    rmatch.add_argument('user_b')
    rmatch.add_argument('score_a', type=int)
    rmatch.add_argument('score_b', type=int)
    rmatch.add_argument('--date', type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(), default=datetime.date.today())
    rmatch.add_argument('--format', choices=FORMAT_WEIGHTS.keys())
    rmatch.add_argument('--weight', type=float)

    rdouble = sub.add_parser('record_doubles')
    rdouble.add_argument('club_id')
    rdouble.add_argument('a1')
    rdouble.add_argument('a2')
    rdouble.add_argument('b1')
    rdouble.add_argument('b2')
    rdouble.add_argument('score_a', type=int)
    rdouble.add_argument('score_b', type=int)
    rdouble.add_argument('--date', type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(), default=datetime.date.today())
    rdouble.add_argument('--format', choices=FORMAT_WEIGHTS.keys())
    rdouble.add_argument('--weight', type=float)

    board = sub.add_parser('leaderboard')
    board.add_argument('club_id', nargs='?')
    board.add_argument('--doubles', action='store_true')
    board.add_argument('--min-rating', type=float)
    board.add_argument('--max-rating', type=float)
    board.add_argument('--min-age', type=int)
    board.add_argument('--max-age', type=int)
    board.add_argument('--gender')

    hist = sub.add_parser('player_history')
    hist.add_argument('club_id')
    hist.add_argument('user_id')
    hist.add_argument('--doubles', action='store_true')

    args = parser.parse_args()
    clubs = load_data()

    if args.cmd == 'create_club':
        create_club(clubs, args.club_id, args.name, args.logo, args.region)
    elif args.cmd == 'add_player':
        add_player(
            clubs,
            args.club_id,
            args.user_id,
            args.name,
            age=args.age,
            gender=args.gender,
            avatar=args.avatar,
        )
    elif args.cmd == 'pre_rate':
        pre_rate(clubs, args.club_id, args.rater_id, args.target_id, args.rating)
    elif args.cmd == 'record_match':
        weight = args.weight
        if args.format:
            weight = format_weight_from_name(args.format)
        if weight is None:
            weight = format_weight_from_name("6_game")
        record_match(
            clubs,
            args.club_id,
            args.user_a,
            args.user_b,
            args.score_a,
            args.score_b,
            args.date,
            weight,
        )
    elif args.cmd == 'record_doubles':
        weight = args.weight
        if args.format:
            weight = format_weight_from_name(args.format)
        if weight is None:
            weight = format_weight_from_name("6_game")
        record_doubles(
            clubs,
            args.club_id,
            args.a1,
            args.a2,
            args.b1,
            args.b2,
            args.score_a,
            args.score_b,
            args.date,
            weight,
        )
    elif args.cmd == 'leaderboard':
        leaderboard(
            clubs,
            args.club_id,
            args.doubles,
            min_rating=args.min_rating,
            max_rating=args.max_rating,
            min_age=args.min_age,
            max_age=args.max_age,
            gender=args.gender,
        )
        return
    elif args.cmd == 'player_history':
        player_history(clubs, args.club_id, args.user_id, args.doubles)
        return
    else:
        parser.print_help()
        return

    save_data(clubs)


if __name__ == '__main__':
    main()
