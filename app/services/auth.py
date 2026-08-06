from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from pwdlib.exceptions import UnknownHashError
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from app.core.config import setting
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_tokens_for_user,
    hash_password_async,
    rotate_refresh_token,
    verify_access_token,
    verify_password_async,
    verify_refresh_token,
)
from app.db.database import DBSession
from app.infrastructure.logging import get_logger
from app.models.models import RefreshToken, Users
from app.repositories.refresh_token_repositories import get_refresh_token
from app.repositories.user_repositories import (
    get_user_by_id_repo,
    get_user_by_username_repo,
)
from app.schemas.base import ClientInfo

logger = get_logger(name=__file__)


async def authenticate_user(
    username: str,
    password: str,
    db: DBSession,
    client_info: ClientInfo,
):
    """Authenticate user and create tokens."""

    user = await get_user_by_username_repo(
        username=username,
        db=db,
    )

    if user is None:
        raise AuthenticationError("Invalid credentials")

    try:
        password_valid = await verify_password_async(
            password=password,
            password_hash=user.password_hash,
        )

        if not password_valid:
            raise AuthenticationError("Invalid credentials")

    except UnknownHashError:
        logger.error(
            "Unknown password hash for user: %s",
            username,
        )
        raise AuthenticationError("Invalid credentials")

    tokens = await create_tokens_for_user(
        user=user,
        db=db,
    )

    refresh_token = RefreshToken(
        token_hash=await hash_password_async(password=tokens["refresh_token"]),
        user_id=user.id,
        expires_at=(
            datetime.now(UTC) + timedelta(days=setting.REFRESH_TOKEN_EXPIRATION_DAYS)
        ),
        created_ip=client_info.created_ip,
        user_agent=client_info.user_agent,
    )

    db.add(refresh_token)

    return tokens


async def authenticate_user_by_token(token: str, db: DBSession):
    """Authenticate user - returns tokens or raises AuthenticationError"""
    jti, username = await verify_access_token(token=token, db=db)

    if username is None:
        raise AuthenticationError("Invalid credentials")

    user = await get_user_by_username_repo(username=username, db=db)
    if user is None:
        raise AuthenticationError("Invalid credentials")

    user_data = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
    }

    return jti, user_data


async def logout_user(username: str, refresh_token: str, db: DBSession):
    user = await get_user_by_username_repo(
        username=username,
        db=db,
    )

    token = await get_refresh_token(
        raw_token=refresh_token,
        db=db,
        options=[selectinload(cast(InstrumentedAttribute, RefreshToken.user))],
    )
    if user.username == token.user.username:
        token.is_revoked = True
    else:
        AuthenticationError("Invalid credentials")


async def refresh_access_token(token: str, db: DBSession):
    try:
        await verify_refresh_token(raw_token=token, db=db)
    except ValueError:
        raise AuthenticationError("Invalid credentials")

    new_tokens = await rotate_refresh_token(old_raw_token=token, db=db)
    return new_tokens


async def expire_user_sessions(user_id: UUID, db: DBSession):
    user = await get_user_by_id_repo(
        user_id=user_id,
        db=db,
        options=[selectinload(cast(InstrumentedAttribute, Users.refresh_tokens))],
    )

    for token in user.refresh_tokens:
        if not token.is_revoked:
            token.is_revoked = True

    return user
