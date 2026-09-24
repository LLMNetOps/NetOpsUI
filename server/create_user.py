"""Create an operator, or reset an existing operator's password.

    docker compose exec manager python create_user.py <username>

The password is read from the terminal (never from an argument or the
environment). Resetting a password also ends that user's sessions.
"""
from __future__ import annotations

import getpass
import sys

import auth
import db


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    username = sys.argv[1]
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Ulangi password: "):
        print("Password tidak sama.")
        return 1
    db.init()
    try:
        created = auth.upsert_user(username, password)
    except ValueError as e:
        print(e)
        return 1
    print(f"User '{username}' {'dibuat' if created else 'diperbarui (password direset)'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
