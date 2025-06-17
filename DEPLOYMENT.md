# Deployment Guide

This walkthrough covers installing dependencies, running tests, starting the API and deploying the WeChat mini program.

## 1. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

## 2. Run tests

```bash
pytest
```

To run the application with PostgreSQL create a database and export a connection
string, for example:

```bash
createdb tennis
export DATABASE_URL=postgresql:///tennis
```

The schema will be created automatically on first start.

The default SQLite database contains these tables: `users`, `players`, `clubs`,
`club_members`, `matches`, `pending_matches`, `appointments`, `club_meta`,
`messages` and `auth_tokens`.

To enable caching export a `REDIS_URL` pointing to a running Redis server. For
example install Redis locally and set `export REDIS_URL=redis://localhost:6379/0`.

## 3. Start the API server

Launch the FastAPI application. A local `tennis.db` SQLite database will be created automatically if it does not exist. Set `DATABASE_URL` to a PostgreSQL DSN if you prefer using a server.

```bash
python3 -m tennis.api
```

The server listens on `http://localhost:8000` by default. Set the `WECHAT_APPID` and `WECHAT_SECRET` environment variables if you need WeChat login support.

All runtime data is persisted in SQLite or PostgreSQL depending on
`DATABASE_URL`. Because the API accesses the database for every request you can
run multiple stateless instances behind a load balancer.

## 4. Import the mini program

1. Open WeChat Developer Tools and choose **Import**.
2. Select the `miniapp` directory from this repository.
3. Configure the request domain to point to the API server URL.
4. Adjust the API endpoints in `miniapp/config.js`. The file contains
   `BASE_URL` values for the WeChat `develop`, `trial` and `release` modes.
   When building the mini program the appropriate entry is chosen based on the
   compilation environment.
5. Build and upload the mini program through the developer tools.
