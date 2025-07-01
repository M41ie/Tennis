from __future__ import annotations

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
import shutil
from uuid import uuid4
from .services.exceptions import ServiceError
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictInt
import datetime
import json
import urllib.request
import urllib.parse
from pathlib import Path

STATIC_ROOT = Path("/home/ubuntu/Tennis/static")
MEDIA_URL_PREFIX = "/static/media/avatars"
AVATARS_ROOT = STATIC_ROOT / "media/avatars"
AVATARS_ROOT.mkdir(parents=True, exist_ok=True)


import tennis.storage as storage
from .storage import load_data, load_users, invalidate_cache, get_cache_version

# ensure cached data does not leak across reloads
invalidate_cache()
CACHE_VERSION = get_cache_version()
from .cli import (
    register_user,
    resolve_user,
    hash_password,
    check_password,
    validate_scores,
    update_player as cli_update_player,
    normalize_gender,
)
from .services.clubs import (
    request_join_club,
    approve_member_request,
    dissolve_existing_club,
    approve_pending_match,
    reject_join_request as svc_reject_join,
    clear_member_rejection as svc_clear_rejection,
    update_club_info as svc_update_club,
    update_player_profile as svc_update_player,
    update_global_player as svc_update_global_player,
    remove_club_member as svc_remove_member,
    update_member_role as svc_update_role,
    submit_pending_match as svc_submit_match,
    confirm_pending_match as svc_confirm_match,
    reject_pending_match as svc_reject_match,
    veto_pending_match as svc_veto_match,
    submit_pending_doubles as svc_submit_doubles,
    confirm_pending_doubles as svc_confirm_doubles,
    reject_pending_doubles as svc_reject_doubles,
    veto_pending_doubles as svc_veto_doubles,
    create_appointment_entry as svc_create_appointment,
    update_appointment_signups as svc_update_signup,
    pre_rate_member as svc_pre_rate,
    record_match_result as svc_record_match,
    sys_set_leader as svc_sys_set_leader,
)
from .services.users import update_user_limits as svc_update_limits
from .rating import (
    update_ratings,
    update_doubles_ratings,
    weighted_rating,
    weighted_doubles_rating,
    format_weight_from_name,
    weighted_singles_matches,
    weighted_doubles_matches,
)
from .services.stats import _pending_status_for_user, _club_stats
from .models import Player, Club, Match, DoublesMatch, Appointment, User

# Runtime state loaded from persistent storage. ``load_data`` returns the
# internal cache dictionaries, so these remain in sync with updates performed
# through the storage layer.
clubs, players = load_data()
users = load_users()
import tennis.cli as cli_module
cli_module.players = players


app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")


@app.middleware("http")
async def cache_sync_middleware(request: Request, call_next):
    """Reload cached data when another worker has updated the version."""
    global CACHE_VERSION, clubs, users, players
    version = storage.get_cache_version()
    if version != CACHE_VERSION:
        invalidate_cache()
        clubs, players = load_data()
        users = load_users()
        import tennis.cli as cli_module
        cli_module.players = players
        CACHE_VERSION = version
    response = await call_next(request)
    return response


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


@app.exception_handler(ServiceError)
def service_error_handler(request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

# runtime state previously lived in ``services.state``
from .services.state import TOKEN_TTL
from .services.auth import require_auth, assert_token_matches
from .services.helpers import get_user_or_404, get_club_or_404
from .routes.users import router as users_router
from .routes.clubs import router as clubs_router
from .routes.matches import router as matches_router

app.include_router(users_router)
app.include_router(clubs_router)
app.include_router(matches_router)


@app.post("/upload/image", tags=["upload"])
async def upload_image(file: UploadFile = File(...)):
    try:
        ext = Path(file.filename).suffix
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".gif"]:
            raise HTTPException(status_code=400, detail="不支持的图片格式")

        new_filename = f"{uuid4()}{ext}"
        save_path = AVATARS_ROOT / new_filename
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"url": f"{MEDIA_URL_PREFIX}/{new_filename}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {e}")





# WeChat mini program credentials from environment (optional)
from .config import get_wechat_appid, get_wechat_secret

WECHAT_APPID = get_wechat_appid()
WECHAT_SECRET = get_wechat_secret()


def _generate_club_id() -> str:
    """Return a unique club id based on existing clubs."""
    i = 1
    while f"c{i}" in clubs:
        i += 1
    return f"c{i}"


def _exchange_wechat_code(code: str) -> dict:
    """Call WeChat API to exchange login code for session info."""
    params = urllib.parse.urlencode(
        {
            "appid": WECHAT_APPID,
            "secret": WECHAT_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    url = "https://api.weixin.qq.com/sns/jscode2session?" + params
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


# --- utility helpers -------------------------------------------------------

def absolute_url(request: Request, path: str | None) -> str | None:
    """Return ``path`` as an absolute URL relative to ``request`` base."""
    if not path or path.startswith("http://") or path.startswith("https://"):
        return path
    return str(request.base_url).rstrip("/") + path


# authentication helpers now provided by services.auth




def _region_match(player_region: str | None, filter_region: str | None) -> bool:
    """Return True if the player's region matches the filter."""
    if not filter_region:
        return True
    if not player_region:
        return False
    return player_region.startswith(filter_region)


class ClubCreate(BaseModel):
    club_id: str | None = None
    name: str
    user_id: str
    logo: str | None = None
    region: str | None = None
    slogan: str | None = None


class ClubUpdate(BaseModel):
    user_id: str
    name: str | None = None
    logo: str | None = None
    region: str | None = None
    slogan: str | None = None


class PlayerCreate(BaseModel):
    user_id: str
    name: str
    age: int | None = None
    gender: str | None = None
    avatar: str | None = None
    birth: str | None = None
    handedness: str | None = None
    backhand: str | None = None
    region: str | None = None


class PlayerUpdate(BaseModel):
    user_id: str
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    avatar: str | None = None
    birth: str | None = None
    handedness: str | None = None
    backhand: str | None = None
    region: str | None = None


class MatchCreate(BaseModel):
    user_id: str
    user_a: str
    user_b: str
    score_a: StrictInt
    score_b: StrictInt
    date: datetime.date | None = None
    format: str | None = None
    weight: float | None = None
    location: str | None = None


class PendingMatchCreate(BaseModel):
    club_id: str | None = None  # optional alternate clubs
    initiator: str
    opponent: str
    score_initiator: StrictInt
    score_opponent: StrictInt
    date: datetime.date | None = None
    format: str | None = None
    weight: float | None = None
    location: str | None = None


class PreRateRequest(BaseModel):
    rater_id: str
    target_id: str
    rating: float


class PendingDoublesCreate(BaseModel):
    club_id: str | None = None
    initiator: str
    partner: str
    opponent1: str
    opponent2: str
    score_initiator: StrictInt
    score_opponent: StrictInt
    date: datetime.date | None = None
    format: str | None = None
    weight: float | None = None
    location: str | None = None


class AppointmentCreate(BaseModel):
    user_id: str
    date: datetime.date
    location: str | None = None
    info: str | None = None


class SignupRequest(BaseModel):
    user_id: str


class WeChatLoginRequest(BaseModel):
    code: str


class JoinRequest(BaseModel):
    user_id: str
    singles_rating: float | None = None
    doubles_rating: float | None = None
    reason: str | None = None


class ApproveRequest(BaseModel):
    approver_id: str
    user_id: str
    rating: float
    admin: bool = False


class RejectRequest(BaseModel):
    approver_id: str
    user_id: str
    reason: str


class ClearRejectRequest(BaseModel):
    user_id: str


class RemoveRequest(BaseModel):
    remover_id: str
    ban: bool = False


class RoleRequest(BaseModel):
    user_id: str
    action: str


class LimitsUpdateRequest(BaseModel):
    max_joinable_clubs: int
    max_creatable_clubs: int


class SysLeaderRequest(BaseModel):
    user_id: str


class DissolveRequest(BaseModel):
    user_id: str





@app.post("/clubs/{club_id}/join")
def join_club(club_id: str, data: JoinRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    assert_token_matches(user, data.user_id)
    request_join_club(
        club_id,
        data.user_id,
        singles_rating=data.singles_rating,
        doubles_rating=data.doubles_rating,
        reason=data.reason,
    )
    return {"status": "ok"}


@app.delete("/clubs/{club_id}")
def dissolve_club_api(club_id: str, data: DissolveRequest, authorization: str | None = Header(None)):
    """Delete a club (leader only)."""
    user = require_auth(authorization)
    assert_token_matches(user, data.user_id)
    dissolve_existing_club(club_id, user)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/reject")
def reject_join_request(club_id: str, data: RejectRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    assert_token_matches(user, data.approver_id)
    svc_reject_join(club_id, data.approver_id, data.user_id, data.reason)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/clear_rejection")
def clear_rejection_api(club_id: str, data: ClearRejectRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    assert_token_matches(user, data.user_id)
    svc_clear_rejection(club_id, data.user_id)
    return {"status": "ok"}


@app.api_route("/clubs/{club_id}", methods=["PATCH", "PUT"])
def update_club_info(club_id: str, data: ClubUpdate, authorization: str | None = Header(None)):
    """Update club basic information (leader or admin only)."""
    user = require_auth(authorization)
    club = get_club_or_404(club_id)
    assert_token_matches(user, data.user_id)
    if user != club.leader_id and user not in club.admin_ids:
        raise HTTPException(403, "Forbidden")
    svc_update_club(
        club_id,
        name=data.name,
        logo=data.logo,
        region=data.region,
        slogan=data.slogan,
    )
    return {"status": "ok"}


@app.post("/clubs/{club_id}/approve")
def approve_club_member(club_id: str, data: ApproveRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    assert_token_matches(user, data.approver_id)
    approve_member_request(
        club_id,
        data.approver_id,
        data.user_id,
        data.rating,
        make_admin=data.admin,
    )
    return {"status": "ok"}


@app.get("/clubs")
def list_clubs():
    clubs = storage.list_clubs()
    return [{"club_id": c.club_id, "name": c.name} for c in clubs]




@app.get("/clubs/{club_id}")
def get_club_info(club_id: str):
    """Return basic club information including members and pending requests."""
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    today = datetime.date.today()
    pending = []
    for uid, info in club.pending_members.items():
        p = storage.get_player(uid)
        entry = {
            "user_id": uid,
            "name": p.name if p else None,
            "avatar": getattr(p, "avatar", None) if p else None,
            "gender": getattr(p, "gender", None) if p else None,
            "reason": info.reason,
            "singles_rating": info.singles_rating,
            "doubles_rating": info.doubles_rating,
        }
        singles = weighted_rating(p, today) if p else None
        if singles is not None:
            entry["global_rating"] = singles
        pending.append(entry)

    return {
        "club_id": club.club_id,
        "name": club.name,
        "logo": club.logo,
        "region": club.region,
        "slogan": club.slogan,
        "leader_id": club.leader_id,
        "admin_ids": list(club.admin_ids),
        "pending_members": pending,
        "members": [
            {
                "user_id": p.user_id,
                "name": p.name,
                "avatar": p.avatar,
                "gender": p.gender,
            }
            for p in club.members.values()
        ],
        "rejected_members": club.rejected_members,
        "stats": _club_stats(club),
    }


@app.get("/clubs/{club_id}/players")
def list_players(
    club_id: str,
    doubles: bool = False,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    gender: str | None = None,
    region: str | None = None,
):
    """Return members of a club optionally filtered and sorted by rating."""

    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")

    gender = normalize_gender(gender)
    today = datetime.date.today()
    get_rating = weighted_doubles_rating if doubles else weighted_rating
    
    players = []
    for p in club.members.values():
        rating = get_rating(p, today)
        singles_count = weighted_singles_matches(p)
        doubles_count = weighted_doubles_matches(p)
        if min_rating is not None and (rating is None or rating < min_rating):
            continue
        if max_rating is not None and (rating is None or rating > max_rating):
            continue
        if min_age is not None and (p.age is None or p.age < min_age):
            continue
        if max_age is not None and (p.age is None or p.age > max_age):
            continue
        if gender is not None and p.gender != gender:
            continue
        if not _region_match(p.region, region):
            continue
        entry = {
            "user_id": p.user_id,
            "name": p.name,
            "avatar": p.avatar,
            "gender": p.gender,
            "joined": p.joined.isoformat(),
            "weighted_singles_matches": round(singles_count, 2),
            "weighted_doubles_matches": round(doubles_count, 2),
        }
        if doubles:
            entry["doubles_rating"] = rating
        else:
            entry["singles_rating"] = rating
        players.append(entry)

    key = "doubles_rating" if doubles else "singles_rating"
    players.sort(key=lambda x: x.get(key, float('-inf')) if x.get(key) is not None else float('-inf'), reverse=True)
    return players


@app.get("/players/{user_id}")
def get_global_player(user_id: str, request: Request, recent: int = 0):
    """Return player information without requiring a club."""
    player = storage.get_player(user_id)
    if not player:
        raise HTTPException(404, "Player not found")

    today = datetime.date.today()
    singles = weighted_rating(player, today)
    doubles = weighted_doubles_rating(player, today)
    singles_count = weighted_singles_matches(player)
    doubles_count = weighted_doubles_matches(player)

    result = {
        "user_id": player.user_id,
        "id": player.user_id,
        "name": player.name,
        "avatar": player.avatar,
        "avatar_url": absolute_url(request, player.avatar),
        "birth": player.birth,
        "gender": player.gender,
        "handedness": player.handedness,
        "backhand": player.backhand,
        "region": player.region,
        "joined": player.joined.isoformat(),
        "singles_rating": singles,
        "doubles_rating": doubles,
        "weighted_singles_matches": round(singles_count, 2),
        "weighted_doubles_matches": round(doubles_count, 2),
        "weighted_games_singles": round(singles_count, 2),
        "weighted_games_doubles": round(doubles_count, 2),
    }

    if recent > 0:
        from .cli import get_player_match_cards

        cards = []
        # iterate across all clubs to collect matches for this player
        for club_id, club in clubs.items():
            if user_id not in club.members:
                continue
            try:
                match_cards = get_player_match_cards(clubs, club_id, user_id)
            except ValueError:
                continue
            for c in match_cards:
                c["date"] = c["date"].isoformat()
                cards.append(c)
        # sort by date descending and return most recent
        cards.sort(key=lambda x: x["date"], reverse=True)
        result["recent_records"] = cards[:recent]

    return result


@app.get("/players")
def list_all_players(
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    gender: str | None = None,
    club: str | None = None,
    doubles: bool = False,
    region: str | None = None,
    limit: int | None = None,
    offset: int = 0,
):
    """Return players from one or more clubs optionally filtered and sorted."""

    gender = normalize_gender(gender)
    if not club:
        clubs_to_iter = list(clubs.values())
        _, all_players = storage.load_data()
        extra_players = [
            p
            for p in all_players.values()
            if all(p.user_id not in c.members for c in clubs_to_iter)
        ]
    else:
        club_ids = club.split(",")
        clubs_to_iter = []
        for cid in club_ids:
            c = clubs.get(cid)
            if not c:
                raise HTTPException(404, "Club not found")
            clubs_to_iter.append(c)
        extra_players = []
    today = datetime.date.today()
    get_rating = weighted_doubles_rating if doubles else weighted_rating
    players_map: dict[str, dict[str, object]] = {}
    for c in clubs_to_iter:
        for p in c.members.values():
            rating = get_rating(p, today)
            singles_count = weighted_singles_matches(p)
            doubles_count = weighted_doubles_matches(p)
            if min_rating is not None and (rating is None or rating < min_rating):
                continue
            if max_rating is not None and (rating is None or rating > max_rating):
                continue
            if min_age is not None and (p.age is None or p.age < min_age):
                continue
            if max_age is not None and (p.age is None or p.age > max_age):
                continue
            if gender is not None and p.gender != gender:
                continue
            if not _region_match(p.region, region):
                continue
            if p.user_id in players_map:
                continue
            entry = {
                "club_id": c.club_id,
                "user_id": p.user_id,
                "name": p.name,
                "avatar": p.avatar,
                "gender": p.gender,
                "joined": p.joined.isoformat(),
                "weighted_singles_matches": round(singles_count, 2),
                "weighted_doubles_matches": round(doubles_count, 2),
            }
            if doubles:
                entry["doubles_rating"] = rating
            else:
                entry["singles_rating"] = rating
            players_map[p.user_id] = entry

    if not club:
        for p in extra_players:
            rating = get_rating(p, today)
            singles_count = weighted_singles_matches(p)
            doubles_count = weighted_doubles_matches(p)
            if min_rating is not None and (rating is None or rating < min_rating):
                continue
            if max_rating is not None and (rating is None or rating > max_rating):
                continue
            if min_age is not None and (p.age is None or p.age < min_age):
                continue
            if max_age is not None and (p.age is None or p.age > max_age):
                continue
            if gender is not None and p.gender != gender:
                continue
            if not _region_match(p.region, region):
                continue
            if p.user_id in players_map:
                continue
            entry = {
                "club_id": None,
                "user_id": p.user_id,
                "name": p.name,
                "avatar": p.avatar,
                "gender": p.gender,
                "joined": p.joined.isoformat(),
                "weighted_singles_matches": round(singles_count, 2),
                "weighted_doubles_matches": round(doubles_count, 2),
            }
            if doubles:
                entry["doubles_rating"] = rating
            else:
                entry["singles_rating"] = rating
            players_map[p.user_id] = entry
    players = list(players_map.values())
    key = "doubles_rating" if doubles else "singles_rating"
    players.sort(key=lambda x: x.get(key, float('-inf')) if x.get(key) is not None else float('-inf'), reverse=True)
    if offset:
        players = players[offset:]
    if limit is not None:
        players = players[:limit]
    return players


@app.get("/leaderboard_full")
def leaderboard_full(
    user_id: str | None = None,
    include_clubs: bool = True,
    include_joined: bool = True,
    include_players: bool = True,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    gender: str | None = None,
    club: str | None = None,
    doubles: bool = False,
    region: str | None = None,
    limit: int | None = None,
    offset: int = 0,
):
    """Return club list, joined clubs and leaderboard data in one call."""

    result: dict[str, object] = {}

    if include_clubs:
        result["clubs"] = list_clubs()

    if include_joined:
        if user_id:
            user = users.get(user_id)
            if not user:
                raise HTTPException(404, "User not found")
            result["joined_clubs"] = [cid for cid, c in clubs.items() if user_id in c.members]
        else:
            result["joined_clubs"] = []

    if include_players:
        result["players"] = list_all_players(
            min_rating=min_rating,
            max_rating=max_rating,
            min_age=min_age,
            max_age=max_age,
            gender=gender,
            club=club,
            doubles=doubles,
            region=region,
            limit=limit,
            offset=offset,
        )

    return result




@app.api_route("/players/{user_id}", methods=["PATCH", "PUT"])
def update_global_player(user_id: str, data: PlayerUpdate, authorization: str | None = Header(None)):
    """Update player information without specifying a club."""
    user = require_auth(authorization)
    if user != data.user_id or data.user_id != user_id:
        raise HTTPException(401, "Token mismatch")

    svc_update_global_player(
        user_id,
        name=data.name,
        age=data.age,
        gender=data.gender,
        avatar=data.avatar,
        birth=data.birth,
        handedness=data.handedness,
        backhand=data.backhand,
        region=data.region,
    )
    return {"status": "ok"}


@app.api_route("/clubs/{club_id}/players/{user_id}", methods=["PATCH", "PUT"])
def update_player_api(club_id: str, user_id: str, data: PlayerUpdate, authorization: str | None = Header(None)):
    """Update existing player information."""
    user = require_auth(authorization)
    if user != data.user_id or data.user_id != user_id:
        raise HTTPException(401, "Token mismatch")
    try:
        svc_update_player(
            club_id,
            user_id,
            name=data.name,
            age=data.age,
            gender=data.gender,
            avatar=data.avatar,
            birth=data.birth,
            handedness=data.handedness,
            backhand=data.backhand,
            region=data.region,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok"}


@app.delete("/clubs/{club_id}/members/{user_id}")
def remove_member_api(club_id: str, user_id: str, data: RemoveRequest, authorization: str | None = Header(None)):
    """Remove a club member (leader or admin only)."""
    user = require_auth(authorization)
    if user != data.remover_id:
        raise HTTPException(401, "Token mismatch")
    try:
        svc_remove_member(club_id, data.remover_id, user_id, ban=data.ban)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok"}


@app.post("/clubs/{club_id}/role")
def update_role_api(club_id: str, data: RoleRequest, authorization: str | None = Header(None)):
    """Update member roles within a club."""
    actor = require_auth(authorization)
    try:
        svc_update_role(club_id, data.action, actor, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok"}


@app.post("/clubs/{club_id}/prerate")
def pre_rate_api(club_id: str, data: PreRateRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    if user != data.rater_id:
        raise HTTPException(401, "Token mismatch")
    try:
        svc_pre_rate(club_id, data.rater_id, data.target_id, data.rating)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok"}


@app.get("/clubs/{club_id}/players/{user_id}")
def get_player(club_id: str, user_id: str, request: Request, recent: int = 0):
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    player = club.members.get(user_id)
    if not player:
        raise HTTPException(404, "Player not found")
    today = datetime.date.today()
    singles = weighted_rating(player, today)
    doubles = weighted_doubles_rating(player, today)
    singles_count = weighted_singles_matches(player)
    doubles_count = weighted_doubles_matches(player)

    result = {
        "user_id": player.user_id,
        "id": player.user_id,
        "name": player.name,
        "avatar": player.avatar,
        "avatar_url": absolute_url(request, player.avatar),
        "birth": player.birth,
        "gender": player.gender,
        "handedness": player.handedness,
        "backhand": player.backhand,
        "region": player.region,
        "joined": player.joined.isoformat(),
        "singles_rating": singles,
        "doubles_rating": doubles,
        "weighted_singles_matches": round(singles_count, 2),
        "weighted_doubles_matches": round(doubles_count, 2),
        "weighted_games_singles": round(singles_count, 2),
        "weighted_games_doubles": round(doubles_count, 2),
    }
    if recent > 0:
        from .cli import get_player_match_cards

        try:
            cards = get_player_match_cards(clubs, club_id, user_id)
        except ValueError as e:
            raise HTTPException(404, str(e))
        for c in cards:
            c["date"] = c["date"].isoformat()
        result["recent_records"] = cards[:recent]

    return result


@app.get("/clubs/{club_id}/players/{user_id}/records")
def get_player_records(
    club_id: str, user_id: str, limit: int | None = None, offset: int = 0
):
    from .cli import get_player_match_cards

    try:
        cards = get_player_match_cards(clubs, club_id, user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    # convert dates to iso strings
    for c in cards:
        c["date"] = c["date"].isoformat()
    if offset:
        cards = cards[offset:]
    if limit is not None:
        cards = cards[:limit]
    return cards


@app.get("/clubs/{club_id}/players/{user_id}/doubles_records")
def get_player_doubles_records(
    club_id: str, user_id: str, limit: int | None = None, offset: int = 0
):
    """Return doubles match history cards for a player."""
    from .cli import get_player_doubles_cards

    try:
        cards = get_player_doubles_cards(clubs, club_id, user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    for c in cards:
        c["date"] = c["date"].isoformat()
    if offset:
        cards = cards[offset:]
    if limit is not None:
        cards = cards[:limit]
    return cards


@app.get("/players/{user_id}/records")
def get_global_player_records(
    user_id: str, limit: int | None = None, offset: int = 0
):
    """Return singles match history across all clubs for a player."""
    from .cli import get_player_global_match_cards

    player = storage.get_player(user_id)
    if not player:
        raise HTTPException(404, "Player not found")

    cards = get_player_global_match_cards(player)
    for c in cards:
        c["date"] = c["date"].isoformat()

    cards.sort(key=lambda x: x["date"], reverse=True)
    if offset:
        cards = cards[offset:]
    if limit is not None:
        cards = cards[:limit]
    return cards


@app.get("/players/{user_id}/doubles_records")
def get_global_player_doubles_records(
    user_id: str, limit: int | None = None, offset: int = 0
):
    """Return doubles match history across all clubs for a player."""
    from .cli import get_player_global_doubles_cards

    player = storage.get_player(user_id)
    if not player:
        raise HTTPException(404, "Player not found")

    cards = get_player_global_doubles_cards(player)
    for c in cards:
        c["date"] = c["date"].isoformat()

    cards.sort(key=lambda x: x["date"], reverse=True)
    if offset:
        cards = cards[offset:]
    if limit is not None:
        cards = cards[:limit]
    return cards


@app.post("/clubs/{club_id}/matches")
def record_match_api(club_id: str, data: MatchCreate, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    try:
        validate_scores(data.score_a, data.score_b)
    except ValueError as e:
        raise HTTPException(400, str(e))

    svc_record_match(
        club_id,
        data.user_a,
        data.user_b,
        data.score_a,
        data.score_b,
        data.date or datetime.date.today(),
        data.weight or (format_weight_from_name(data.format) if data.format else format_weight_from_name("6_game")),
        location=data.location,
        format_name=data.format,
    )
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_matches")
def submit_match_api(club_id: str, data: PendingMatchCreate, authorization: str | None = Header(None)):

    user = require_auth(authorization)
    if user != data.initiator:
        raise HTTPException(401, "Token mismatch")

    cid = data.club_id or club_id
    try:
        validate_scores(data.score_initiator, data.score_opponent)
        svc_submit_match(
            cid,
            data.initiator,
            data.opponent,
            data.score_initiator,
            data.score_opponent,
            data.date or datetime.date.today(),
            data.weight or (format_weight_from_name(data.format) if data.format else format_weight_from_name("6_game")),
            location=data.location,
            format_name=data.format,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "pending"}


class ConfirmRequest(BaseModel):
    user_id: str


class ApproveMatchRequest(BaseModel):
    approver: str


@app.post("/clubs/{club_id}/pending_matches/{match_id}/confirm")
def confirm_match_api(club_id: str, match_id: int, data: ConfirmRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")

    try:
        svc_confirm_match(club_id, match_id, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_matches/{match_id}/reject")
def reject_match_api(club_id: str, match_id: int, data: ConfirmRequest, authorization: str | None = Header(None)):
    """Participant rejects a pending singles match."""

    user = require_auth(authorization)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")

    try:
        svc_reject_match(club_id, match_id, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "rejected"}


@app.post("/clubs/{club_id}/pending_matches/{match_id}/approve")
def approve_match_api(club_id: str, match_id: int, data: ApproveMatchRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    if user != data.approver:
        raise HTTPException(401, "Token mismatch")

    approve_pending_match(club_id, match_id, data.approver)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_matches/{match_id}/veto")
def veto_match_api(club_id: str, match_id: int, data: ApproveMatchRequest, authorization: str | None = Header(None)):
    """Admin vetoes a pending singles match."""
    user = require_auth(authorization)
    if user != data.approver:
        raise HTTPException(401, "Token mismatch")

    try:
        svc_veto_match(club_id, match_id, data.approver)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "vetoed"}


@app.post("/clubs/{club_id}/pending_doubles")
def submit_doubles_api(club_id: str, data: PendingDoublesCreate, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    if user != data.initiator:
        raise HTTPException(401, "Token mismatch")

    cid = data.club_id or club_id
    try:
        validate_scores(data.score_initiator, data.score_opponent)
        svc_submit_doubles(
            cid,
            data.initiator,
            data.partner,
            data.opponent1,
            data.opponent2,
            data.score_initiator,
            data.score_opponent,
            data.date or datetime.date.today(),
            data.weight or (
                format_weight_from_name(data.format)
                if data.format
                else format_weight_from_name("6_game")
            ),
            location=data.location,
            format_name=data.format,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "pending"}


@app.post("/clubs/{club_id}/pending_doubles/{match_id}/confirm")
def confirm_doubles_api(club_id: str, match_id: int, data: ConfirmRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")

    try:
        svc_confirm_doubles(club_id, match_id, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_doubles/{match_id}/reject")
def reject_doubles_api(club_id: str, match_id: int, data: ConfirmRequest, authorization: str | None = Header(None)):
    """Participant rejects a pending doubles match."""
    user = require_auth(authorization)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")

    try:
        svc_reject_doubles(club_id, match_id, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "rejected"}


@app.post("/clubs/{club_id}/pending_doubles/{match_id}/approve")
def approve_doubles_api(club_id: str, match_id: int, data: ApproveMatchRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    if user != data.approver:
        raise HTTPException(401, "Token mismatch")

    approve_pending_match(club_id, match_id, data.approver)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_doubles/{match_id}/veto")
def veto_doubles_api(club_id: str, match_id: int, data: ApproveMatchRequest, authorization: str | None = Header(None)):
    """Admin vetoes a pending doubles match."""

    user = require_auth(authorization)
    if user != data.approver:
        raise HTTPException(401, "Token mismatch")

    try:
        svc_veto_doubles(club_id, match_id, data.approver)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "vetoed"}


@app.post("/clubs/{club_id}/appointments")
def create_appointment(club_id: str, data: AppointmentCreate, authorization: str | None = Header(None)):
    """Create a new appointment in a club."""
    user = require_auth(authorization)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    if data.user_id not in club.members and data.user_id != club.leader_id:
        raise HTTPException(400, "Not a member")
    appt = Appointment(
        date=data.date,
        creator=data.user_id,
        location=data.location,
        info=data.info,
    )
    svc_create_appointment(club_id, appt)
    return {"status": "ok"}


@app.get("/clubs/{club_id}/appointments")
def list_appointments(club_id: str):
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    result = []
    for idx, a in enumerate(club.appointments):
        result.append(
            {
                "index": idx,
                "date": a.date.isoformat(),
                "creator": a.creator,
                "location": a.location,
                "info": a.info,
                "signups": list(a.signups),
            }
        )
    return result


@app.post("/clubs/{club_id}/appointments/{index}/signup")
def signup_appointment(club_id: str, index: int, data: SignupRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    if index >= len(club.appointments):
        raise HTTPException(404, "Appointment not found")
    if data.user_id not in club.members:
        raise HTTPException(400, "Not a member")
    svc_update_signup(club_id, index, add=data.user_id)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/appointments/{index}/cancel")
def cancel_signup(club_id: str, index: int, data: SignupRequest, authorization: str | None = Header(None)):
    user = require_auth(authorization)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    if index >= len(club.appointments):
        raise HTTPException(404, "Appointment not found")
    svc_update_signup(club_id, index, remove=data.user_id)
    return {"status": "ok"}


# ---- System management endpoints ----

def _user_summary(user: User, request: Request) -> dict[str, object]:
    """Return basic profile information with rating stats."""
    player = storage.get_player(user.user_id)
    today = datetime.date.today()
    if player:
        singles = weighted_rating(player, today)
        doubles = weighted_doubles_rating(player, today)
        singles_count = weighted_singles_matches(player)
        doubles_count = weighted_doubles_matches(player)
    else:
        singles = doubles = None
        singles_count = doubles_count = 0.0
    return {
        "user_id": user.user_id,
        "id": user.user_id,
        "name": user.name,
        "avatar_url": absolute_url(request, player.avatar if player else None),
        "singles_rating": singles,
        "doubles_rating": doubles,
        "weighted_games_singles": round(singles_count, 2),
        "weighted_games_doubles": round(doubles_count, 2),
    }


@app.get("/sys/users")
def list_all_users(
    request: Request,
    query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    """Return users optionally filtered by a search query."""
    q = query.lower() if query else None
    result = []
    for u in users.values():
        if q and q not in u.user_id.lower() and q not in u.name.lower():
            continue
        result.append(_user_summary(u, request))
    result.sort(key=lambda x: x["user_id"])
    if offset:
        result = result[offset:]
    if limit is not None:
        result = result[:limit]
    return result


@app.post("/sys/users/{user_id}/limits")
def update_user_limits(user_id: str, data: LimitsUpdateRequest, authorization: str | None = Header(None)):
    """System admin updates a user's club limits."""
    actor = require_auth(authorization)
    user = users.get(actor)
    if not user or not getattr(user, "is_sys_admin", False):
        raise HTTPException(401, "Not authorized")
    target = users.get(user_id)
    if not target:
        raise HTTPException(404, "User not found")
    try:
        svc_update_limits(
            user_id,
            max_joinable=data.max_joinable_clubs,
            max_creatable=data.max_creatable_clubs,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok"}


@app.get("/sys/clubs")
def list_all_clubs(
    query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    """Return clubs optionally filtered by a search query with stats."""
    q = query.lower() if query else None
    result = []
    for c in clubs.values():
        if q and q not in c.club_id.lower() and q not in c.name.lower():
            continue
        result.append(
            {
                "club_id": c.club_id,
                "name": c.name,
                "pending_members": len(c.pending_members),
                "pending_matches": len(c.pending_matches),
                "total_matches": len(c.matches),
            }
        )
    result.sort(key=lambda x: x["club_id"])
    if offset:
        result = result[offset:]
    if limit is not None:
        result = result[:limit]
    return result


@app.post("/sys/clubs/{club_id}/leader")
def sys_set_club_leader(club_id: str, data: SysLeaderRequest, authorization: str | None = Header(None)):
    """System admin sets club leader."""
    actor = require_auth(authorization)
    user = users.get(actor)
    if not user or not getattr(user, "is_sys_admin", False):
        raise HTTPException(401, "Not authorized")
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    try:
        svc_sys_set_leader(club_id, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok"}


@app.get("/sys/stats")
def system_stats() -> dict[str, int]:
    """Return aggregated statistics for system overview."""
    total_users = len(users)
    total_matches = sum(len(c.matches) for c in clubs.values())
    total_clubs = len(clubs)
    pending_items = sum(len(c.pending_members) + len(c.pending_matches) for c in clubs.values())
    return {
        "total_users": total_users,
        "total_matches": total_matches,
        "total_clubs": total_clubs,
        "pending_items": pending_items,
    }


@app.get("/sys/user_trend")
def system_user_trend(days: int = 7) -> list[dict[str, object]]:
    """Return cumulative user counts for the given number of days."""
    if days not in (7, 30, 90):
        raise HTTPException(400, "days must be 7, 30 or 90")

    end = datetime.date.today()
    start = end - datetime.timedelta(days=days - 1)

    join_dates: dict[str, datetime.date] = {}
    for club in clubs.values():
        for p in club.members.values():
            d = p.joined
            if p.user_id not in join_dates or d < join_dates[p.user_id]:
                join_dates[p.user_id] = d

    sorted_dates = sorted(join_dates.values())
    result = []
    total = 0
    idx = 0
    current = start
    while current <= end:
        while idx < len(sorted_dates) and sorted_dates[idx] <= current:
            total += 1
            idx += 1
        result.append({"date": current.isoformat(), "count": total})
        current += datetime.timedelta(days=1)

    return result


@app.get("/sys/match_activity")
def system_match_activity(days: int = 7) -> list[dict[str, object]]:
    """Return daily match counts for the given number of days."""
    if days not in (7, 30, 90):
        raise HTTPException(400, "days must be 7, 30 or 90")

    end = datetime.date.today()
    start = end - datetime.timedelta(days=days - 1)

    counts: dict[datetime.date, int] = {}
    for club in clubs.values():
        for m in club.matches:
            if start <= m.date <= end:
                counts[m.date] = counts.get(m.date, 0) + 1

    result = []
    current = start
    while current <= end:
        result.append({"date": current.isoformat(), "count": counts.get(current, 0)})
        current += datetime.timedelta(days=1)

    return result


@app.get("/sys/matches")
def list_all_matches(
    limit: int | None = None, offset: int = 0
) -> list[dict[str, object]]:
    """Return all singles match records across all clubs."""
    result = []
    for cid, club in clubs.items():
        for m in club.matches:
            if isinstance(m, DoublesMatch):
                continue
            result.append(
                {
                    "date": m.date.isoformat(),
                    "created_ts": m.created_ts,
                    "club_id": cid,
                    "player_a": m.player_a.user_id,
                    "player_b": m.player_b.user_id,
                    "a_name": m.player_a.name,
                    "b_name": m.player_b.name,
                    "a_avatar": m.player_a.avatar,
                    "b_avatar": m.player_b.avatar,
                    "score_a": m.score_a,
                    "score_b": m.score_b,
                    "location": m.location,
                    "format": m.format_name,
                    "a_before": m.rating_a_before,
                    "a_after": m.rating_a_after,
                    "b_before": m.rating_b_before,
                    "b_after": m.rating_b_after,
                }
            )
    result.sort(key=lambda x: (x["date"], x["created_ts"]), reverse=True)
    if offset:
        result = result[offset:]
    if limit is not None:
        result = result[:limit]
    for r in result:
        r.pop("created_ts", None)
    return result


@app.get("/sys/doubles")
def list_all_doubles(
    limit: int | None = None, offset: int = 0
) -> list[dict[str, object]]:
    """Return all doubles match records across all clubs."""
    result = []
    for cid, club in clubs.items():
        for m in club.matches:
            if not isinstance(m, DoublesMatch):
                continue
            result.append(
                {
                    "date": m.date.isoformat(),
                    "created_ts": m.created_ts,
                    "club_id": cid,
                    "a1": m.player_a1.user_id,
                    "a2": m.player_a2.user_id,
                    "b1": m.player_b1.user_id,
                    "b2": m.player_b2.user_id,
                    "a1_name": m.player_a1.name,
                    "a2_name": m.player_a2.name,
                    "b1_name": m.player_b1.name,
                    "b2_name": m.player_b2.name,
                    "a1_avatar": m.player_a1.avatar,
                    "a2_avatar": m.player_a2.avatar,
                    "b1_avatar": m.player_b1.avatar,
                    "b2_avatar": m.player_b2.avatar,
                    "score_a": m.score_a,
                    "score_b": m.score_b,
                    "location": m.location,
                    "format": m.format_name,
                    "rating_a1_before": m.rating_a1_before,
                    "rating_a2_before": m.rating_a2_before,
                    "rating_b1_before": m.rating_b1_before,
                    "rating_b2_before": m.rating_b2_before,
                    "rating_a1_after": m.rating_a1_after,
                    "rating_a2_after": m.rating_a2_after,
                    "rating_b1_after": m.rating_b1_after,
                    "rating_b2_after": m.rating_b2_after,
                }
            )
    result.sort(key=lambda x: (x["date"], x["created_ts"]), reverse=True)
    if offset:
        result = result[offset:]
    if limit is not None:
        result = result[:limit]
    for r in result:
        r.pop("created_ts", None)
    return result


@app.get("/sys/pending_matches")
def list_all_pending_matches(authorization: str | None = Header(None)) -> list[dict[str, object]]:
    """Return all pending singles matches awaiting admin review."""
    uid = require_auth(authorization)
    user = users.get(uid)
    if not user or not getattr(user, "is_sys_admin", False):
        raise HTTPException(401, "Not authorized")

    from .models import DoublesMatch
    from .cli import cleanup_pending_matches

    combined: list[dict[str, object]] = []
    for cid, club in clubs.items():
        cleanup_pending_matches(club)
        for idx, m in enumerate(club.pending_matches):
            if isinstance(m, DoublesMatch):
                continue
            if m.status in {"rejected", "vetoed"}:
                continue
            entry = {
                "club_id": cid,
                "index": idx,
                "date": m.date.isoformat(),
                "player_a": m.player_a.user_id,
                "player_b": m.player_b.user_id,
                "score_a": m.score_a,
                "score_b": m.score_b,
                "confirmed_a": m.confirmed_a,
                "confirmed_b": m.confirmed_b,
                "location": m.location,
                "format_name": m.format_name,
                "status": m.status,
            }
            pa = club.members.get(m.player_a.user_id)
            pb = club.members.get(m.player_b.user_id)
            entry["player_a_name"] = pa.name if pa else m.player_a.user_id
            entry["player_b_name"] = pb.name if pb else m.player_b.user_id
            entry["rating_a_before"] = pa.singles_rating if pa else None
            entry["rating_b_before"] = pb.singles_rating if pb else None
            entry["player_a_avatar"] = pa.avatar if pa else None
            entry["player_b_avatar"] = pb.avatar if pb else None
            if m.initiator and (submitter := club.members.get(m.initiator)):
                entry["submitted_by_player_name"] = submitter.name

            ready = m.confirmed_a and m.confirmed_b
            if m.status == "vetoed":
                days_left = 3 - (datetime.date.today() - (m.status_date or datetime.date.today())).days
                entry["display_status_text"] = f"已否决，将在{days_left}日后删除"
                entry["can_approve"] = False
                entry["can_veto"] = False
            elif m.status == "rejected":
                days_left = 3 - (datetime.date.today() - (m.status_date or datetime.date.today())).days
                entry["display_status_text"] = f"已拒绝，将在{days_left}日后删除"
                entry["can_approve"] = False
                entry["can_veto"] = False
            else:
                entry["display_status_text"] = "双方已确认，请审核" if ready else "待确认"
                entry["can_approve"] = ready
                entry["can_veto"] = ready

            combined.append(entry)

    combined.sort(key=lambda x: x["date"], reverse=True)
    return combined


@app.get("/sys/pending_doubles")
def list_all_pending_doubles(authorization: str | None = Header(None)) -> list[dict[str, object]]:
    """Return all pending doubles matches awaiting admin review."""
    uid = require_auth(authorization)
    user = users.get(uid)
    if not user or not getattr(user, "is_sys_admin", False):
        raise HTTPException(401, "Not authorized")

    from .models import DoublesMatch
    from .cli import cleanup_pending_matches

    combined: list[dict[str, object]] = []
    for cid, club in clubs.items():
        cleanup_pending_matches(club)
        for idx, m in enumerate(club.pending_matches):
            if not isinstance(m, DoublesMatch):
                continue
            if m.status in {"rejected", "vetoed"}:
                continue
            entry = {
                "club_id": cid,
                "index": idx,
                "date": m.date.isoformat(),
                "a1": m.player_a1.user_id,
                "a2": m.player_a2.user_id,
                "b1": m.player_b1.user_id,
                "b2": m.player_b2.user_id,
                "score_a": m.score_a,
                "score_b": m.score_b,
                "confirmed_a": m.confirmed_a,
                "confirmed_b": m.confirmed_b,
                "location": m.location,
                "format_name": m.format_name,
                "status": m.status,
            }
            a1 = club.members.get(m.player_a1.user_id)
            a2 = club.members.get(m.player_a2.user_id)
            b1 = club.members.get(m.player_b1.user_id)
            b2 = club.members.get(m.player_b2.user_id)
            entry["a1_name"] = a1.name if a1 else m.player_a1.user_id
            entry["a2_name"] = a2.name if a2 else m.player_a2.user_id
            entry["b1_name"] = b1.name if b1 else m.player_b1.user_id
            entry["b2_name"] = b2.name if b2 else m.player_b2.user_id
            entry["rating_a1_before"] = a1.doubles_rating if a1 else None
            entry["rating_a2_before"] = a2.doubles_rating if a2 else None
            entry["rating_b1_before"] = b1.doubles_rating if b1 else None
            entry["rating_b2_before"] = b2.doubles_rating if b2 else None
            entry["a1_avatar"] = a1.avatar if a1 else None
            entry["a2_avatar"] = a2.avatar if a2 else None
            entry["b1_avatar"] = b1.avatar if b1 else None
            entry["b2_avatar"] = b2.avatar if b2 else None
            if m.initiator and (submitter := club.members.get(m.initiator)):
                entry["submitted_by_player_name"] = submitter.name

            ready = m.confirmed_a and m.confirmed_b
            if m.status == "vetoed":
                days_left = 3 - (datetime.date.today() - (m.status_date or datetime.date.today())).days
                entry["display_status_text"] = f"已否决，将在{days_left}日后删除"
                entry["can_approve"] = False
                entry["can_veto"] = False
            elif m.status == "rejected":
                days_left = 3 - (datetime.date.today() - (m.status_date or datetime.date.today())).days
                entry["display_status_text"] = f"已拒绝，将在{days_left}日后删除"
                entry["can_approve"] = False
                entry["can_veto"] = False
            else:
                entry["display_status_text"] = "双方已确认，请审核" if ready else "待确认"
                entry["can_approve"] = ready
                entry["can_veto"] = ready

            combined.append(entry)

    combined.sort(key=lambda x: x["date"], reverse=True)
    return combined


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
