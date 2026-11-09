"""Create the Telemetry database schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "TelemetryEvents",
        sa.Column("event_type_id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("event_type", sa.String(50), nullable=False, unique=True),
        schema="dbo",
    )
    op.create_table(
        "Telemetry",
        sa.Column("event_id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer),
        sa.Column("session_id", sa.Integer),
        sa.Column("client_ip", sa.String(45), nullable=False),
        sa.Column(
            "event_type_id",
            sa.Integer,
            sa.ForeignKey("dbo.TelemetryEvents.event_type_id"),
            nullable=False,
        ),
        sa.Column("telemetry_data", sa.UnicodeText),
        sa.Column(
            "event_time",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="dbo",
    )


def downgrade() -> None:
    op.drop_table("Telemetry", schema="dbo")
    op.drop_table("TelemetryEvents", schema="dbo")
