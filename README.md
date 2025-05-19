# Tennis Rating Prototype

This repository contains a prototype implementation of a tennis rating system
based on the requirements in the `Original Requirement` file. It allows creation of
clubs, registration of players and recording of match scores. Ratings are
updated with a simplified Elo style algorithm and are time weighted according to
the last 20 matches.

## Usage

```
python3 -m tennis.cli register_user USER_ID NAME PASSWORD [--allow-create]
python3 -m tennis.cli create_club USER_ID CLUB_ID NAME [--logo LOGO] [--region REGION]
python3 -m tennis.cli add_player CLUB_ID USER_ID NAME
python3 -m tennis.cli pre_rate CLUB_ID RATER_ID TARGET_ID RATING
python3 -m tennis.cli record_match CLUB_ID USER_A USER_B SCORE_A SCORE_B [--date YYYY-MM-DD] [--format NAME | --weight W]
python3 -m tennis.cli request_join CLUB_ID USER_ID
python3 -m tennis.cli approve_member CLUB_ID APPROVER_ID USER_ID [--admin]
```

Use `pre_rate` for club members to vote on a new player's skill before any matches are recorded. The player's initial rating is the weighted average of these votes based on each rater's match count.

Data is stored in a SQLite database `tennis.db` in the repository root.

Basic account management is available. Register users with `register_user` and
only accounts marked with `--allow-create` can create clubs. Players must
request to join a club and be approved by the club leader or an administrator.

Available format names:

- `6_game` – standard six game set (`weight=1.0`)
- `4_game` – shortened four game set (`weight=0.7`)
- `tb11` – tiebreak to 11 (`weight=0.3`)
- `tb10` – tiebreak to 10 (`weight=0.27`)
- `tb7` – tiebreak to 7 (`weight=0.2`)

### REST API

You can run a simple REST server with FastAPI:

```bash
python3 -m tennis.api
```

The API exposes endpoints to create clubs, add players and record matches.

### Testing

To run the test suite:

```bash
# Install test dependencies
python3 -m pip install pytest

# Execute the tests from the repository root
pytest
```
