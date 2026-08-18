# app/api/v1/endpoints/auth.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from pwdlib.exceptions import UnknownHashError

from app.api.deps import CurrrentUser
from app.core.exceptions import AuthenticationError
from app.db.database import DBSession
from app.infrastructure.logging import get_logger
from app.infrastructure.redis.dependencies import (
    AdminRateLimit,
    LoginRateLimit,
    PublicRateLimit,
)
from app.schemas.base import ClientInfo
from app.schemas.users import RefreshTokenRequest, Token, UserCreate
from app.services.auth import (
    authenticate_user,
    logout_user,
    refresh_access_token,
)
from app.services.auth import expire_user_sessions as expire_user_sessions_service
from app.services.users import get_user_by_id

logger = get_logger(__file__)

router = APIRouter(prefix="/auth")


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login/oauth",
    auto_error=False,
)


# # This is not used in admin-only JWT flow.
# @router.post("/register", response_model=UserResponse)
# async def register(user_data: Annotated[UserCreate, Body()], db: DBSession):
#     user = await create_user(
#         username=user_data.username, password=user_data.password, db=db
#     )

#     return user


@router.post("/login", response_model=Token)
async def login(
    user_data: Annotated[UserCreate, Body()],
    db: DBSession,
    request: Request,
    limiter: LoginRateLimit,
):
    """
    Login user with username and password.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    logger.info(
        "Login attempt for user: %s from IP: %s",
        user_data.username,
        client_ip,
    )

    client_info = ClientInfo(
        created_ip=client_ip,
        user_agent=user_agent,
    )

    try:
        tokens = await authenticate_user(
            username=user_data.username,
            password=user_data.password,
            db=db,
            client_info=client_info,
        )
    except AuthenticationError as e:
        logger.warning(
            "Failed login attempt for user: %s from IP: %s - %s",
            user_data.username,
            client_ip,
            str(e),
        )

        # Log user action for failed login
        logger.user_action(
            action="LOGIN",
            username=user_data.username,
            request=request,
            status="FAILED",
            error=str(e),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Success logs after try block
    logger.info(
        "Successful login for user: %s from IP: %s",
        user_data.username,
        client_ip,
    )

    logger.user_action(
        action="LOGIN",
        username=user_data.username,
        request=request,
    )

    return tokens


@router.post("/login/oauth", response_model=Token)
async def login_oauth(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession,
    request: Request,
    limiter: PublicRateLimit,
):
    """
    Login user with OAuth2 password flow.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    username = form_data.username

    logger.info(
        "OAuth login attempt for user: %s from IP: %s",
        username,
        client_ip,
    )

    client_info = ClientInfo(
        created_ip=client_ip,
        user_agent=user_agent,
    )

    try:
        tokens = await authenticate_user(
            username=username,
            password=form_data.password,
            db=db,
            client_info=client_info,
        )
    except AuthenticationError as e:
        logger.warning(
            "Failed OAuth login attempt for user: %s from IP: %s - %s",
            username,
            client_ip,
            str(e),
        )

        logger.user_action(
            action="LOGIN_OAUTH",
            username=username,
            request=request,
            status="FAILED",
            error="Invalid credentials",
        )

        raise HTTPException(
            detail="username or password is wrong",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    except UnknownHashError:
        logger.warning(
            "Unknown hash error during OAuth login for user: %s from IP: %s",
            username,
            client_ip,
        )

        logger.user_action(
            action="LOGIN_OAUTH",
            username=username,
            request=request,
            status="FAILED",
            error="User not found",
        )

        raise HTTPException(
            detail="No user found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Success logs after try block
    logger.info(
        "Successful OAuth login for user: %s from IP: %s",
        username,
        client_ip,
    )

    logger.user_action(
        action="LOGIN_OAUTH",
        username=username,
        request=request,
    )

    return tokens


@router.post("/refresh", response_model=Token, summary="Refresh Access Token Here")
async def refresh(
    request_data: RefreshTokenRequest,
    db: DBSession,
    request: Request,
):
    """
    Refresh access token using refresh token.
    """
    logger.debug(
        "Token refresh attempt from IP: %s",
        request.client.host if request.client else None,
    )

    try:
        new_tokens = await refresh_access_token(token=request_data.refresh_token, db=db)
    except AuthenticationError as e:
        logger.warning(
            "Failed token refresh attempt from IP: %s - %s",
            request.client.host if request.client else None,
            str(e),
        )

        logger.warning(
            "SECURITY: Failed token refresh attempt from IP: %s",
            request.client.host if request.client else None,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Success logs after try block
    logger.info(
        "Successful token refresh for user from IP: %s",
        request.client.host if request.client else None,
    )

    logger.user_action(
        action="TOKEN_REFRESH",
        username="unknown",  # We don't have username here
        request=request,
        status="SUCCESS",
    )

    return new_tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: CurrrentUser,
    request_data: RefreshTokenRequest,
    db: DBSession,
    request: Request,
    limiter: PublicRateLimit,
):
    """
    Logout user by revoking their refresh token.
    This endpoint is idempotent - always returns 204 No Content.
    """
    logger.info(
        "User %s (ID: %s) attempting to logout from IP: %s",
        current_user.username,
        current_user.id,
        request.client.host if request.client else None,
    )

    try:
        await logout_user(
            username=current_user.username,
            refresh_token=request_data.refresh_token,
            db=db,
        )
        # Success logs after successful logout
        logger.info(
            "User %s (ID: %s) logged out successfully from IP: %s",
            current_user.username,
            current_user.id,
            request.client.host if request.client else None,
        )
        logger.user_action(
            action="LOGOUT",
            username=current_user.username,
            request=request,
        )
    except AuthenticationError as e:
        logger.warning(
            "Authentication error during logout for user %s: %s",
            current_user.username,
            str(e),
        )
        logger.user_action(
            action="LOGOUT",
            username=current_user.username,
            request=request,
            status="FAILED",
            error=str(e),
        )
        # Idempotent - still return 204
    except ValueError as e:
        logger.warning(
            "Invalid token during logout for user %s: %s",
            current_user.username,
            str(e),
        )
        logger.user_action(
            action="LOGOUT",
            username=current_user.username,
            request=request,
            status="FAILED",
            error="Invalid token",
        )
        # Idempotent - still return 204
    except Exception as e:
        logger.error(
            "Unexpected error during logout for user %s: %s",
            current_user.username,
            str(e),
            exc_info=True,
        )
        logger.user_action(
            action="LOGOUT",
            username=current_user.username,
            request=request,
            status="FAILED",
            error="Unexpected error",
        )
        # For unexpected errors, we still return 204 to maintain idempotency
        # but log as error for monitoring

    # Always return 204 No Content
    return None


@router.post("/sessions/expire/{user_id}")
async def expire_user_sessions(
    admin: AdminRateLimit,
    user_id: UUID,
    db: DBSession,
    request: Request,
    limiter: PublicRateLimit,
):
    """
    Expire all sessions for a user (Admin only).
    """
    logger.info(
        "Admin %s (ID: %s) attempting to expire sessions for user ID: %s",
        admin.username,
        admin.id,
        user_id,
    )

    try:
        user = await get_user_by_id(user_id=user_id, db=db)
    except AuthenticationError as e:
        logger.warning(
            "Authentication error when fetching user %s: %s",
            user_id,
            str(e),
        )
        logger.admin_action(
            action="SESSIONS_EXPIRE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {UUID} not found",
        )
    except Exception as e:
        logger.error(
            "Unexpected error when fetching user %s: %s",
            user_id,
            str(e),
            exc_info=True,
        )
        logger.admin_action(
            action="SESSIONS_EXPIRE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error="Failed to fetch user",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user",
        )

    if user is None:
        logger.warning(
            "Admin %s (ID: %s) attempted to expire sessions for non-existent user ID: %s",
            admin.username,
            admin.id,
            user_id,
        )

        logger.admin_action(
            action="SESSIONS_EXPIRE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error=f"User with ID {user_id} not found",
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    try:
        result = await expire_user_sessions_service(user_id=user_id, db=db)
    except AuthenticationError as e:
        logger.warning(
            "Authentication error expiring sessions for user %s (ID: %s): %s",
            user.username,
            user_id,
            str(e),
        )

        logger.admin_action(
            action="SESSIONS_EXPIRE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Admin %s failed to expire sessions for user %s (ID: %s): %s",
            admin.username,
            user.username,
            user_id,
            str(e),
        )

        logger.admin_action(
            action="SESSIONS_EXPIRE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to expire sessions",
        )

    # Success logs after try block
    logger.info(
        "Admin %s (ID: %s) expired all sessions for user %s (ID: %s)",
        admin.username,
        admin.id,
        user.username,
        user_id,
    )

    logger.admin_action(
        action="SESSIONS_EXPIRE",
        admin_id=admin.id,
        admin_username=admin.username,
        target_user=user.username,
        target_user_id=user_id,
        request=request,
    )

    return {"detail": f"Sessions for {result.username} expired"}
