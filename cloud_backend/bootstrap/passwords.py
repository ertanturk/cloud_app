"""Interactive password prompts used by the Windows bootstrap."""

import getpass


def prompt_password(label: str, minimum_length: int = 12, attempts: int = 3) -> str:
    """Prompt repeatedly until a password meets the bootstrap policy."""
    for attempt in range(attempts):
        password = getpass.getpass(label)
        if len(password) >= minimum_length:
            return password
        remaining = attempts - attempt - 1
        if remaining:
            print(
                f"Password must contain at least {minimum_length} characters. "
                f"Attempts remaining: {remaining}."
            )
    raise ValueError(f"Password must contain at least {minimum_length} characters.")
