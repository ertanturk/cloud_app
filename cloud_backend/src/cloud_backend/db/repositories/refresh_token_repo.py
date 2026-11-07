"""Refresh token repository for managing refresh token records in the database."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cloud_backend.db.models.core import RefreshTokens


class RefreshTokenRepository:
    """Manages refresh token records in the database."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_token(
        self, session_id: int, token_hash: bytes, expires_at: datetime
    ) -> RefreshTokens:
        try:
            token = RefreshTokens(
                session_id=session_id,
                token_hash=token_hash,
                created_at=datetime.now(UTC),
                expires_at=expires_at,
            )
            self.db.add(token)
            self.db.commit()
            self.db.refresh(token)
            return token
        except Exception:
            self.db.rollback()
            raise

    def get_by_hash(
        self, token_hash: bytes, lock: bool = False
    ) -> RefreshTokens | None:
        """Finds a refresh token by its SHA-256 hash. Optionally locks the row for update."""
        stmt = select(RefreshTokens).where(RefreshTokens.token_hash == token_hash)
        if lock:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def rotate_token(
        self, old_token: RefreshTokens, new_token_hash: bytes, new_expires_at: datetime
    ) -> RefreshTokens:
        """
        Rotates an existing refresh token in a single atomic transaction.
        Marks old token as used and links it to the newly created token.
        """
        try:
            now = datetime.now(UTC)
            old_token.used_at = now

            new_token = RefreshTokens(
                session_id=old_token.session_id,
                token_hash=new_token_hash,
                created_at=now,
                expires_at=new_expires_at,
            )
            self.db.add(new_token)
            self.db.flush()

            old_token.replaced_by_token_id = new_token.refresh_token_id
            self.db.commit()
            self.db.refresh(new_token)
            return new_token
        except Exception:
            self.db.rollback()
            raise

    def revoke_all_for_session(self, session_id: int) -> None:
        """Revokes all active refresh tokens associated with a given session."""
        try:
            stmt = select(RefreshTokens).where(
                RefreshTokens.session_id == session_id,
                RefreshTokens.revoked_at.is_(None),
            )
            active_tokens = list(self.db.scalars(stmt).all())
            now = datetime.now(UTC)

            for token in active_tokens:
                token.revoked_at = now

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
