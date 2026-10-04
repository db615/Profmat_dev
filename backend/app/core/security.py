import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from jwt.algorithms import RSAAlgorithm
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def new_secret() -> str:
    return secrets.token_urlsafe(48)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class AccessTokens:
    def __init__(
        self,
        private_key: str,
        public_key: str,
        issuer: str,
        audience: str,
        lifetime_minutes: int = 15,
    ) -> None:
        signing_key = load_pem_private_key(private_key.encode(), password=None)
        verification_key = load_pem_public_key(public_key.encode())
        if (
            not isinstance(signing_key, RSAPrivateKey)
            or not isinstance(verification_key, RSAPublicKey)
            or signing_key.key_size < 2048
            or signing_key.public_key().public_numbers() != verification_key.public_numbers()
        ):
            raise ValueError("JWT keys must be a matching RSA key pair of at least 2048 bits")
        self.private_key = private_key
        self.public_key = public_key
        self.issuer = issuer
        self.audience = audience
        self.lifetime_minutes = lifetime_minutes
        self.key_id = hash_secret(public_key)[:16]

    def issue(self, user_id: str, role: str) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": user_id,
                "role": role,
                "iss": self.issuer,
                "aud": self.audience,
                "iat": now,
                "nbf": now,
                "exp": now + timedelta(minutes=self.lifetime_minutes),
                "jti": str(uuid4()),
                "token_type": "access",
            },
            self.private_key,
            algorithm="RS256",
            headers={"kid": self.key_id},
        )

    def verify(self, token: str) -> dict:
        claims = jwt.decode(
            token,
            self.public_key,
            algorithms=["RS256"],
            issuer=self.issuer,
            audience=self.audience,
            options={"require": ["sub", "role", "iss", "aud", "iat", "nbf", "exp", "jti"]},
        )
        if claims.get("token_type") != "access":
            raise jwt.InvalidTokenError("Not an access token")
        return claims

    def jwks(self) -> dict:
        key = RSAAlgorithm.to_jwk(load_pem_public_key(self.public_key.encode()), as_dict=True)
        return {"keys": [{**key, "kid": self.key_id, "use": "sig", "alg": "RS256"}]}
