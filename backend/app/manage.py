import argparse
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import create_database_engine, utcnow
from app.core.security import new_secret
from app.etl import sync_crawler
from app.models import AuthRateLimit, GoogleChallenge, RefreshSession
from app.repositories.auth import AuthRepository
from app.seed import seed_database


def write_private_file(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(content)


def init_dev(root: Path, db_port: int, api_port: int) -> None:
    if not (1 <= db_port <= 65535 and 1 <= api_port <= 65535):
        raise SystemExit("Ports must be between 1 and 65535")
    env_path = root / ".env"
    secrets_directory = root / ".secrets"
    private_path = secrets_directory / "jwt-private.pem"
    public_path = secrets_directory / "jwt-public.pem"
    if any(path.exists() for path in (env_path, private_path, public_path)):
        raise SystemExit("Existing .env or signing keys were not modified")
    secrets_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    write_private_file(
        private_path,
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    with public_path.open("xb") as output:
        output.write(
            private_key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
    password = new_secret()
    values = {
        "ENVIRONMENT": "development",
        "DB_NAME": "Professorsdb",
        "DB_USER": "local",
        "DB_PASSWORD": password,
        "DB_ROOT_PASSWORD": new_secret(),
        "DB_PORT": str(db_port),
        "DATABASE_URL": (
            f"mariadb+pymysql://local:{password}@localhost:{db_port}/Professorsdb?charset=utf8mb4"
        ),
        "AUTH_PORT": str(api_port),
        "LOCAL_UID": str(os.getuid()),
        "LOCAL_GID": str(os.getgid()),
        "JWT_PRIVATE_KEY_FILE": ".secrets/jwt-private.pem",
        "JWT_PUBLIC_KEY_FILE": ".secrets/jwt-public.pem",
        "JWT_ISSUER": "professor-auth",
        "JWT_AUDIENCE": "professor-api",
        "ACCESS_TOKEN_MINUTES": "15",
        "REFRESH_TOKEN_DAYS": "30",
        "GOOGLE_CLIENT_ID": "",
        "COOKIE_SECURE": "false",
        "COOKIE_SAMESITE": "lax",
        "ALLOWED_ORIGINS": json.dumps(["http://localhost:3000", f"http://localhost:{api_port}"]),
        "AUTH_REQUESTS_PER_MINUTE": "30",
        "CRAWLER_DATABASE_URL": "",
        "CRAWLER_DEFAULT_COUNTRY": "US",
    }
    write_private_file(
        env_path, "".join(f"{key}={value}\n" for key, value in values.items()).encode()
    )
    print("Created local .env and signing keys. No credentials were printed.")


def init_docker(root: Path, db_port: int, api_port: int) -> None:
    configuration = (
        root / ".env",
        root / ".secrets/jwt-private.pem",
        root / ".secrets/jwt-public.pem",
    )
    if all(path.is_file() for path in configuration):
        print("Existing .env and signing keys retained. Ready for docker compose up.")
        return
    init_dev(root, db_port, api_port)


def promote_admin(session: Session, email: str) -> None:
    email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    repository = AuthRepository(session)
    user = repository.user_by_email(email)
    if user is None:
        raise SystemExit("Register this account first; no user was modified")
    user = repository.lock_user(user.id)
    if user is None:
        raise SystemExit("Account no longer exists; no user was modified")
    user.role = "ADMIN"
    repository.revoke_all(user.id)
    session.commit()
    print("Administrator role granted. Sign in again to obtain updated access-token claims.")


def cleanup(session: Session) -> None:
    now = utcnow()
    for model in (RefreshSession, GoogleChallenge, AuthRateLimit):
        session.execute(delete(model).where(model.expires_at <= now))
    session.commit()
    print("Expired auth records removed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auth service maintenance")
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("init-dev", help="Generate local configuration and signing keys")
    setup.add_argument("--db-port", type=int, default=3306)
    setup.add_argument("--api-port", type=int, default=8000)
    docker_setup = commands.add_parser("init-docker", help="Create or retain Docker configuration")
    docker_setup.add_argument("--db-port", type=int, default=3306)
    docker_setup.add_argument("--api-port", type=int, default=8000)
    admin = commands.add_parser("promote-admin", help="Promote an existing account using DB access")
    admin.add_argument("email")
    commands.add_parser("seed", help="Insert or update the normalized demo catalog data")
    sync = commands.add_parser(
        "sync-crawler", help="ETL raw crawler tables into the normalized catalog"
    )
    sync.add_argument(
        "--source-url",
        default=os.environ.get("CRAWLER_DATABASE_URL") or None,
        help="SQLAlchemy URL for the crawler database (defaults to CRAWLER_DATABASE_URL)",
    )
    sync.add_argument(
        "--default-country",
        default=os.environ.get("CRAWLER_DEFAULT_COUNTRY", "US"),
        help="Country code applied to universities that have none in the raw data",
    )
    sync.add_argument("--dry-run", action="store_true", help="Roll back instead of committing")
    commands.add_parser("cleanup", help="Remove expired sessions, Google nonces and rate buckets")
    arguments = parser.parse_args()
    if arguments.command == "init-dev":
        init_dev(Path.cwd(), arguments.db_port, arguments.api_port)
        return
    if arguments.command == "init-docker":
        init_docker(Path.cwd(), arguments.db_port, arguments.api_port)
        return
    settings = Settings()
    engine = create_database_engine(settings.database_url)
    source_engine = None
    if arguments.command == "sync-crawler":
        source_url = arguments.source_url or settings.crawler_database_url
        if not source_url:
            raise SystemExit("Provide --source-url or set CRAWLER_DATABASE_URL")
        source_engine = create_database_engine(source_url)
    try:
        with Session(engine, expire_on_commit=False) as session:
            if arguments.command == "promote-admin":
                promote_admin(session, arguments.email)
            elif arguments.command == "seed":
                counts = seed_database(session)
                print(
                    "Seeded demo data: "
                    + ", ".join(f"{name}={count}" for name, count in counts.items())
                )
            elif arguments.command == "sync-crawler":
                counts = sync_crawler(
                    session,
                    source_engine,
                    arguments.default_country,
                    dry_run=arguments.dry_run,
                )
                label = "Crawler sync (dry run)" if arguments.dry_run else "Crawler sync"
                print(label + ": " + ", ".join(f"{name}={count}" for name, count in counts.items()))
            else:
                cleanup(session)
    finally:
        engine.dispose()
        if source_engine is not None:
            source_engine.dispose()


if __name__ == "__main__":
    main()
