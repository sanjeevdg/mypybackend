
from getpass import getpass

from sqlalchemy import select, insert
from passlib.context import CryptContext

from database import SessionLocal
from auth import auth_users, create_auth_table

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def main():
    email = input("User email: ").strip().lower()

    if not email or "@" not in email:
        print("Please enter a valid email address.")
        return

    password = getpass("Password: ")
    confirm = getpass("Confirm password: ")

    if not password:
        print("Password cannot be empty.")
        return

    if password != confirm:
        print("Passwords do not match.")
        return

    create_auth_table()

    with SessionLocal() as db:
        existing = db.execute(
            select(auth_users.c.id).where(
                auth_users.c.email == email
            )
        ).first()

        if existing:
            print("An account with this email already exists.")
            return

        password_hash = pwd_context.hash(password)

        db.execute(
            insert(auth_users).values(
                email=email,
                password_hash=password_hash,
                role="user",
                is_active=True
            )
        )

        db.commit()

    print(f"User account created successfully: {email}")


if __name__ == "__main__":
    main()
