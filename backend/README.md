# Professor Search Auth Service

A fresh FastAPI authentication/authorization microservice, independent of the legacy
`professor_search/` scraper. MariaDB owns registered users, Google identities,
hashed refresh tokens, one-time Google challenges, and shared rate-limit buckets.

## Run The Backend

Prerequisite: Docker with Compose v2. On macOS, start Docker Desktop first.
**No local Python, pip, virtual environment, or MariaDB installation is required.**
Setup, the API, migrations, tests, and maintenance all run in containers. The React
frontend runs in its own Compose project in `frontend/`.

From the repository root, enter the backend directory. All subsequent commands run here:

```sh
cd backend
```

If `.env` and the signing keys in `.secrets/` already exist, go directly to
**Start The Stack**. Keep ports 8000 (API) and 3306 (MariaDB) available.

### One-Time Setup

For a fresh checkout, run this from `backend/` on macOS or Linux:

```sh
LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)" \
  docker compose -f docker-compose.setup.yml run --build --rm setup
```

This builds the runtime image and generates separate application/root database passwords and RSA signing
keys **inside a temporary setup container**. It writes an ignored mode-600 `.env` and
`.secrets/` to the backend directory so they survive container replacement. The UID/GID
settings keep the generated files owned by your host user and readable by the non-root
API container. No secrets are included in the image or printed.

The Docker setup command is safe to rerun: it retains a complete existing configuration
without rotating passwords or keys. It refuses a partial setup; restore missing files
from your backup rather than replacing credentials for an existing database. Do not
copy `.env.example` over generated configuration or commit `.env` or `.secrets/`.

To select different ports on the first setup, append a command override:

```sh
LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)" \
  docker compose -f docker-compose.setup.yml run --build --rm setup \
  python -m app.manage init-docker --db-port 3307 --api-port 8001
```

The `python` command above executes in the container. These port arguments do not
modify existing configuration. To change ports later, update `.env`, including
`ALLOWED_ORIGINS` for a different API origin, then recreate the stack.

### Start The Stack

This starts MariaDB, applies migrations, and starts the API:

```sh
docker compose up --build -d --wait
```

Use the same command for subsequent starts or after changing application code.
The startup order is MariaDB healthy -> migrations complete -> API healthy.
The one-shot `migrate` container exiting successfully is expected. The `tests` service
is opt-in and does not run during normal startup.

- API documentation: http://localhost:8000/docs
- Readiness endpoint: http://localhost:8000/health/ready
- MariaDB: `localhost:3306`, database `Professorsdb`, user `local`; credentials are in `.env`.

Check that the service is ready:

```sh
docker compose ps
curl --fail --silent --show-error http://localhost:8000/health/ready
```

The readiness response should be `{"status":"ready"}`. Adjust the URLs if you chose
a different API port. All published ports bind only to localhost.

### MariaDB Configuration

The `database` service uses `mariadb:latest`, container name `professor_database`,
and the bind mount `./data/mysql:/var/lib/mysql`. Database settings in `.env` are
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_ROOT_PASSWORD`, and `DB_PORT`.
Compose defaults to database `Professorsdb`, application user/password `local`, and
port `3306`; the root password falls back to `DB_PASSWORD` or `root` when unset.
Run setup to generate strong random passwords instead of using these development defaults.
Use URL-safe passwords: Compose inserts them into SQLAlchemy connection URLs.

Containers connect with `mariadb+pymysql` to `database:3306`; the host `DATABASE_URL`
uses `localhost` and `DB_PORT`. The API uses read-committed transactions for token
replay detection and stores UTC timestamps with microsecond precision. MariaDB already
supports native-password authentication, so the MySQL-only
`--default-authentication-plugin` option is not used. The server uses `utf8mb4` with
case-sensitive collation for auth identifiers. `lower_case_table_names=1` is set from
initialization so mixed-case database names work on macOS bind mounts; MariaDB stores
database/table names in lowercase internally. Do not change that setting on an existing
data directory. Pin a tested image version for production.

Switching from PostgreSQL starts a separate MariaDB database; it does not copy users
or sessions. Retain the old PostgreSQL volume as a backup, never mount it into MariaDB,
and update database settings in `.env` without replacing signing keys. The new data
directory is `backend/data/mysql`, not the legacy scraper's `professor_search/data/mysql`.
If another project owns the `professor_database` container name, resolve that name
conflict before starting this stack; do not delete its database files.

### Start The Frontend Separately

After the backend is running, start the frontend from its own directory:

```sh
cd ../frontend
docker compose up --build -d --wait
```

Open http://localhost:3000 for registration and login. The two Compose projects share
`professor-auth-network`, created by the backend. Only the auth API is exposed on that
network; MariaDB remains on the backend's `database-network`. Frontend commands do
not manage backend containers. See the [frontend guide](../frontend/README.md) for
browser testing and frontend port configuration. Return to `backend/` before running
the backend commands below.

### Logs, Restart, And Stop

Run these commands individually as needed:

```sh
# Follow API logs; Ctrl+C stops following, not the service.
docker compose logs -f auth

# Inspect migration failures.
docker compose logs migrate

# Restart the containerized API without changing its configuration.
docker compose restart auth

# Apply .env changes, including GOOGLE_CLIENT_ID.
docker compose up -d --force-recreate auth

# Stop the backend services while retaining database contents.
docker compose down
```

Stop the frontend project first when shutting down everything, so the backend can
remove the shared Docker network. Stopping just the frontend leaves the backend running.

Database contents persist in `backend/data/mysql`; `.env` and `.secrets/` also
persist on the host. All three are excluded from the image and Git. Even
`docker compose down -v` does not delete bind-mounted database files. Do not remove
that directory unless intentionally resetting the database. Changing database passwords
in `.env` after initialization does not update MariaDB accounts; change their passwords
in MariaDB too before recreating the API.

For a database shell without a host MariaDB client, substitute your configured user
and database if different, then enter its password at the prompt:

```sh
docker compose exec database mariadb --user=local --password Professorsdb
```

### Try The API

Open http://localhost:8000/docs. Every auth POST requires `X-CSRF-Protection: 1`;
enter `1` in that header field when using Swagger. Register with an email and a
12-128 character password. Registration logs the user in and sets the refresh cookie.
Use Swagger's **Authorize** button with the returned access token, then call
`GET /api/v1/auth/me`. Call `POST /api/v1/auth/refresh` to obtain another access token.

Keep using `localhost`, not a mix of `localhost` and `127.0.0.1`, for browser cookies.
Email/password login works without Google configuration. To enable Google sign-in,
follow **Google Login** below and recreate the API container after setting its client ID.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | Email/password signup; optional `full_name` |
| POST | `/api/v1/auth/login` | Email/password login |
| POST | `/api/v1/auth/refresh` | Rotate the refresh cookie; issue a new access token |
| POST | `/api/v1/auth/logout` | Revoke this refresh family and clear cookies |
| POST | `/api/v1/auth/logout-all` | Revoke every refresh session; bearer token required |
| GET | `/api/v1/auth/me` | Current active user; bearer token required |
| POST | `/api/v1/auth/google/nonce` | Create a five-minute browser-bound Google nonce |
| POST | `/api/v1/auth/google` | Exchange `{ "id_token": "..." }` for an app session |
| POST | `/api/v1/auth/google/link` | Link matching Google identity; bearer token required |
| GET | `/api/v1/admin/users` | Paginated user list; `ADMIN` only |
| GET | `/.well-known/jwks.json` | Public RSA signing key for other services |
| GET | `/health/live` | Process health |
| GET | `/health/ready` | Database connectivity |

Registration accepts 12-128 character passwords and never accepts a role from the
client. Passwords use Argon2; email addresses are normalized to lowercase. Responses
never expose password hashes, Google subjects, or refresh-token values in JSON.

Create an administrator by registering normally, then running a DB-authorized command:

```sh
docker compose exec auth python -m app.manage promote-admin admin@example.com
```

There is no public endpoint for self-promotion. `USER`/`ADMIN` follow the root RBAC notes.

## Browser Integration

Use `credentials: "include"` and `X-CSRF-Protection: 1` for all auth POSTs. Keep access
tokens in memory; on reload, obtain one through `/refresh`. Send the access token as
`Authorization: Bearer <token>` on protected API calls. Do not put tokens in URLs or
local storage. CORS uses exact `ALLOWED_ORIGINS`, and requests from unapproved origins
are rejected even if they include the custom header.

```js
const response = await fetch("http://localhost:8000/api/v1/auth/login", {
  method: "POST",
  credentials: "include",
  headers: { "Content-Type": "application/json", "X-CSRF-Protection": "1" },
  body: JSON.stringify({ email, password }),
});
if (!response.ok) throw new Error("Login failed");
const session = await response.json();
```

Refresh tokens are opaque random secrets in an HttpOnly cookie, with only SHA-256
hashes stored in SQL. Access tokens expire after 15 minutes. Refresh sessions have an
absolute 30-day lifetime, including rotations. A refresh token is single-use: replay
revokes its entire family, including its replacement. **Serialize refresh requests
across tabs**; do not automatically retry a refresh whose response was lost. In that
case, sign in again. Logout revokes refresh tokens; already-issued access tokens remain
valid until expiry. This service checks active status and roles against SQL on each
protected request; other services using JWT-only verification see changes after expiry.

## Google Login

Create a **Web application** OAuth client in Google Cloud / Google Auth Platform,
configure its consent screen/test users and authorized JavaScript origins (for local
testing, `http://localhost` and `http://localhost:3000`), and set `GOOGLE_CLIENT_ID` in `.env`. Run
`docker compose up -d --force-recreate auth` after changing it; a simple restart does
not reload container environment variables. No client secret or redirect URI is needed for
this Google Identity Services ID-token flow.

The React frontend already implements this flow. Reload http://localhost:3000 after
configuring the backend, then use **Sign in with Google**. No frontend client-ID
variable or rebuild is required. Until configured, the button remains visible but
disabled with an unavailable status. Existing password-account users can sign in and
select **Link Google** in their account view; Google emails must match.
See the [frontend guide](../frontend/README.md#enable-google-sign-in) for setup details.

1. POST `/api/v1/auth/google/nonce` with credentials and the CSRF header.
2. Pass the returned `client_id` and `nonce` to `google.accounts.id.initialize`.
3. Render Google's sign-in button using Google Identity Services.
4. In its callback, POST `{ "id_token": result.credential }` to `/api/v1/auth/google`,
   again including credentials and the CSRF header.
5. Keep the returned app access token in memory; the refresh cookie is set automatically.

Google's library verifies signature, expiry, issuer, and the configured audience.
The service additionally requires a verified email and the one-time, browser-bound
nonce. It identifies Google accounts by stable `sub`, not email alone. A collision
with an existing email/password account returns 409: log in normally, request a new
nonce, and call `/api/v1/auth/google/link` with the bearer token to explicitly link it.
The email addresses must match. Google login returns 503 until configured; a provider
verification outage also returns 503, never a bypass. Real Google sign-in requires
your own client ID; tests use controlled identities and do not contact Google.

## Service Boundaries

```text
Browser -> auth service -> auth MariaDB database
Browser -> future professor/search services -> their own data stores
                       -> auth public JWKS (signature verification only)
```

Only auth owns these tables and the private signing key. Future services should
validate JWTs locally with the public JWKS: allow **RS256 only**, require `iss`, `aud`,
`exp`, `sub`, and `token_type=access`, and enforce roles/resource ownership themselves.
The defaults are issuer `professor-auth` and audience `professor-api`. Cache the public
keys, refresh on an unknown `kid`, and use a trusted configured JWKS URL. Never let a
token supply its own key URL. No gateway, Redis, or empty placeholder services are
needed for this initial deployment.

## Operations And Tests

All commands below run inside containers. The test image adds development dependencies
without putting them in the runtime image:

```sh
docker compose --profile tools run --build --rm tests
docker compose --profile tools run --rm tests ruff check .
docker compose --profile tools run --rm tests ruff format --check .
docker compose exec auth alembic check
docker compose exec auth python -m app.manage cleanup
```

The test service runs `pytest --mariadb -q` against MariaDB using uniquely named
temporary databases, which are dropped afterward without touching application tables.
Only this opt-in test container uses root credentials to create/drop test databases;
the API and migration job use `DB_USER`. This enables refresh, nonce, registration,
and rate-limit concurrency tests. Google verification tests do not need real credentials.
Rebuild the test image after changing code. To run the faster SQLite tests without
starting MariaDB:

```sh
docker compose --profile tools run --build --rm --no-deps tests pytest -q
```

Run cleanup periodically, such as hourly. Consumed refresh rows must remain until
their absolute expiry for replay detection; the cleanup command preserves them.
The SQL rate limiter allows 30 auth POSTs/IP/minute by default and is shared across
replicas. Behind a trusted gateway, configure Uvicorn's trusted forwarded IPs explicitly;
never trust arbitrary public `X-Forwarded-For` headers. Add edge rate limits and request
body size limits for production traffic.

Development sets `COOKIE_SECURE=false` only for local HTTP. Production requires
`ENVIRONMENT=production`, HTTPS origins, `COOKIE_SECURE=true`, strong database
credentials, and privately mounted signing keys (not baked into the image). Prefer
same-site frontend/API domains with `COOKIE_SAMESITE=lax`. For genuinely cross-site
deployment, use `COOKIE_SAMESITE=none` with HTTPS; browser third-party-cookie policies
can still block that configuration. Provision the runtime key permissions for its
non-root UID; Docker setup records your UID/GID for Compose's read-only key mount.

Use a separate least-privilege runtime database role and privileged migration role in
production. Back up the database and stable signing keys. The initial JWKS publishes
one key; rolling key rotation requires retaining old public keys until old access
tokens expire. Email/password registrations remain `email_verified=false`: email
verification and password recovery are separate future workflows, not silently faked.