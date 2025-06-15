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

The SQLite database contains these tables: `users`, `players`, `clubs`,
`club_members`, `matches`, `pending_matches`, `appointments`, `club_meta`,
`messages` and `auth_tokens`.

## 3. Start the API server

Launch the FastAPI application. A local `tennis.db` SQLite database will be created automatically if it does not exist.

```bash
python3 -m tennis.api
```

The server listens on `http://localhost:8000` by default. Set the `WECHAT_APPID` and `WECHAT_SECRET` environment variables if you need WeChat login support.

All runtime data is persisted in SQLite. Because the API accesses the database
for every request you can run multiple stateless instances behind a load
balancer.

## 4. Import the mini program

1. Open WeChat Developer Tools and choose **Import**.
2. Select the `miniapp` directory from this repository.
3. Configure the request domain to point to the API server URL.
4. For production deployments edit `miniapp/app.js` and change the `BASE_URL` constant from `http://localhost:8000` to your production domain.
5. Build and upload the mini program through the developer tools.
