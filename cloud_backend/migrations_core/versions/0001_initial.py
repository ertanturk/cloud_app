""" "Create the Core database schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "IF NOT EXISTS (SELECT 1 FROM sys.sequences "
        "WHERE name = 'FileIdSequence' AND schema_id = SCHEMA_ID('dbo')) "
        "CREATE SEQUENCE dbo.FileIdSequence AS BIGINT START WITH 1 INCREMENT BY 1"
    )
    op.create_table(
        "Users",
        sa.Column("user_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.Unicode(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("password_hash_version", sa.SmallInteger, nullable=False),
        sa.Column(
            "role", sa.String(20), nullable=False, server_default=sa.text("'user'")
        ),
        sa.Column(
            "storage_quota_bytes",
            sa.BigInteger,
            nullable=False,
            server_default=sa.text("10000000000"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("role IN ('user', 'admin')", name="chk_users_role"),
        sa.CheckConstraint(
            "storage_quota_bytes > 0", name="chk_users_storage_quota_bytes"
        ),
        schema="dbo",
    )
    op.create_table(
        "UserSecrets",
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("dbo.Users.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("password_salt", sa.LargeBinary(16), nullable=False),
        sa.Column("encrypted_totp_secret", sa.LargeBinary(512)),
        sa.Column("pending_totp_secret", sa.LargeBinary(512)),
        sa.Column("totp_setup_token_hash", sa.LargeBinary(32)),
        sa.Column("totp_setup_expires_at", sa.DateTime),
        sa.Column(
            "totp_enabled", sa.Boolean, nullable=False, server_default=sa.text("0")
        ),
        sa.CheckConstraint(
            "totp_enabled IN (0, 1)", name="chk_user_secrets_totp_enabled"
        ),
        schema="dbo",
    )
    op.create_table(
        "Sessions",
        sa.Column("session_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("dbo.Users.user_id"), nullable=False
        ),
        sa.Column("client_ip", sa.String(45), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("ended_at", sa.DateTime),
        sa.Column("last_activity_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "session_id", name="uq_sessions_user_session"),
        sa.CheckConstraint(
            "ended_at IS NULL OR started_at <= ended_at",
            name="chk_sessions_started_ended",
        ),
        schema="dbo",
    )
    op.create_table(
        "RefreshTokens",
        sa.Column(
            "refresh_token_id", sa.BigInteger, primary_key=True, autoincrement=True
        ),
        sa.Column(
            "session_id",
            sa.Integer,
            sa.ForeignKey("dbo.Sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used_at", sa.DateTime),
        sa.Column("revoked_at", sa.DateTime),
        sa.Column("replaced_by_token_id", sa.BigInteger),
        sa.UniqueConstraint(
            "session_id", "refresh_token_id", name="uq_refresh_tokens_session_token"
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name="chk_refresh_tokens_expires_at"
        ),
        sa.CheckConstraint(
            "used_at IS NULL OR used_at >= created_at",
            name="chk_refresh_tokens_used_at",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="chk_refresh_tokens_revoked_at",
        ),
        schema="dbo",
    )
    op.create_foreign_key(
        "fk_refresh_tokens_replaced_by",
        "RefreshTokens",
        "RefreshTokens",
        ["session_id", "replaced_by_token_id"],
        ["session_id", "refresh_token_id"],
        source_schema="dbo",
        referent_schema="dbo",
    )
    op.create_table(
        "Files",
        sa.Column("file_id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("dbo.Users.user_id"), nullable=False
        ),
        sa.Column(
            "session_id",
            sa.Integer,
            sa.ForeignKey("dbo.Sessions.session_id"),
            nullable=False,
        ),
        sa.Column("original_file_name", sa.Unicode(255), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False, unique=True),
        sa.Column("checksum_sha256", sa.LargeBinary(32), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("file_extension", sa.String(20)),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'active'")
        ),
        sa.Column("uploaded_at", sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "session_id"],
            ["dbo.Sessions.user_id", "dbo.Sessions.session_id"],
            name="fk_files_user_session",
        ),
        sa.CheckConstraint("file_size_bytes >= 0", name="chk_files_file_size_bytes"),
        sa.CheckConstraint("status IN ('active', 'deleting')", name="chk_files_status"),
        schema="dbo",
    )
    op.create_table(
        "UploadReservations",
        sa.Column(
            "reservation_id", sa.BigInteger, primary_key=True, autoincrement=True
        ),
        sa.Column("file_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("dbo.Users.user_id"), nullable=False
        ),
        sa.Column(
            "session_id",
            sa.Integer,
            sa.ForeignKey("dbo.Sessions.session_id"),
            nullable=False,
        ),
        sa.Column("reserved_bytes", sa.BigInteger, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("upload_started_at", sa.DateTime),
        sa.Column("last_activity_at", sa.DateTime),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime),
        sa.ForeignKeyConstraint(
            ["user_id", "session_id"],
            ["dbo.Sessions.user_id", "dbo.Sessions.session_id"],
            name="fk_upload_reservations_user_session",
        ),
        sa.CheckConstraint(
            "reserved_bytes >= 0", name="chk_upload_reservations_reserved_bytes"
        ),
        sa.CheckConstraint(
            "status IN ('reserved', 'uploading', 'completed')",
            name="chk_upload_reservations_status",
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name="chk_upload_reservations_expires_at"
        ),
        schema="dbo",
    )


def downgrade() -> None:
    op.drop_table("UploadReservations", schema="dbo")
    op.drop_table("Files", schema="dbo")
    op.drop_constraint(
        "fk_refresh_tokens_replaced_by",
        "RefreshTokens",
        schema="dbo",
        type_="foreignkey",
    )
    op.drop_table("RefreshTokens", schema="dbo")
    op.drop_table("Sessions", schema="dbo")
    op.drop_table("UserSecrets", schema="dbo")
    op.drop_table("Users", schema="dbo")
    op.execute("DROP SEQUENCE dbo.FileIdSequence")
