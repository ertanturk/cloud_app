from datetime import datetime

from sqlalchemy import (
    BIGINT,
    INT,
    NVARCHAR,
    CheckConstraint,
    ForeignKey,
    String,
    text,
)
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TelemetryEvents(Base):
    __tablename__ = "TelemetryEvents"
    __table_args__ = ({"schema": "dbo"},)

    event_type_id: Mapped[int] = mapped_column(
        INT, primary_key=True, autoincrement=False, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)


class Telemetry(Base):
    __tablename__ = "Telemetry"
    __table_args__ = (
        CheckConstraint(
            "telemetry_data IS NULL OR ISJSON(telemetry_data) = 1",
            name="chk_telemetry_data_is_json",
        ),
        {"schema": "dbo"},
    )

    event_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(INT, nullable=True)
    session_id: Mapped[int | None] = mapped_column(INT, nullable=True)
    client_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    event_type_id: Mapped[int] = mapped_column(
        INT, ForeignKey("dbo.TelemetryEvents.event_type_id"), nullable=False
    )
    telemetry_data: Mapped[str | None] = mapped_column(NVARCHAR(None), nullable=True)
    event_time: Mapped[datetime] = mapped_column(
        DATETIME2(precision=3), nullable=False, server_default=text("SYSUTCDATETIME()")
    )
