import argparse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cloud Store terminal client")
    parser.add_argument("--admin", action="store_true", help="Open the admin interface")
    parser.add_argument(
        "--base-url",
        default="https://api-cloudvault.tech",
        help="Cloud Store backend URL",
    )
    return parser.parse_args(argv)
