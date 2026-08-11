from datetime import UTC, datetime
from typing import Optional, cast
from uuid import UUID

import jwt
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from app.core.config import setting
from app.core.exceptions import AuthenticationError
from app.core.security import (
    RefreshTokenData,
    TokenStore,
    create_tokens_for_user,
    hash_token,
    rotate_refresh_token,
    verify_access_token,
    verify_password_async,
    verify_refresh_token,
)
from app.db.database import DBSession
from app.infrastructure.logging import get_logger
from app.models.models import RefreshToken, Users
from app.repositories.refresh_token_repositories import (
    get_refresh_token_by_hash,
    revoke_refresh_token_by_hash,
    update_refresh_token_usage_by_hash,
)
from app.repositories.user_repositories import (
    get_user_by_id_repo,
    get_user_by_username_repo,
)
from app.schemas.base import ClientInfo

logger = get_logger(name=__file__)


# ---------- Database TokenStore Implementation ----------
class DatabaseTokenStore(TokenStore):
    def __init__(self, db: DBSession):
        self.db = db

    async def get_refresh_token_by_hash(
        self, token_hash: str
    ) -> Optional[RefreshTokenData]:
        token = await get_refresh_token_by_hash(
            token_hash=token_hash,
            db=self.db,
            options=[selectinload(cast(InstrumentedAttribute, RefreshToken.user))],
        )
        if not token:
            return None
        return RefreshTokenData(
            token_hash=token.token_hash,
            user_id=str(token.user_id),
            expires_at=token.expires_at,
            created_ip=token.created_ip,
            user_agent=token.user_agent,
            is_revoked=token.is_revoked,
            last_used_at=token.last_used_at,
        )

    async def create_refresh_token(self, token_data: RefreshTokenData) -> None:
        # Convert to model and save
        refresh_token = RefreshToken(
            token_hash=token_data.token_hash,
            user_id=UUID(token_data.user_id),
            expires_at=token_data.expires_at,
            created_ip=token_data.created_ip,
            user_agent=token_data.user_agent,
            is_revoked=token_data.is_revoked,
            last_used_at=token_data.last_used_at or datetime.now(UTC),
        )
        self.db.add(refresh_token)

    async def revoke_refresh_token(self, token_hash: str) -> None:
        await revoke_refresh_token_by_hash(token_hash=token_hash, db=self.db)

    async def update_refresh_token_usage(self, token_hash: str) -> None:
        await update_refresh_token_usage_by_hash(token_hash=token_hash, db=self.db)

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        user = await get_user_by_id_repo(user_id=UUID(user_id), db=self.db)
        if not user:
            return None
        return {
            "id": str(user.id),
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
        }


# ---------- Authentication Services ----------
async def authenticate_user(
    username: str,
    password: str,
    db: DBSession,
    client_info: ClientInfo,
):
    """Authenticate user and create tokens."""
    user = await get_user_by_username_repo(username=username, db=db)
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
        logger.error("Unknown password hash for user: %s", username)
        raise AuthenticationError("Invalid credentials")

    token_store = DatabaseTokenStore(db)
    tokens = await create_tokens_for_user(
        user_id=str(user.id),
        username=user.username,
        token_store=token_store,
        secret_key=setting.SECRET_KEY,
        access_expiration_minutes=setting.ACCESS_TOKEN_EXPIRATION_MINUTES,
        refresh_expiration_days=setting.REFRESH_TOKEN_EXPIRATION_DAYS,
        created_ip=client_info.created_ip,
        user_agent=client_info.user_agent,
    )
    return tokens


async def authenticate_user_by_token(token: str, db: DBSession):
    """Authenticate user via access token."""
    try:
        jti, username = await verify_access_token(
            token=token,
            secret_key=setting.SECRET_KEY,
        )
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError) as e:
        raise AuthenticationError("Invalid credentials") from e

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
    """Revoke the refresh token if it belongs to the user."""
    user = await get_user_by_username_repo(username=username, db=db)
    if not user:
        raise AuthenticationError("Invalid credentials")

    token_hash = hash_token(refresh_token)  # need to import hash_token
    token = await get_refresh_token_by_hash(
        token_hash=token_hash,
        db=db,
        options=[selectinload(cast(InstrumentedAttribute, RefreshToken.user))],
    )
    if not token or token.user.username != username:
        raise AuthenticationError("Invalid credentials")

    token.is_revoked = True
    db.add(token)


async def refresh_access_token(
    token: str, db: DBSession, client_info: Optional[ClientInfo] = None
):
    """Refresh access token using a valid refresh token."""
    token_store = DatabaseTokenStore(db)
    try:
        # First verify the token (this will raise if invalid)
        await verify_refresh_token(raw_token=token, token_store=token_store)
    except ValueError:
        raise AuthenticationError("Invalid credentials")

    # Perform rotation
    new_tokens = await rotate_refresh_token(
        old_raw_token=token,
        token_store=token_store,
        secret_key=setting.SECRET_KEY,
        access_expiration_minutes=setting.ACCESS_TOKEN_EXPIRATION_MINUTES,
        new_ip=client_info.created_ip if client_info else None,
        new_user_agent=client_info.user_agent if client_info else None,
    )
    return new_tokens


async def expire_user_sessions(user_id: UUID, db: DBSession):
    """Revoke all refresh tokens for a user."""
    user = await get_user_by_id_repo(
        user_id=user_id,
        db=db,
        options=[selectinload(cast(InstrumentedAttribute, Users.refresh_tokens))],
    )
    if not user:
        raise AuthenticationError("User not found")

    for token in user.refresh_tokens:
        if not token.is_revoked:
            token.is_revoked = True
    return user
