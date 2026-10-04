# Professor Search Frontend

A small React + TypeScript interface for email/password registration, Google sign-in,
account linking, protected profile access, refresh-cookie session restoration, and
logout against the real FastAPI backend. It does not create mock accounts or simulate
successful logins.

## Run With Docker

Only Docker with Compose v2 is required. Frontend and backend have separate Compose
projects. Start the backend first from the repository root:

```sh
cd backend
docker compose up --build -d --wait
```

Then start the frontend from its own directory:

```sh
cd ../frontend
docker compose up --build -d --wait
```

On subsequent starts, run `docker compose up -d --wait` directly from `frontend/`.
Use `--build` after changing frontend code.

Open **http://localhost:3000**. FastAPI docs remain at http://localhost:8000/docs.
The backend project manages MariaDB, migrations, and auth. The frontend project
manages only Nginx and the React build, without starting or stopping backend containers.
No host Node.js, npm, Python, or virtual environment is needed.

If this is a fresh checkout without backend configuration, run this once from
`backend/` before starting the stack:

```sh
LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)" \
  docker compose -f docker-compose.setup.yml run --build --rm setup
```

See [backend setup](../backend/README.md) for configuration and Google backend details.

## Check Registration And Login

1. Open **Create account**, enter an email, and choose a password of 12-128 characters.
2. Submit. A successful response shows **Registration successful** and the account ID.
3. Select **Check profile** to confirm the protected `/api/v1/auth/me` endpoint works.
4. Reload the page. The HttpOnly refresh cookie restores the session.
5. Select **Sign out**, then sign in again with the same email and password.
6. Try a wrong password or register the same email again to see real API errors.

Accounts created here are real records in MariaDB and persist across restarts.
The UI sends `X-CSRF-Protection: 1` and cookies automatically; no Swagger header entry
or token copying is needed.

## Enable Google Sign-In

The **Sign in with Google** button appears on both account-access tabs. Until the
backend has a Google client ID, it stays disabled and displays
"Google sign-in is not configured yet." Email/password access remains available.

1. Create an OAuth client of type **Web application** in
  [Google Auth Platform](https://console.cloud.google.com/auth/clients).
2. Configure the app's branding/consent screen and test users if it is in testing mode.
3. Add `http://localhost` and `http://localhost:3000` to **Authorized JavaScript origins**.
  Add the actual frontend origin too if using another port or domain.
4. Set `GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com` in `backend/.env`.
  No client secret or redirect URI is needed for this popup ID-token flow.
5. From `backend/`, reload the API configuration:

```sh
docker compose up -d --force-recreate auth
```

Reload http://localhost:3000, or use the Google retry control. The frontend obtains
the public client ID and a browser-bound, single-use nonce from the backend; no Vite
environment variable or frontend rebuild is needed when changing the client ID.
Google's official Identity Services button returns an ID token, which the backend
verifies before issuing the same app session used by email/password login. The Google
ID token is not saved in browser storage. Google One Tap and automatic account selection
are disabled.

If a password account already uses the Google email, sign in with that password first,
select **Link Google** in the account view, then select the matching Google account.
The backend requires an authenticated session and matching email before linking.

Expired challenges, provider failures, and rejected token exchanges offer a fresh
attempt through the retry control; tokens are never retried automatically. Opening
Google sign-in in another tab can replace the shared challenge cookie, requiring a
fresh attempt in the first tab.

Real Google sign-in requires your own configured OAuth client and consent. Automated
tests cover the frontend callbacks and backend contract using controlled responses;
they do not sign into a real Google account.

## Containers And Requests

```text
Browser :3000 -> Nginx frontend :8080 -> static React build
                                   -> /api/* -> auth:8000 -> MariaDB
```

The backend creates the `professor-auth-network` Docker network; the frontend joins
it as an external network. Only the auth API joins both this network and the backend's
private database network. Start the backend first if Docker reports that the external
network does not exist. If the backend is stopped, the frontend can still serve its
page, but API requests fail until auth is available again. Nginx re-resolves Docker DNS
when the backend container is recreated.

The multi-stage image builds with Node and serves static assets with non-root Nginx.
API calls use relative URLs. Nginx forwards cookies and the original Origin/CSRF
headers without bypassing backend validation. Fonts and the image are bundled locally.
Google's SDK loads directly from `accounts.google.com`. Nginx allows its script,
styles, frames, and connections; a per-response nonce authorizes its injected styles.
Inline scripts remain blocked, and the opener policy permits the sign-in popup.
Access tokens stay in memory, never localStorage or sessionStorage. Refresh requests
are coalesced within a tab and serialized across tabs with the Web Locks API in
supported browsers. Failed refresh requests are not automatically retried.

Use **localhost** consistently rather than switching to `127.0.0.1`. The backend's
`ALLOWED_ORIGINS` must include `http://localhost:3000`. To change the frontend port,
set `FRONTEND_PORT` in a `frontend/.env` file, add the corresponding origin to
`ALLOWED_ORIGINS` in `backend/.env`, and recreate each service from its own directory.
The frontend does not read the backend's secrets file. Never put secrets in Vite
environment variables: anything bundled into the frontend is public.

## Rebuild And Inspect

From `frontend/`:

```sh
docker compose up --build -d --wait
docker compose logs -f frontend
docker compose ps
```

The frontend build runs lint, 21 API-client and Google-button tests, TypeScript checks, and the Vite
production build. Rebuild after changing source. Run `docker compose down` in
`frontend/` to stop only the frontend; the backend and database keep running. To stop
everything, stop the frontend first, then run `docker compose down` in `backend/`.
Stopping in this order allows the backend to remove its shared network cleanly.
MariaDB data persists in `backend/data/mysql/`; do not delete that directory unless
intentionally resetting the database.

The auth API limits requests to 30 POSTs per IP per minute by default. If repeated
testing returns 429, wait for the next minute. All requests through this local proxy
share its upstream IP unless trusted proxy handling is configured separately.

## Asset

The locally bundled graduation photograph is from
[Unsplash](https://images.unsplash.com/photo-1541339907198-e08756dedf3f).
The fallback Google mark is the
[official Google G asset](https://developers.google.com/static/identity/images/g-logo.png);
the configured sign-in button is rendered by Google Identity Services.
