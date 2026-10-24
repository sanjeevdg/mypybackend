
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    func,
    CheckConstraint,
)

from database import engine


# Independent metadata: separate from YAML-defined tables.
auth_metadata = MetaData()


auth_users = Table(
    "auth_users",
    auth_metadata,

    Column(
        "id",
        Integer,
        primary_key=True,
        autoincrement=True,
    ),

    Column(
        "email",
        String(320),
        nullable=False,
        unique=True,
        index=True,
    ),

    Column(
        "password_hash",
        String(255),
        nullable=False,
    ),

    Column(
        "role",
        String(20),
        nullable=False,
        server_default="user",
    ),

    Column(
        "is_active",
        Boolean,
        nullable=False,
        server_default="true",
    ),

    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),

    CheckConstraint(
        "role IN ('admin', 'user')",
        name="ck_auth_users_role",
    ),
)


def create_auth_table():
    """Create auth_users if it does not already exist."""
    auth_metadata.create_all(
        bind=engine,
        tables=[auth_users],
        checkfirst=True,
    )
