# app/api/deps.py

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from pydantic.config import ConfigDict
from sqlalchemy.exc import NoResultFound

from app.core.enums import Role
from app.core.exceptions import AuthenticationError
from app.db.database import DBSession
from app.services.auth import authenticate_user_by_token


class AuthUser(BaseModel):
    id: UUID
    username: str
    role: Role
    is_active: bool
    must_change_password: bool
    source: str = "jwt"
    jti: str | None = None

    model_config = ConfigDict(from_attributes=True)


security = HTTPBearer()


async def get_current_user(
    db: DBSession,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """Main authentication dependency. Handles both API key and JWT."""

    token = credentials.credentials

    # JWT token must be present
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify JWT access token
    try:
        jti, user_data = await authenticate_user_by_token(token=token, db=db)
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

    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(jti=jti, **user_data)


CurrrentUser = Annotated[AuthUser, Depends(get_current_user)]


async def require_active(user: CurrrentUser):
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is not active"
        )
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required",
            headers={"X-Password-Change-Required": "true"},
        )
    return user


ActiveUser = Annotated[AuthUser, Depends(require_active)]


async def require_admin(user: ActiveUser):
    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return user


AdminUser = Annotated[AuthUser, Depends(require_admin)]
