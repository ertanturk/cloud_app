"""
Repository for User and UserSecrets database operations.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cloud_backend.core.app_logging import ProjectLogger
from cloud_backend.db.models.core import Users, UserSecrets

logger = ProjectLogger.get_logger(__name__)


class UserRepository:
    """Repository for User and UserSecrets database operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_username(self, username: str) -> Users | None:
        """Finds a user by their unique username."""
        stmt = select(Users).where(Users.username == username)
        return self.db.scalar(stmt)

    def get_by_id(self, user_id: int) -> Users | None:
        """Finds a user by their primary key."""
        stmt = select(Users).where(Users.user_id == user_id)
        return self.db.scalar(stmt)

    def get_by_setup_token(self, totp_setup_token_hash: bytes) -> UserSecrets | None:
        """Finds a UserSecrets by their setup token hash."""
        stmt = select(UserSecrets).where(
            UserSecrets.totp_setup_token_hash == totp_setup_token_hash
        )
        return self.db.scalar(stmt)

    def get_user_secrets(self, user_id: int) -> UserSecrets | None:
        """Finds a user's secrets record by user_id."""
        stmt = select(UserSecrets).where(UserSecrets.user_id == user_id)
        return self.db.scalar(stmt)

    def create_user_with_secrets(
        self,
        username: str,
        password_hash: bytes,
        password_hash_version: int,
        password_salt: bytes,
        role: str = "user",
    ) -> Users:
        """Creates a user and their initial secrets record atomically."""
        try:
            new_user = Users(
                username=username,
                password_hash=password_hash,
                password_hash_version=password_hash_version,
                role=role,
            )
            self.db.add(new_user)
            self.db.flush()  # Generates new_user.user_id before committing

            secrets = UserSecrets(
                user_id=new_user.user_id,
                password_salt=password_salt,
                totp_enabled=False,
            )
            self.db.add(secrets)
            self.db.commit()
            self.db.refresh(new_user)
            return new_user
        except Exception:
            logger.exception("Failed to create user and secrets")
            self.db.rollback()
            raise

    def save_pending_totp(
        self,
        user_id: int,
        pending_totp_secret: bytes,
        totp_setup_token_hash: bytes,
        totp_setup_expires_at: datetime,
    ) -> UserSecrets | None:
        """Saves the pending TOTP secret and setup token details for a user."""
        try:
            secrets = self.get_user_secrets(user_id)
            if secrets is None:
                return None

            secrets.pending_totp_secret = pending_totp_secret
            secrets.totp_setup_token_hash = totp_setup_token_hash
            secrets.totp_setup_expires_at = totp_setup_expires_at

            self.db.commit()
            self.db.refresh(secrets)
            return secrets
        except Exception:
            logger.exception("Failed to save pending TOTP setup")
            self.db.rollback()
            raise

    def confirm_totp(self, user_id: int) -> UserSecrets | None:
        """
        Confirms TOTP setup by moving pending secret to encrypted_totp_secret,
        clearing pending setup fields, and enabling TOTP.
        """
        try:
            secrets = self.get_user_secrets(user_id)
            if secrets is None:
                return None

            secrets.encrypted_totp_secret = secrets.pending_totp_secret
            secrets.pending_totp_secret = None
            secrets.totp_setup_token_hash = None
            secrets.totp_setup_expires_at = None
            secrets.totp_enabled = True

            self.db.commit()
            self.db.refresh(secrets)
            return secrets
        except Exception:
            logger.exception("Failed to confirm TOTP setup")
            self.db.rollback()
            raise

    def update_quota(self, user_id: int, new_quota_bytes: int) -> Users | None:
        """Updates storage_quota_bytes for the user using pessimistic row locking."""
        try:
            stmt = select(Users).where(Users.user_id == user_id).with_for_update()
            user = self.db.scalar(stmt)
            if user is None:
                return None

            user.storage_quota_bytes = new_quota_bytes
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception:
            logger.exception("Failed to update user quota for user_id=%s", user_id)
            self.db.rollback()
            raise

    def list_users(self) -> list[Users]:
        stmt = select(Users)
        return list(self.db.execute(stmt).scalars().all())
