
import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from database import SessionLocal
from auth import auth_users


AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY")

if not AUTH_SECRET_KEY:
    raise RuntimeError(
        "AUTH_SECRET_KEY environment variable is not configured."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30

bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user: dict) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }

    return jwt.encode(
        payload,
        AUTH_SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    unauthorized = HTTPException(
        status_code=401,
        detail="Authentication required or token expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = jwt.decode(
            credentials.credentials,
            AUTH_SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")

        if not user_id:
            raise unauthorized

        user_id = int(user_id)

    except (JWTError, ValueError, TypeError):
        raise unauthorized

    with SessionLocal() as db:
        result = db.execute(
            select(auth_users).where(auth_users.c.id == user_id)
        )

        user = result.mappings().first()

        if user is None or not user["is_active"]:
            raise unauthorized

        return {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
        }


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required.",
        )

    return current_user
