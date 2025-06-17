# new service functions extracted from api
import datetime
from fastapi import HTTPException
from .. import storage
from ..models import DoublesMatch
from .auth import require_auth

# state proxies will be provided by api during runtime
from .. import api


def list_pending_doubles_service(club_id: str, token: str):
    uid = require_auth(token)
    club = api.clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    from ..cli import cleanup_pending_matches

    cleanup_pending_matches(club)

    admins = {club.leader_id, *club.admin_ids}
    result = []
    today = datetime.date.today()
    for idx, m in sorted(
        enumerate(club.pending_matches),
        key=lambda x: (x[1].date, x[1].created_ts),
        reverse=True,
    ):
        if not isinstance(m, DoublesMatch):
            continue
        team_a = {m.player_a1.user_id, m.player_a2.user_id}
        team_b = {m.player_b1.user_id, m.player_b2.user_id}
        participants = team_a | team_b
        if m.status == "rejected":
            if uid != m.initiator:
                continue
        elif m.status == "vetoed":
            if uid not in participants:
                continue
        elif uid not in participants:
            if uid in admins and m.confirmed_a and m.confirmed_b:
                pass
            else:
                continue

        entry = {
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

        is_admin = uid in admins

        if uid == m.initiator:
            role = "submitter"
        elif uid in team_a:
            role = "teammate"
        elif uid in team_b:
            role = "opponent"
        elif is_admin:
            role = "admin"
        else:
            role = "viewer"

        confirmed_self = None
        confirmed_opp = None
        if uid in team_a:
            confirmed_self = m.confirmed_a
            confirmed_opp = m.confirmed_b
        elif uid in team_b:
            confirmed_self = m.confirmed_b
            confirmed_opp = m.confirmed_a

        can_confirm = False
        can_decline = False
        status_text = ""

        if m.status == "rejected":
            days_left = 3 - (today - (m.status_date or today)).days
            status_text = f"对手已拒绝，该记录将在{days_left}日后自动删除"
        elif m.status == "vetoed":
            days_left = 3 - (today - (m.status_date or today)).days
            status_text = f"管理员审核未通过，该记录将在{days_left}日后自动删除"
        else:
            if role == "submitter":
                if not (m.confirmed_a and m.confirmed_b):
                    status_text = "您已提交，等待对手确认"
                    wait_days = (today - m.created).days
                    if wait_days >= 4:
                        left = 7 - wait_days
                        status_text = f"该记录长时间未得到对手确认，将在{left}日后自动删除"
                else:
                    status_text = "对手已确认，等待管理员审核"
                    wait_days = (today - (m.confirmed_on or m.created)).days
                    if wait_days >= 4:
                        left = 7 - wait_days
                        status_text = f"该记录长时间未得到管理员审核，将在{left}日后自动删除"
            elif role in {"teammate", "opponent"}:
                if role == "teammate":
                    if not m.confirmed_b:
                        status_text = "您的队友已确认，等待对手确认"
                        wait_days = (today - m.created).days
                        if wait_days >= 4:
                            left = 7 - wait_days
                            status_text = f"该记录长时间未得到对手确认，将在{left}日后自动删除"
                    else:
                        status_text = "对手和队友已确认，等待管理员审核"
                        wait_days = (today - (m.confirmed_on or m.created)).days
                        if wait_days >= 4:
                            left = 7 - wait_days
                            status_text = f"该记录长时间未得到管理员审核，将在{left}日后自动删除"
                else:  # opponent
                    if confirmed_self is False:
                        can_confirm = True
                        can_decline = True
                        status_text = "对手提交了比赛战绩，请确认"
                    else:
                        status_text = "您的队友已确认，等待管理员审核"
                        wait_days = (today - (m.confirmed_on or m.created)).days
                        if wait_days >= 4:
                            left = 7 - wait_days
                            status_text = f"该记录长时间未得到管理员审核，将在{left}日后自动删除"
            elif role == "admin":
                status_text = "双方已确认，请审核"
            else:
                if m.confirmed_a and m.confirmed_b:
                    status_text = "等待管理员审核"
                else:
                    status_text = "待确认"

        if not m.status and is_admin and m.confirmed_a and m.confirmed_b:
            role = "admin"
            status_text = "双方已确认，请审核"
            can_confirm = False
            can_decline = False

        entry.update(
            {
                "display_status_text": status_text,
                "can_confirm": can_confirm,
                "can_decline": can_decline,
                "current_user_role_in_match": role,
                "submitted_by_player_id": m.initiator,
            }
        )

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

        result.append(entry)

    return result


def list_pending_matches_service(club_id: str, token: str):
    uid = require_auth(token)
    club = api.clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    from ..cli import cleanup_pending_matches

    cleanup_pending_matches(club)
    result = []
    admins = {club.leader_id, *club.admin_ids}
    today = datetime.date.today()
    for idx, m in sorted(
        enumerate(club.pending_matches),
        key=lambda x: (x[1].date, x[1].created_ts),
        reverse=True,
    ):
        if isinstance(m, DoublesMatch):
            continue
        participants = {m.player_a.user_id, m.player_b.user_id}
        if m.status == "rejected":
            if uid != m.initiator:
                continue
        elif m.status == "vetoed":
            if uid not in participants:
                continue
        elif uid not in participants:
            if uid in admins and m.confirmed_a and m.confirmed_b:
                pass
            else:
                continue

        entry = {
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

        is_admin = uid in admins

        if uid == m.initiator:
            role = "submitter"
        elif uid in participants:
            role = "opponent"
        elif is_admin:
            role = "admin"
        else:
            role = "viewer"

        confirmed_self = None
        confirmed_opp = None
        if uid == m.player_a.user_id:
            confirmed_self = m.confirmed_a
            confirmed_opp = m.confirmed_b
        elif uid == m.player_b.user_id:
            confirmed_self = m.confirmed_b
            confirmed_opp = m.confirmed_a

        can_confirm = False
        can_decline = False
        status_text = ""

        if m.status == "rejected":
            days_left = 3 - (today - (m.status_date or today)).days
            status_text = f"对手已拒绝，该记录将在{days_left}日后自动删除"
        elif m.status == "vetoed":
            days_left = 3 - (today - (m.status_date or today)).days
            status_text = f"管理员审核未通过，该记录将在{days_left}日后自动删除"
        else:
            if role == "submitter":
                if not (m.confirmed_a and m.confirmed_b):
                    status_text = "您已提交，等待对手确认"
                    wait_days = (today - m.created).days
                    if wait_days >= 4:
                        left = 7 - wait_days
                        status_text = f"该记录长时间未得到对手确认，将在{left}日后自动删除"
                else:
                    status_text = "对手已确认，等待管理员审核"
                    wait_days = (today - (m.confirmed_on or m.created)).days
                    if wait_days >= 4:
                        left = 7 - wait_days
                        status_text = f"该记录长时间未得到管理员审核，将在{left}日后自动删除"
            elif role == "opponent":
                if confirmed_self is False:
                    can_confirm = True
                    can_decline = True
                    status_text = "对手提交了比赛战绩，请确认"
                else:
                    status_text = "您已确认，等待管理员审核"
                    wait_days = (today - (m.confirmed_on or m.created)).days
                    if wait_days >= 4:
                        left = 7 - wait_days
                        status_text = f"该记录长时间未得到管理员审核，将在{left}日后自动删除"
            elif role == "admin":
                status_text = "双方已确认，请审核"
            else:
                if m.confirmed_a and m.confirmed_b:
                    status_text = "等待管理员审核"
                else:
                    status_text = "待确认"

        if not m.status and is_admin and m.confirmed_a and m.confirmed_b:
            role = "admin"
            status_text = "双方已确认，请审核"
            can_confirm = False
            can_decline = False

        entry.update(
            {
                "display_status_text": status_text,
                "can_confirm": can_confirm,
                "can_decline": can_decline,
                "current_user_role_in_match": role,
                "submitted_by_player_id": m.initiator,
            }
        )

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

        result.append(entry)

    return result


def list_global_pending_doubles_service(user_id: str, token: str):
    uid = require_auth(token)
    if uid != user_id:
        raise HTTPException(401, "Token mismatch")

    combined = []
    for cid, club in api.clubs.items():
        try:
            entries = list_pending_doubles_service(cid, token)
        except HTTPException:
            continue
        is_admin = uid == club.leader_id or uid in club.admin_ids
        for e in entries:
            e["club_id"] = cid
            ready = e.get("confirmed_a") and e.get("confirmed_b") and not e.get("status")
            e["can_approve"] = is_admin and ready
            e["can_veto"] = e["can_approve"]
            combined.append(e)

    combined.sort(key=lambda x: x["date"], reverse=True)
    return combined


def list_global_pending_matches_service(user_id: str, token: str):
    uid = require_auth(token)
    if uid != user_id:
        raise HTTPException(401, "Token mismatch")

    combined = []
    for cid, club in api.clubs.items():
        try:
            entries = list_pending_matches_service(cid, token)
        except HTTPException:
            continue
        is_admin = uid == club.leader_id or uid in club.admin_ids
        for e in entries:
            e["club_id"] = cid
            ready = e.get("confirmed_a") and e.get("confirmed_b") and not e.get("status")
            e["can_approve"] = is_admin and ready
            e["can_veto"] = e["can_approve"]
            combined.append(e)

    combined.sort(key=lambda x: x["date"], reverse=True)
    return combined

