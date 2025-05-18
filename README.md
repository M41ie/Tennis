# Tennis Rating Prototype

This repository contains a prototype implementation of a tennis rating system
based on the requirements in the `Original Requirement` file. It allows creation of
clubs, registration of players and recording of match scores. Ratings are
updated with a simplified Elo style algorithm and are time weighted according to
the last 20 matches.

## Usage

```
python3 -m tennis.cli create_club CLUB_ID NAME [--logo LOGO] [--region REGION]
python3 -m tennis.cli add_player CLUB_ID USER_ID NAME
python3 -m tennis.cli pre_rate CLUB_ID RATER_ID TARGET_ID RATING
python3 -m tennis.cli record_match CLUB_ID USER_A USER_B SCORE_A SCORE_B [--date YYYY-MM-DD] [--format NAME | --weight W]
```

Use `pre_rate` for club members to vote on a new player's skill before any matches are recorded. The player's initial rating is the weighted average of these votes based on each rater's match count.

Data is saved to `data.json` in the repository root.

Available format names:

- `6_game` – standard six game set (`weight=1.0`)
- `4_game` – shortened four game set (`weight=0.7`)
- `tb11` – tiebreak to 11 (`weight=0.3`)
- `tb7` – tiebreak to 7 (`weight=0.2`)

### Testing

To run the test suite:

```bash
# Install test dependencies
python3 -m pip install pytest

# Execute the tests from the repository root
pytest
```
