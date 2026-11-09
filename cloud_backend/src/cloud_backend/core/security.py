"""
Security utilities for the cloud backend, including password hashing and JWT token handling.
"""

import base64
import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from argon2 import Type, low_level
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from .config import get_config

# Argon2id Settings
_MEMORY_COST_KIB: int = 19456
_PARALLELISM: int = 1
_SALT_LEN_BYTE: int = 16
_HASH_LEN_BYTE: int = 32
_ITERATIONS: int = 2

_KEY_STR: str = get_config().JWT_SECRET_KEY.get_secret_value()
# Derive a fixed-size AES-256 key so every valid JWT secret length is usable
# for TOTP encryption as well.
_KEY_BYTES: bytes = hashlib.sha256(_KEY_STR.encode("utf-8")).digest()

# JWT Settings
_ALGORITHM: str = "HS256"
_EXPIRATION_MINUTES: int = 10


def hash_password(password: str) -> tuple[bytes, bytes]:
    """
    Hashes a password using Argon2id with a cryptographically secure 16-byte salt.

    Returns:
        tuple[bytes, bytes]: (password_hash [32 bytes], password_salt [16 bytes])
    """
    salt: bytes = os.urandom(_SALT_LEN_BYTE)
    raw_hash: bytes = low_level.hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=_ITERATIONS,
        memory_cost=_MEMORY_COST_KIB,
        parallelism=_PARALLELISM,
        hash_len=_HASH_LEN_BYTE,
        type=Type.ID,
    )
    return raw_hash, salt


def verify_password(password: str, salt: bytes, expected_hash: bytes) -> bool:
    """
    Verifies a plain-text password against the stored raw salt and hash digest.
    Uses constant-time byte comparison to prevent timing side-channel attacks.
    """
    try:
        calculated_hash: bytes = low_level.hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=salt,
            time_cost=_ITERATIONS,
            memory_cost=_MEMORY_COST_KIB,
            parallelism=_PARALLELISM,
            hash_len=_HASH_LEN_BYTE,
            type=Type.ID,
        )
        return secrets.compare_digest(calculated_hash, expected_hash)
    except Exception:  # noqa
        return False


@lru_cache(maxsize=1)
def _get_AES_key() -> AESGCM:
    """
    Returns a cached instance of AESGCM initialized with the binary secret key.
    """
    return AESGCM(_KEY_BYTES)


def encrypt_totp_secret(secret_text: str) -> str:
    """
    Encrypts the given TOTP secret text using AESGCM and returns the base64-encoded ciphertext.
    """
    aesgcm: AESGCM = _get_AES_key()
    nonce: bytes = os.urandom(12)
    data_bytes: bytes = secret_text.encode("utf-8")
    cipher_text: bytes = aesgcm.encrypt(nonce, data_bytes, associated_data=None)
    combined_payload: bytes = nonce + cipher_text
    encrypted_string: str = base64.b64encode(combined_payload).decode("utf-8")
    return encrypted_string


def decrypt_totp_secret(encrypted_string: str) -> str:
    """
    Decrypts the given base64-encoded TOTP secret using AESGCM and returns the decrypted text.
    """
    combined_payload: bytes = base64.b64decode(encrypted_string.encode("utf-8"))
    nonce: bytes = combined_payload[:12]
    cipher_text: bytes = combined_payload[12:]
    aesgcm: AESGCM = _get_AES_key()
    decrypted_bytes: bytes = aesgcm.decrypt(nonce, cipher_text, associated_data=None)
    decrypted_string: str = decrypted_bytes.decode("utf-8")
    return decrypted_string


def create_access_token(data: dict) -> str:
    """Creates a JWT token using the given data."""
    payload = data.copy()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=_EXPIRATION_MINUTES)
    payload.update(
        {
            "exp": expire,
            "iat": now,
        }
    )
    encoded_jwt = jwt.encode(payload, _KEY_STR, algorithm=_ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> dict | None:
    """
    Verifies the given JWT token and returns the decoded payload if valid, otherwise returns None.
    """
    try:
        decoded_token = jwt.decode(token, _KEY_STR, algorithms=[_ALGORITHM])
        return decoded_token
    except ExpiredSignatureError:
        return None
    except InvalidTokenError:
        return None
