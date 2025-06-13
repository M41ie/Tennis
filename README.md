# Tennis Rating Prototype

This repository contains a prototype implementation of a tennis rating system based on the requirements in the `Original Requirement` file. It allows creation of clubs, registration of players and recording of match scores. Ratings are updated with a simplified Elo style algorithm and the post-match value becomes the player's current rating without averaging previous results.

## Usage

```
python3 -m tennis.cli register_user USER_ID NAME PASSWORD [--allow-create]
python3 -m tennis.cli create_club USER_ID CLUB_ID NAME [--logo LOGO] [--region REGION]
python3 -m tennis.cli add_player CLUB_ID USER_ID NAME
python3 -m tennis.cli pre_rate CLUB_ID RATER_ID TARGET_ID RATING
python3 -m tennis.cli record_match CLUB_ID USER_A USER_B SCORE_A SCORE_B [--date YYYY-MM-DD] [--format NAME | --weight W]
python3 -m tennis.cli submit_match CLUB_ID INITIATOR OPPONENT SCORE_I SCORE_O [--date YYYY-MM-DD] [--format NAME | --weight W]
python3 -m tennis.cli confirm_match CLUB_ID INDEX USER_ID
python3 -m tennis.cli approve_match CLUB_ID INDEX APPROVER
```

When calling `register_user` you can omit the `USER_ID` argument. The server will
assign the next available alphabetic ID automatically (A, B, ..., Z, AA, AB,
...).

Creating a club automatically makes the creator a member. This also counts
toward their joined club limit (default 5).

Use `pre_rate` for club members to vote on a new player's skill before any matches are recorded. The player's initial rating is the weighted average of these votes based on each rater's match count.

Data is stored in a SQLite database `tennis.db` in the repository root.

Available format names:

- `6_game` – standard six game set (`weight=1.0`)
- `4_game` – shortened four game set (`weight=0.7`)
- `tb10` – tiebreak to 10 (`weight=0.25`)
- `tb7` – tiebreak to 7 (`weight=0.15`)

### REST API

You can run a simple REST server with FastAPI. Install the required
packages first:

```bash
python3 -m pip install -r requirements.txt
python3 -m tennis.api
```

The API exposes endpoints to create clubs, add players and record matches.

Authentication is required for any operation that modifies data. Obtain a token
by logging in:

```bash
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/json" \
     -d '{"user_id": "USER", "password": "PW"}'
```
You may supply a username instead of `USER` and the server will look up the
corresponding ID automatically.

Include the returned `token` value in the `token` field when calling protected
endpoints. Creating a club or adding a player requires the caller's token, e.g.:

```bash
curl -X POST http://localhost:8000/clubs \
     -H "Content-Type: application/json" \
     -d '{"name": "Club", "user_id": "USER", "token": "TOKEN"}'
```
The API automatically assigns a `club_id` and returns it in the response.

To invalidate a token call `/logout` with the token value.

To update profile information before joining a club, use the global endpoint:

```bash
curl -X PATCH http://localhost:8000/players/USER \
     -H "Content-Type: application/json" \
     -d '{"user_id":"USER","token":"TOKEN","name":"New"}'
```
This accepts the same fields as the club specific `/clubs/{club_id}/players/{user_id}` route.

Similarly, recording a match uses:

```bash
curl -X POST http://localhost:8000/clubs/c1/matches \
     -H "Content-Type: application/json" \
     -d '{"user_id":"USER","user_a":"A","user_b":"B","score_a":6,"score_b":4,"token":"TOKEN"}'
```

Pending matches can be reviewed via (authentication required):

```bash
curl "http://localhost:8000/clubs/c1/pending_matches?token=TOKEN"
curl "http://localhost:8000/clubs/c1/pending_doubles?token=TOKEN"
```

Each item contains the index to use when confirming, rejecting or approving the match.

Use the following authenticated endpoints to respond:

```bash
curl -X POST http://localhost:8000/clubs/c1/pending_matches/INDEX/confirm \
     -H "Content-Type: application/json" \
     -d '{"user_id":"USER","token":"TOKEN"}'
curl -X POST http://localhost:8000/clubs/c1/pending_matches/INDEX/reject \
     -H "Content-Type: application/json" \
     -d '{"user_id":"USER","token":"TOKEN"}'
curl -X POST http://localhost:8000/clubs/c1/pending_matches/INDEX/approve \
     -H "Content-Type: application/json" \
     -d '{"approver":"ADMIN","token":"TOKEN"}'
```

Doubles matches use the corresponding `/pending_doubles/...` routes.

### Mini App

The `miniapp` directory contains a very small WeChat Mini Program that
demonstrates how a front‑end could consume the REST API. It provides three
pages:

* **Leaderboard** – displays player ratings with basic club and rating filters
* **Match Records** – shows the logged in user's recent matches
* **Profile** – displays user information and links to club management

To run the mini program, build it with the WeChat Developer Tools and start the
REST API server as shown above.

### Testing

To run the test suite:

```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Execute the tests from the repository root
pytest
```

### Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for instructions on running the API server, initializing the database and building the mini program.

