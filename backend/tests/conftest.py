from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import Settings
from app.core.database import Base, create_database_engine
from app.core.security import AccessTokens
from app.main import create_app


def pytest_addoption(parser):
    parser.addoption("--mariadb", action="store_true", help="Test in isolated MariaDB databases")


@pytest.fixture(scope="session")
def signing_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
        private_key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode(),
    )


@pytest.fixture
def tokens(signing_keys):
    return AccessTokens(*signing_keys, issuer="professor-auth", audience="professor-api")


@pytest.fixture
def database(request):
    if request.config.getoption("--mariadb"):
        namespace = f"auth_test_{uuid4().hex}"
        engine = create_database_engine(Settings().database_url).execution_options(
            schema_translate_map={None: namespace}
        )
        with engine.begin() as connection:
            connection.execute(CreateSchema(namespace))
        try:
            Base.metadata.create_all(engine)
            yield engine
        finally:
            with engine.begin() as connection:
                connection.execute(DropSchema(namespace))
            engine.dispose()
        return
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(database):
    with sessionmaker(bind=database, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def app(database, tokens):
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite+pysqlite://",
        cookie_secure=False,
        google_client_id="test-client",
    )
    return create_app(settings, database, tokens)


@pytest.fixture
def client(app):
    with TestClient(app, headers={"X-CSRF-Protection": "1"}) as client:
        yield client
