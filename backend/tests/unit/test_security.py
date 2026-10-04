from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from search_prof.backend.app.core.security import AccessTokens, hash_password, hash_secret, new_secret, verify_password


@pytest.fixture(scope="module")
def tokens():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return AccessTokens(
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
        issuer="professor-auth",
        audience="professor-api",
    )


def test_password_hash_is_salted_and_verifiable():
    password = "a long test password"
    encoded = hash_password(password)
    assert encoded != password
    assert encoded != hash_password(password)
    assert verify_password(password, encoded)
    assert not verify_password("incorrect password", encoded)


def test_access_token_round_trip(tokens):
    token = tokens.issue("user-id", "USER")
    claims = tokens.verify(token)
    assert claims["sub"] == "user-id"
    assert claims["role"] == "USER"
    assert claims["token_type"] == "access"
    assert tokens.issue("user-id", "USER") != token


@pytest.mark.parametrize(
    "changed_claim",
    [
        {"aud": "another-service"},
        {"iss": "another-issuer"},
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        {"token_type": "refresh"},
    ],
)
def test_invalid_claims_are_rejected(tokens, changed_claim):
    claims = tokens.verify(tokens.issue("user-id", "USER"))
    claims.update(changed_claim)
    token = jwt.encode(claims, tokens.private_key, algorithm="RS256")
    with pytest.raises(jwt.InvalidTokenError):
        tokens.verify(token)


def test_jwks_contains_only_public_key(tokens):
    key = tokens.jwks()["keys"][0]
    assert key["kid"] == tokens.key_id
    assert key["kty"] == "RSA"
    assert "d" not in key
    public_key = jwt.PyJWK.from_dict(key).key
    claims = jwt.decode(
        tokens.issue("user-id", "USER"),
        public_key,
        algorithms=["RS256"],
        issuer=tokens.issuer,
        audience=tokens.audience,
    )
    assert claims["sub"] == "user-id"


def test_refresh_secrets_are_random_and_only_hashes_are_stored():
    secret = new_secret()
    assert secret != new_secret()
    assert len(secret) >= 64
    assert len(hash_secret(secret)) == 64
    assert hash_secret(secret) != secret


def test_mismatched_key_pair_is_rejected(tokens, signing_keys):
    with pytest.raises(ValueError, match="matching RSA"):
        AccessTokens(tokens.private_key, signing_keys[1], "issuer", "audience")
