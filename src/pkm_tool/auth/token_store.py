"""Encrypted token storage backed by SQLite."""

from __future__ import annotations

import base64
import hashlib
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import structlog
from cryptography.fernet import Fernet, InvalidToken

logger = structlog.get_logger(__name__)

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

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path = self.db_path.expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(_derive_key())
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

        conn = self._connect()
        try:
            with conn:
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
        finally:
            conn.close()

    def get_token(self, source: str) -> StoredToken | None:
        """Retrieve a stored token for a given source."""
        logger.debug("token_store_get", source=source)
        conn = self._connect()
        try:
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
                refresh_token = (
                    self._decrypt(row["refresh_token"]) if row["refresh_token"] else None
                )
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
        finally:
            conn.close()

    def delete_token(self, source: str) -> None:
        """Delete a token from the store."""
        logger.debug("token_store_delete", source=source)
        conn = self._connect()
        try:
            with conn:
                conn.execute("DELETE FROM tokens WHERE source = ?", (source,))
        finally:
            conn.close()

    def list_tokens(self) -> list[StoredToken]:
        """List all tokens stored (including decrypted tokens)."""
        conn = self._connect()
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT source, token, refresh_token, expires_at, token_type "
                "FROM tokens ORDER BY source"
            ).fetchall()

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
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        """Create a new SQLite connection."""
        return sqlite3.connect(self.db_path)

    def _initialize_database(self) -> None:
        """Ensure the tokens table exists."""
        conn = self._connect()
        try:
            with conn:
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
        finally:
            conn.close()

    def _encrypt(self, value: str) -> str:
        """Encrypt a value using Fernet."""
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def _decrypt(self, value: str) -> str:
        """Decrypt a previously encrypted value."""
        decrypted = self._fernet.decrypt(value.encode("utf-8"))
        return decrypted.decode("utf-8")


def _derive_key() -> bytes:
    """Derive a stable encryption key for the current machine."""
    machine_id = uuid.getnode()
    home_path = str(Path.home())
    digest = hashlib.sha256(f"{machine_id}:{home_path}".encode()).digest()
    return base64.urlsafe_b64encode(digest)


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
