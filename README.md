# Tennis Rating Prototype

This repository contains a prototype implementation of a tennis rating system. It allows creation of clubs, registration of players and recording of match scores. Ratings are updated with a simplified Elo style algorithm and the post-match value becomes the player's current rating without averaging previous results.

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

When calling `register_user` you can omit the `USER_ID` argument. The server
assigns the next available alphabetic ID automatically (A, B, ..., Z, AA, AB,
...). The very first account registered in this manner receives ID `A` and is
marked as the system administrator. Passing `use_uuid=True` will instead
generate a random seven character identifier. No administrator account is
created automatically in this mode.

Creating a club automatically makes the creator a member. This also counts
toward their joined club limit (default 5).

Use `pre_rate` for club members to vote on a new player's skill before any matches are recorded. The player's initial rating is the weighted average of these votes based on each rater's match count.

Data is stored in a SQLite database `tennis.db` in the repository root by
default. Set the `DATABASE_URL` environment variable to a PostgreSQL DSN to use
a server instead. The schema contains tables for `users`, `clubs`, `players`,
`club_members`, `matches`, `pending_matches`, `appointments`, `club_meta`,
`messages` and `auth_tokens`. Each API call writes directly to these tables so
the service can operate in a stateless manner.

If the `REDIS_URL` environment variable is set the application caches loaded
club and user data in Redis for faster access. A running Redis server is
required for this feature, for example `export REDIS_URL=redis://localhost:6379/0`.
Cached entries expire automatically after a few minutes.
Every write operation bumps a `CACHE_VERSION` value in Redis so that multiple
API workers reload their local cache when the version changes.

### Environment configuration

Configuration values are loaded from environment variables. When
`python-dotenv` is installed a `.env` file in the repository root will be
read automatically. Example contents:

```ini
DATABASE_URL=postgresql:///tennis
REDIS_URL=redis://localhost:6379/0
WECHAT_APPID=your-app-id
WECHAT_SECRET=your-secret
```

Install `python-dotenv` with `pip install python-dotenv` if you want to use a
`.env` file during development.

When caching is enabled via `REDIS_URL` the server stores a `CACHE_VERSION`
value in Redis. All workers compare this version on each request and reload
their cached data whenever it changes. Ensure all processes point to the same
Redis instance.

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

Include the returned `token` value in the `Authorization` header when calling
protected endpoints:

```bash
Authorization: Bearer TOKEN
```

Creating a club or adding a player requires authentication, e.g.:

```bash
curl -X POST http://localhost:8000/clubs \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer TOKEN" \
     -d '{"name": "Club", "user_id": "USER"}'
```
The API automatically assigns a `club_id` (a `uuid4` hex string) and returns it
in the response.

To invalidate a token call `/logout` with the token value.

To update profile information before joining a club, use the global endpoint:

```bash
curl -X PUT http://localhost:8000/players/USER \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer TOKEN" \
     -d '{"user_id":"USER","name":"New"}'
```
This accepts the same fields as the club specific `/clubs/{club_id}/players/{user_id}` route.

Use `/players/{user_id}/friends` to retrieve aggregated interaction statistics
with opponents and doubles partners. Each entry in the response contains the
friend's `user_id`, name, avatar and the weighted counts and wins.

Similarly, recording a match uses:

```bash
curl -X POST http://localhost:8000/clubs/c1/matches \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer TOKEN" \
     -d '{"user_id":"USER","user_a":"A","user_b":"B","score_a":6,"score_b":4}'
```

Pending matches can be reviewed via (authentication required):

```bash
curl -H "Authorization: Bearer TOKEN" "http://localhost:8000/clubs/c1/pending_matches"
curl -H "Authorization: Bearer TOKEN" "http://localhost:8000/clubs/c1/pending_doubles"
```

Each item contains the index to use when confirming, rejecting or approving the match.

Use the following authenticated endpoints to respond:

```bash
curl -X POST http://localhost:8000/clubs/c1/pending_matches/INDEX/confirm \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer TOKEN" \
     -d '{"user_id":"USER"}'
curl -X POST http://localhost:8000/clubs/c1/pending_matches/INDEX/reject \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer TOKEN" \
     -d '{"user_id":"USER"}'
curl -X POST http://localhost:8000/clubs/c1/pending_matches/INDEX/approve \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer TOKEN" \
     -d '{"approver":"ADMIN"}'
```

Doubles matches use the corresponding `/pending_doubles/...` routes.

### Upload

Use `/upload/image` to store images on the server.

```
POST /upload/image
```

Files larger than 2&nbsp;MB are rejected with status code `413`.

Send the image in a multipart form field named `file`. The response contains
the relative URL of the stored file:

```json
{ "url": "/static/media/avatars/<filename>" }
```

Example:

```bash
curl -X POST http://localhost:8000/upload/image \
     -F "file=@example.jpg"
```

### Mini App

The `miniapp` directory contains a very small WeChat Mini Program that
demonstrates how a front‑end could consume the REST API. It provides three
pages:

* **Leaderboard** – displays player ratings with basic club and rating filters
* **Match Records** – shows the logged in user's recent matches. Approved
  entries are ordered by when they were approved and fall back to their
  original order if no timestamp is present
* **Profile** – displays user information (always from global data) and links to club management

To run the mini program, build it with the WeChat Developer Tools and start the
REST API server as shown above.

To keep the front‑end code healthy an ESLint configuration lives in
`miniapp/`. Install the Node.js dependencies and run the linter:

```bash
cd miniapp
npm install
npm run lint
```

Basic front‑end tests using `miniprogram-simulate` can be executed with `npm test`.

### Web Admin

The repository also contains a tiny web based dashboard under `static/admin`.
Start the API server and open `http://localhost:8000/admin/` in a browser to
see basic statistics and a user search page. The interface is intentionally
minimal but demonstrates how the REST API can be consumed from a regular web
application.

### WeChat subscription messages

The mini program requests message push authorization only when needed. The
backend tracks quota usage per **scene** identifier:

- `club_manage` – leaders and admins receive notifications about pending join
  requests. Permission is requested when an admin approves or rejects an
  application.
- `join_club` – applicants are informed when their join request is approved or
  rejected. Authorization happens when submitting the request.
- `match_confirm` – opponents are notified of a newly created match. The
  subscription is requested when opening the pending match list.
- `match_audit` – club staff are asked to review confirmed matches. Permission is
  requested when they tap the approve or veto buttons.
- `match_create` – players are informed when a match is rejected or approved.
  Authorization occurs after submitting a match or confirming an opponent's
  match.

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

