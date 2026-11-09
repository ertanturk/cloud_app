from datetime import datetime

from sqlalchemy import (
    BIGINT,
    BINARY,
    INT,
    NVARCHAR,
    VARBINARY,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "Users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="chk_users_role"),
        CheckConstraint(
            "storage_quota_bytes > 0", name="chk_users_storage_quota_bytes"
        ),
        {"schema": "dbo"},
    )

    user_id: Mapped[int] = mapped_column(INT, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(NVARCHAR(100), nullable=False, unique=True)
    password_hash: Mapped[bytes] = mapped_column(BINARY(32), nullable=False)
    password_hash_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), server_default=text("'user'"), nullable=False
    )
    storage_quota_bytes: Mapped[int] = mapped_column(
        BIGINT, nullable=False, server_default=text("10000000000")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class UserSecrets(Base):
    __tablename__ = "UserSecrets"
    __table_args__ = (
        CheckConstraint("totp_enabled IN (0, 1)", name="chk_user_secrets_totp_enabled"),
        {"schema": "dbo"},
    )

    user_id: Mapped[int] = mapped_column(
        INT, ForeignKey("dbo.Users.user_id", ondelete="CASCADE"), primary_key=True
    )
    password_salt: Mapped[bytes] = mapped_column(BINARY(16), nullable=False)
    encrypted_totp_secret: Mapped[bytes | None] = mapped_column(
        VARBINARY(512), nullable=True
    )
    pending_totp_secret: Mapped[bytes | None] = mapped_column(
        VARBINARY(512), nullable=True
    )
    totp_setup_token_hash: Mapped[bytes | None] = mapped_column(
        BINARY(32), nullable=True
    )
    totp_setup_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    totp_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0")
    )


class Sessions(Base):
    __tablename__ = "Sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_sessions_user_session"),
        CheckConstraint(
            "ended_at IS NULL OR started_at <= ended_at",
            name="chk_sessions_started_ended",
        ),
        {"schema": "dbo"},
    )

    session_id: Mapped[int] = mapped_column(INT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        INT, ForeignKey("dbo.Users.user_id"), nullable=False
    )
    client_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class RefreshTokens(Base):
    __tablename__ = "RefreshTokens"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "refresh_token_id", name="uq_refresh_tokens_session_token"
        ),
        ForeignKeyConstraint(
            ["session_id", "replaced_by_token_id"],
            ["dbo.RefreshTokens.session_id", "dbo.RefreshTokens.refresh_token_id"],
            name="fk_refresh_tokens_replaced_by",
        ),
        CheckConstraint(
            "expires_at > created_at", name="chk_refresh_tokens_expires_at"
        ),
        CheckConstraint(
            "used_at IS NULL OR used_at >= created_at",
            name="chk_refresh_tokens_used_at",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="chk_refresh_tokens_revoked_at",
        ),
        {"schema": "dbo"},
    )

    refresh_token_id: Mapped[int] = mapped_column(
        BIGINT, primary_key=True, autoincrement=True
    )
    session_id: Mapped[int] = mapped_column(
        INT, ForeignKey("dbo.Sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[bytes] = mapped_column(BINARY(32), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    replaced_by_token_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True)


class Files(Base):
    __tablename__ = "Files"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "session_id"],
            ["dbo.Sessions.user_id", "dbo.Sessions.session_id"],
            name="fk_files_user_session",
        ),
        CheckConstraint("file_size_bytes >= 0", name="chk_files_file_size_bytes"),
        CheckConstraint("status IN ('active', 'deleting')", name="chk_files_status"),
        {"schema": "dbo"},
    )

    file_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    user_id: Mapped[int] = mapped_column(
        INT, ForeignKey("dbo.Users.user_id"), nullable=False
    )
    session_id: Mapped[int] = mapped_column(
        INT, ForeignKey("dbo.Sessions.session_id"), nullable=False
    )
    original_file_name: Mapped[str] = mapped_column(NVARCHAR(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    checksum_sha256: Mapped[bytes] = mapped_column(BINARY(32), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BIGINT, nullable=False)
    file_extension: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'active'")
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UploadReservations(Base):
    __tablename__ = "UploadReservations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "session_id"],
            ["dbo.Sessions.user_id", "dbo.Sessions.session_id"],
            name="fk_upload_reservations_user_session",
        ),
        CheckConstraint(
            "reserved_bytes >= 0", name="chk_upload_reservations_reserved_bytes"
        ),
        CheckConstraint(
            "status IN ('reserved', 'uploading', 'completed')",
            name="chk_upload_reservations_status",
        ),
        CheckConstraint(
            "expires_at > created_at", name="chk_upload_reservations_expires_at"
        ),
        {"schema": "dbo"},
    )

    reservation_id: Mapped[int] = mapped_column(
        BIGINT, primary_key=True, autoincrement=True
    )
    file_id: Mapped[int] = mapped_column(BIGINT, unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        INT, ForeignKey("dbo.Users.user_id"), nullable=False
    )
    session_id: Mapped[int] = mapped_column(
        INT, ForeignKey("dbo.Sessions.session_id"), nullable=False
    )
    reserved_bytes: Mapped[int] = mapped_column(BIGINT, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    upload_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
