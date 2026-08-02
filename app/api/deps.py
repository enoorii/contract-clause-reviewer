# app/api/deps.py
from dataclasses import dataclass
from typing import Annotated, Optional
from uuid import UUID

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.exc import NoResultFound

from app.api.auth import oauth2_scheme
from app.db.database import DBSession
from app.services.auth import authenticate_user_by_token


@dataclass
class AuthUser:
    id: UUID | None
    username: str
    source: str = "jwt"
    jti: str | None = None


async def get_current_user(
    db: DBSession,
    header_token: Optional[str] = Depends(oauth2_scheme),
    cookie_token: Annotated[
        Optional[str], Cookie(default=None, alias="access_token")
    ] = None,
) -> AuthUser:
    """Main authentication dependency. Handles both API key and JWT."""

    token = header_token or cookie_token
    # JWT token must be present
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify JWT access token
    try:
        jti, user = await authenticate_user_by_token(token=token, db=db)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, ValueError, NoResultFound):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(id=user.id, username=user.username, jti=jti)


DBCurrrentUser = Annotated[AuthUser, Depends(get_current_user)]
