#!/usr/bin/env python3
"""Script to make a user admin."""

import sys
from pathlib import Path

# Add the parent directory to sys.path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config.database import SessionLocal
from backend.domains.user.repository import SqlAlchemyUserRepository
from backend.domains.user.models import User


def make_user_admin(user_id: int):
    """Make a user admin by setting their role."""
    with SessionLocal() as db:
        repo = SqlAlchemyUserRepository(db)
        user = repo.get(user_id)

        if not user:
            print(f"❌ User with ID {user_id} not found")
            return

        if user.role == "admin":
            print(f"✅ User {user.id} ({user.name or user.email}) is already an admin")
            return

        user.role = "admin"
        db.commit()
        db.refresh(user)

        print(f"✅ User {user.id} ({user.name or user.email}) is now an admin")


def set_user_name(user_id: int, name: str):
    """Set a user's display name."""
    with SessionLocal() as db:
        repo = SqlAlchemyUserRepository(db)
        user = repo.get(user_id)

        if not user:
            print(f"❌ User with ID {user_id} not found")
            return

        old_name = user.name
        user.name = name
        db.commit()
        db.refresh(user)

        print(f"✅ Updated user {user.id} name from '{old_name}' to '{name}'")


def list_users():
    """List all users with their roles."""
    with SessionLocal() as db:
        users = db.query(User).all()

        print("📋 All users:")
        for user in users:
            print(f"  ID: {user.id}, Name: {user.name or 'N/A'}, Email: {user.email or 'N/A'}, Role: {user.role}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python make_admin.py list                    # List all users")
        print("  python make_admin.py admin <user_id>         # Make user admin")
        print("  python make_admin.py name <user_id> <name>   # Set user name")
        sys.exit(1)

    if sys.argv[1] == "list":
        list_users()
    elif sys.argv[1] == "admin":
        if len(sys.argv) < 3:
            print("❌ User ID required")
            sys.exit(1)
        try:
            user_id = int(sys.argv[2])
            make_user_admin(user_id)
        except ValueError:
            print("❌ User ID must be a number")
            sys.exit(1)
    elif sys.argv[1] == "name":
        if len(sys.argv) < 4:
            print("❌ User ID and name required")
            sys.exit(1)
        try:
            user_id = int(sys.argv[2])
            name = sys.argv[3]
            set_user_name(user_id, name)
        except ValueError:
            print("❌ User ID must be a number")
            sys.exit(1)
    else:
        print("❌ Unknown command. Use 'list', 'admin', or 'name'")
        sys.exit(1)