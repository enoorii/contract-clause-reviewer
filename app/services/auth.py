from pwdlib.exceptions import UnknownHashError

from app.core.exceptions import AuthenticationError
from app.infrastructure.logging import get_logger
from app.core.security import (
    create_tokens_for_user,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_access_token,
    verify_password,
    verify_refresh_token,
)
from app.db.database import DBSession
from app.repositories.user_repositories import (
    get_user_by_username_repo,
)

logger = get_logger(name=__file__)


async def authenticate_user(username: str, password: str, db: DBSession):
    """Authenticate user - returns tokens or raises AuthenticationError"""
    user = await get_user_by_username_repo(username=username, db=db)

    if user is None:
        raise AuthenticationError("Invalid credentials")

    try:
        if not verify_password(password=password, password_hash=user.password_hash):
            raise AuthenticationError("Invalid credentials")
    except UnknownHashError:
        # Log the error internally for debugging
        logger.error(f"Unknown hash error for user: {username}")
        raise AuthenticationError("Invalid credentials")

    return await create_tokens_for_user(user=user, db=db)


async def authenticate_user_by_token(token: str, db: DBSession):
    """Authenticate user - returns tokens or raises AuthenticationError"""
    jti, username = await verify_access_token(token=token, db=db)

    if username is None:
        raise AuthenticationError("Invalid credentials")

    user = await get_user_by_username_repo(username=username, db=db)
    if user is None:
        raise AuthenticationError("Invalid credentials")

    return jti, user


async def logout_user(username: str, refresh_token: str, db: DBSession):
    result = await verify_refresh_token(raw_token=refresh_token, db=db)
    if result.user.username == username:
        await revoke_refresh_token(raw_token=refresh_token, db=db)
    else:
        AuthenticationError("Invalid credentials")


async def refresh_access_token(token: str, db: DBSession):
    try:
        await verify_refresh_token(raw_token=token, db=db)
    except ValueError:
        raise AuthenticationError("Invalid credentials")

    new_tokens = await rotate_refresh_token(old_raw_token=token, db=db)
    return new_tokens
