"""SQL Server service and authentication health checks."""

import socket
import time

import pymssql

from .sql_discovery import SqlInstance


def wait_for_sql(
    instance: SqlInstance,
    password: str,
    port: int = 1433,
    attempts: int = 12,
) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3):
                pass
            connection = pymssql.connect(
                server="127.0.0.1",
                user="sa",
                password=password,
                database="master",
                port=port,
                login_timeout=5,
                timeout=5,
            )
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            finally:
                connection.close()
            return
        except (OSError, pymssql.Error) as error:
            last_error = error
            time.sleep(5)
    raise RuntimeError(f"SQL Server health check failed: {last_error}") from last_error
