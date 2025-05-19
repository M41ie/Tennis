from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime

from .storage import load_data, save_data
from .rating import (
    update_ratings,
    update_doubles_ratings,
    weighted_rating,
    weighted_doubles_rating,
    format_weight_from_name,
)
from .models import Player, Club

app = FastAPI()

clubs = load_data()


class ClubCreate(BaseModel):
    club_id: str
    name: str
    logo: str | None = None
    region: str | None = None


class PlayerCreate(BaseModel):
    user_id: str
    name: str
    age: int | None = None
    gender: str | None = None
    avatar: str | None = None


class MatchCreate(BaseModel):
    user_a: str
    user_b: str
    score_a: int
    score_b: int
    date: datetime.date | None = None
    format: str | None = None
    weight: float | None = None
    location: str | None = None


@app.get("/clubs")
def list_clubs():
    return [{"club_id": c.club_id, "name": c.name} for c in clubs.values()]


@app.post("/clubs")
def create_club(data: ClubCreate):
    if data.club_id in clubs:
        raise HTTPException(400, "Club exists")
    clubs[data.club_id] = Club(
        club_id=data.club_id,
        name=data.name,
        logo=data.logo,
        region=data.region,
    )
    save_data(clubs)
    return {"status": "ok"}


@app.get("/clubs/{club_id}/players")
def list_players(club_id: str):
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    today = datetime.date.today()
    return [
        {
            "user_id": p.user_id,
            "name": p.name,
            "rating": weighted_rating(p, today),
        }
        for p in club.members.values()
    ]


@app.post("/clubs/{club_id}/players")
def add_player(club_id: str, data: PlayerCreate):
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    if data.user_id in club.members:
        raise HTTPException(400, "Player exists")
    club.members[data.user_id] = Player(
        user_id=data.user_id,
        name=data.name,
        age=data.age,
        gender=data.gender,
        avatar=data.avatar,
    )
    save_data(clubs)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/matches")
def record_match_api(club_id: str, data: MatchCreate):
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    pa = club.members.get(data.user_a)
    pb = club.members.get(data.user_b)
    if not pa or not pb:
        raise HTTPException(400, "Players not found")
    date = data.date or datetime.date.today()
    weight = data.weight
    if data.format:
        weight = format_weight_from_name(data.format)
    if weight is None:
        weight = format_weight_from_name("6_game")
    match = Match(
        date=date,
        player_a=pa,
        player_b=pb,
        score_a=data.score_a,
        score_b=data.score_b,
        format_weight=weight,
        location=data.location,
        format_name=data.format,
    )
    update_ratings(match)
    club.matches.append(match)
    pa.singles_rating = weighted_rating(pa, date)
    pb.singles_rating = weighted_rating(pb, date)
    save_data(clubs)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
