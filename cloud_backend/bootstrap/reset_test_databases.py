"""Drop the local test databases before recreating them with migrations."""

import argparse
import getpass

import pymssql


def reset_databases(password: str, port: int = 1433) -> None:
    connection = pymssql.connect(
        server="127.0.0.1",
        user="sa",
        password=password,
        database="master",
        port=str(port),
        autocommit=True,
    )
    try:
        cursor = connection.cursor()
        for database in ("CloudCore", "CloudTelemetry"):
            cursor.execute(
                f"IF DB_ID('{database}') IS NOT NULL "
                f"BEGIN ALTER DATABASE [{database}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; "
                f"DROP DATABASE [{database}]; END"
            )  # nosec B608
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", required=True)
    args = parser.parse_args()
    if not args.yes:
        raise SystemExit("Pass --yes to confirm destructive test database reset.")
    reset_databases(getpass.getpass("SQL administrator password for localhost: "))
    print("CloudCore and CloudTelemetry were removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
