"""
Script untuk membuat user pertama (admin) di database.
Jalankan sekali: python create_admin.py

Usage:
  python create_admin.py --username admin --password rahasia123 --role admin
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from auth import hash_password
from database import get_user_by_username, create_user


def main():
    parser = argparse.ArgumentParser(description="Buat user GempaBot")
    parser.add_argument("--username", required=True, help="Username")
    parser.add_argument("--password", required=True, help="Password")
    parser.add_argument("--role", default="user", choices=["admin", "user"], help="Role (default: user)")
    args = parser.parse_args()

    existing = get_user_by_username(args.username)
    if existing:
        print(f"[ERROR] Username '{args.username}' sudah ada.")
        sys.exit(1)

    hashed = hash_password(args.password)
    user = create_user(args.username, hashed, args.role)
    if user:
        print(f"[OK] User '{user['username']}' berhasil dibuat dengan role '{user['role']}'.")
        print(f"     ID: {user['id']}")
    else:
        print("[ERROR] Gagal membuat user.")
        sys.exit(1)


if __name__ == "__main__":
    main()
