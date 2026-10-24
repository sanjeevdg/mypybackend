
from getpass import getpass

from sqlalchemy import select, insert
from passlib.context import CryptContext

from auth import auth_users, create_auth_table
from database import engine


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def create_admin():
    print("\n=== Create Initial Admin Account ===\n")

    email = input("Admin email: ").strip().lower()

    if not email or "@" not in email:
        print("Error: Please enter a valid email address.")
        return

    password = getpass("Admin password: ")
    confirm_password = getpass("Confirm password: ")

    if not password:
        print("Error: Password cannot be empty.")
        return

    if password != confirm_password:
        print("Error: Passwords do not match.")
        return

    # bcrypt supports passwords up to 72 bytes.
    if len(password.encode("utf-8")) > 72:
        print("Error: Password must not exceed 72 UTF-8 bytes.")
        return

    # Create only the dedicated authentication table.
    create_auth_table()

    with engine.begin() as connection:
        existing_user = connection.execute(
            select(auth_users.c.id).where(
                auth_users.c.email == email
            )
        ).first()

        if existing_user:
            print(
                f"An account already exists for {email}. "
                "No changes were made."
            )
            return

        password_hash = pwd_context.hash(password)

        connection.execute(
            insert(auth_users).values(
                email=email,
                password_hash=password_hash,
                role="admin",
                is_active=True,
            )
        )

    print("\nAdmin account created successfully.")
    print(f"Email: {email}")
    print("Role: admin")


if __name__ == "__main__":
    try:
        create_admin()
    except Exception as error:
        print(f"\nCould not create admin account: {error}")
        print("Check your database connection and auth.py configuration.")
