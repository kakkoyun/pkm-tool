"""Encrypted token storage backed by SQLite."""

from __future__ import annotations

import base64
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import keyring
import structlog
from cryptography.fernet import Fernet, InvalidToken

logger = structlog.get_logger(__name__)

# Keyring service name for storing the encryption key
_KEYRING_SERVICE = "pkm-tool"
_KEYRING_USERNAME = "token-store-encryption-key"

DEFAULT_DB_PATH = Path.home() / ".pkm-tool" / "tokens.db"


@dataclass(slots=True)
class StoredToken:
    """Represents a token stored in the token store."""

    source: str
    token: str
    refresh_token: str | None
    expires_at: datetime | None
    token_type: str


class TokenStore:
    """Encrypted token store that keeps credentials in SQLite."""

    def __init__(
        self, db_path: Path | None = None, *, encryption_key: bytes | None = None
    ) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path = self.db_path.expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Allow dependency injection of encryption key for testing
        key = encryption_key if encryption_key is not None else _derive_key()
        self._fernet = Fernet(key)
        self._initialize_database()

    def save_token(
        self,
        source: str,
        token: str,
        *,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
        token_type: str = "bearer",
    ) -> None:
        """Save or update a token for a specific source."""
        logger.debug("token_store_save", source=source)
        encrypted_token = self._encrypt(token)
        encrypted_refresh = self._encrypt(refresh_token) if refresh_token else None
        expires_ts = _serialize_datetime(expires_at)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tokens (source, token, refresh_token, expires_at, token_type)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source) DO UPDATE SET
                    token = excluded.token,
                    refresh_token = excluded.refresh_token,
                    expires_at = excluded.expires_at,
                    token_type = excluded.token_type
                """,
                (source, encrypted_token, encrypted_refresh, expires_ts, token_type),
            )

    def get_token(self, source: str) -> StoredToken | None:
        """Retrieve a stored token for a given source."""
        logger.debug("token_store_get", source=source)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            query = (
                "SELECT source, token, refresh_token, expires_at, token_type "
                "FROM tokens WHERE source = ?"
            )
            row = conn.execute(query, (source,)).fetchone()

        if row is None:
            return None

        try:
            token = self._decrypt(row["token"])
            refresh_token = self._decrypt(row["refresh_token"]) if row["refresh_token"] else None
        except InvalidToken as exc:
            logger.error("token_store_decrypt_failed", source=source, error=str(exc))
            return None

        return StoredToken(
            source=row["source"],
            token=token,
            refresh_token=refresh_token,
            expires_at=_deserialize_datetime(row["expires_at"]),
            token_type=row["token_type"],
        )

    def delete_token(self, source: str) -> None:
        """Delete a token from the store."""
        logger.debug("token_store_delete", source=source)
        with self._connect() as conn:
            conn.execute("DELETE FROM tokens WHERE source = ?", (source,))

    def list_tokens(self) -> list[StoredToken]:
        """List all tokens stored (including decrypted tokens)."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            query = (
                "SELECT source, token, refresh_token, expires_at, token_type "
                "FROM tokens ORDER BY source"
            )
            rows = conn.execute(query).fetchall()

        tokens: list[StoredToken] = []
        for row in rows:
            try:
                token = self._decrypt(row["token"])
                refresh_token = (
                    self._decrypt(row["refresh_token"]) if row["refresh_token"] else None
                )
            except InvalidToken as exc:
                logger.error("token_store_decrypt_failed", source=row["source"], error=str(exc))
                continue

            tokens.append(
                StoredToken(
                    source=row["source"],
                    token=token,
                    refresh_token=refresh_token,
                    expires_at=_deserialize_datetime(row["expires_at"]),
                    token_type=row["token_type"],
                )
            )
        return tokens

    def _connect(self) -> sqlite3.Connection:
        """Create a new SQLite connection."""
        return sqlite3.connect(self.db_path)

    def _initialize_database(self) -> None:
        """Ensure the tokens table exists."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tokens (
                    source TEXT PRIMARY KEY,
                    token TEXT NOT NULL,
                    refresh_token TEXT,
                    expires_at INTEGER,
                    token_type TEXT NOT NULL
                )
                """
            )

    def _encrypt(self, value: str) -> str:
        """Encrypt a value using Fernet."""
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def _decrypt(self, value: str) -> str:
        """Decrypt a previously encrypted value."""
        decrypted = self._fernet.decrypt(value.encode("utf-8"))
        return decrypted.decode("utf-8")


def _derive_key() -> bytes:
    """
    Retrieve or generate a secure encryption key using the system keyring.

    On first use, generates a cryptographically secure random key and stores it
    in the system keyring. On subsequent calls, retrieves the stored key.

    This approach provides better security than deriving keys from machine identifiers:
    - Uses cryptographically secure random generation (secrets module)
    - Leverages OS-level keyring security (Keychain on macOS, Credential Manager on Windows, etc.)
    - No predictable patterns or insufficient entropy

    Returns:
        bytes: A 32-byte Fernet-compatible encryption key

    Raises:
        RuntimeError: If keyring operations fail
    """
    try:
        # Try to retrieve existing key from keyring
        stored_key = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)

        if stored_key is not None:
            # Key exists, decode and return it
            try:
                logger.debug("encryption_key_retrieved_from_keyring")
                decoded_key = base64.urlsafe_b64decode(stored_key.encode("utf-8"))
                # Validate key length (Fernet requires exactly 32 bytes)
                if len(decoded_key) != 32:
                    raise ValueError(f"Invalid key length: {len(decoded_key)} bytes (expected 32)")
                return decoded_key
            except Exception as decode_exc:
                # Key is corrupted, log and regenerate
                logger.warning(
                    "stored_key_corrupted",
                    error=str(decode_exc),
                    action="regenerating_key",
                )
                # Fall through to generate new key

        # No key exists (or corrupted key), generate a new secure random key
        logger.info("generating_new_encryption_key")
        random_key = secrets.token_bytes(32)  # 256 bits of entropy
        encoded_key = base64.urlsafe_b64encode(random_key).decode("utf-8")

        # Store the key in the system keyring
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, encoded_key)
        logger.info("encryption_key_stored_in_keyring")

        return random_key

    except Exception as exc:
        logger.error("keyring_operation_failed", error=str(exc))
        raise RuntimeError(
            f"Failed to access system keyring for encryption key management: {exc}"
        ) from exc


def _serialize_datetime(value: datetime | None) -> int | None:
    """Convert datetime to POSIX timestamp."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return int(value.timestamp())


def _deserialize_datetime(value: int | None) -> datetime | None:
    """Convert POSIX timestamp to datetime."""
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=UTC)
