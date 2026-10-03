"""PenodecorPro do‘kon administratorini yaratish.

Bu skript yuk tashish administrator skriptidan alohida.
Parol ekranda ko‘rinmaydi va faqat Argon2 xeshi saqlanadi.

Ishlatish:
    python -m scripts.create_store_admin admin@example.com
"""
import asyncio
import getpass
import sys

from app.crud.store_admin import StoreAdminWriteError, create_store_admin
from app.db.base import Base  # noqa: F401
from app.db.session import AsyncSessionLocal


async def _create(email: str) -> None:
    full_name = input("Ism: ").strip()
    password = getpass.getpass("Parol (8–128 belgi): ")
    confirm = getpass.getpass("Parolni qaytaring: ")
    if password != confirm:
        print("Parollar mos kelmadi.")
        sys.exit(1)
    async with AsyncSessionLocal() as db:
        try:
            await create_store_admin(db, email=email, full_name=full_name, password=password)
        except StoreAdminWriteError as exc:
            print(exc.message)
            sys.exit(1)
    print("Do‘kon administratori yaratildi.")


def main() -> None:
    if len(sys.argv) != 2:
        print("Ishlatish: python -m scripts.create_store_admin admin@example.com")
        sys.exit(1)
    asyncio.run(_create(sys.argv[1]))


if __name__ == "__main__":
    main()
