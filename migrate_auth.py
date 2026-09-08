"""Create authentication tables and optionally bootstrap the first administrator."""

import argparse
import getpass

from app import app
from models import User, db
from routes.auth import normalize_username, validate_username


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username")
    parser.add_argument("--display-name")
    args = parser.parse_args()

    with app.app_context():
        db.create_all()
        if User.query.count() > 0 and not args.username:
            print("Authentication tables are ready. At least one account already exists.")
            return

        username = normalize_username(args.username or input("Administrator username: "))
        display_name = (args.display_name or input("Administrator display name: ")).strip()
        if not validate_username(username):
            raise SystemExit("Username must be 3-80 lowercase letters, numbers, dots, dashes, or underscores.")
        if not display_name:
            raise SystemExit("Display name is required.")
        if User.query.filter_by(username=username).first():
            raise SystemExit("That username already exists.")

        password = getpass.getpass("Administrator password (12+ characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise SystemExit("Passwords do not match.")
        if len(password) < 12:
            raise SystemExit("Password must contain at least 12 characters.")

        user = User(
            username=username,
            display_name=display_name,
            is_admin=True,
            is_active=True,
            must_change_password=False,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Created administrator: {username}")


if __name__ == "__main__":
    main()
