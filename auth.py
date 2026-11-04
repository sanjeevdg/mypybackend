
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    func,
    ForeignKey,
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



password_reset_tokens = Table(
    "password_reset_tokens",
    auth_metadata,

    Column(
        "id",
        Integer,
        primary_key=True,
        autoincrement=True,
    ),

    Column(
        "user_id",
        Integer,
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),

    Column(
        "token_hash",
        String(64),
        nullable=False,
        unique=True,
    ),

    Column(
        "expires_at",
        DateTime(timezone=True),
        nullable=False,
    ),

    Column(
        "used_at",
        DateTime(timezone=True),
        nullable=True,
    ),

    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)



def create_auth_table():
    """Create authentication and password-reset tables."""

    auth_metadata.create_all(
        bind=engine,
        tables=[
            auth_users,
            password_reset_tokens
        ],
        checkfirst=True,
    )