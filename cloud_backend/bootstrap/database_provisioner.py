"""Idempotent Cloud Store database and login provisioning."""

import re
from urllib.parse import quote_plus

import pymssql

from .passwords import prompt_password
from .sql_discovery import SqlInstance


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", value):
        raise ValueError(
            "SQL identifiers must start with a letter and contain only A-Z, 0-9, _."
        )
    return value


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def provision(
    instance: SqlInstance, bootstrap_password: str, port: int = 1433
) -> tuple[str, str]:
    app_user = _identifier(input("Cloud Store SQL application username: ").strip())
    app_password = prompt_password("Cloud Store SQL application password: ")
    connection = pymssql.connect(
        server="127.0.0.1",
        user="sa",
        password=bootstrap_password,
        database="master",
        port=str(port),
        autocommit=True,
    )
    try:
        cursor = connection.cursor()
        for database in ("CloudCore", "CloudTelemetry"):
            cursor.execute(  # nosec B608
                f"IF DB_ID({_literal(database)}) IS NULL CREATE DATABASE [{database}]"
            )
        cursor.execute(  # nosec B608
            "IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = %s) "
            f"BEGIN CREATE LOGIN [{app_user}] WITH PASSWORD = {_literal(app_password)} END "
            f"ELSE ALTER LOGIN [{app_user}] WITH PASSWORD = {_literal(app_password)}",  # nosec B608
            (app_user,),
        )
        for database in ("CloudCore", "CloudTelemetry"):
            cursor.execute(f"USE [{database}]")
            cursor.execute(  # nosec B608
                "IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = %s) "
                f"CREATE USER [{app_user}] FOR LOGIN [{app_user}]",  # nosec B608
                (app_user,),
            )
            cursor.execute(  # nosec B608
                "IF NOT EXISTS ("
                "SELECT 1 FROM sys.database_role_members drm "
                "JOIN sys.database_principals role_principal "
                "ON role_principal.principal_id = drm.role_principal_id "
                "JOIN sys.database_principals user_principal "
                "ON user_principal.principal_id = drm.member_principal_id "
                "WHERE role_principal.name = 'db_owner' AND user_principal.name = %s"
                f") ALTER ROLE db_owner ADD MEMBER [{app_user}]",  # nosec B608
                (app_user,),
            )
    finally:
        connection.close()
    encoded = quote_plus(app_password)
    return (
        f"mssql+pymssql://{app_user}:{encoded}@{instance.server}:{port}/CloudCore",
        f"mssql+pymssql://{app_user}:{encoded}@{instance.server}:{port}/CloudTelemetry",
    )
