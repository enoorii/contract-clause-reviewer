from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from pwdlib.exceptions import UnknownHashError

from app.api.deps import AdminUser, CurrrentUser
from app.core.exceptions import AuthenticationError
from app.db.database import DBSession
from app.schemas.base import ClientInfo
from app.schemas.users import Token, UserCreate
from app.services.auth import (
    authenticate_user,
    logout_user,
    refresh_access_token,
)
from app.services.auth import expire_user_sessions as expire_user_sessions_service

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
):
    client_info = ClientInfo(
        created_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    try:
        tokens = await authenticate_user(
            username=user_data.username,
            password=user_data.password,
            db=db,
            client_info=client_info,
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return tokens


@router.post("/login/oauth")
async def login_oauth(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession,
    request: Request,
):
    client_info = ClientInfo(
        created_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    username = form_data.username
    password = form_data.password

    try:
        tokens = await authenticate_user(
            username=username, password=password, db=db, client_info=client_info
        )
    except AuthenticationError:
        raise HTTPException(
            detail="username or password is wrong",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    except UnknownHashError:
        raise HTTPException(
            detail="No user found", status_code=status.HTTP_404_NOT_FOUND
        )

    return tokens


@router.post("/refresh", response_model=Token, summary="Refresh Access Token Here")
async def refresh(
    refresh_token: Annotated[str, Body(...)],
    db: DBSession,
):
    token = refresh_token
    try:
        new_tokens = await refresh_access_token(token=token, db=db)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    return new_tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: CurrrentUser,
    refresh_token: Annotated[str, Body(...)],
    db: DBSession,
):
    """
    Logout user by revoking their refresh token.

    Requires the refresh token to be present in the HTTP-only cookie.
    """
    token_to_revoke = refresh_token

    try:
        await logout_user(
            username=current_user.username, refresh_token=token_to_revoke, db=db
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid token: {str(e)}"
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        # Log the actual error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )

    return {"message": "Logged out successfully"}


@router.post("/sessions/expire/{user_id}")
async def expire_user_sessions(
    admin: AdminUser,
    user_id: UUID,
    db: DBSession,
):
    return await expire_user_sessions_service(user_id=user_id, db=db)
