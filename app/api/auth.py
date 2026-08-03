from typing import Annotated, Optional

from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib.exceptions import UnknownHashError

from app.api.deps import DBCurrrentUser
from app.core.exceptions import AuthenticationError
from app.db.database import DBSession
from app.schemas.users import Token, UserCreate, UserResponse
from app.services.auth import authenticate_user, logout_user, refresh_access_token
from app.services.user import create_user

router = APIRouter(prefix="/auth")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login/oauth",
    auto_error=False,
)


@router.post("/register", response_model=UserResponse)
async def register(user_data: Annotated[UserCreate, Body()], db: DBSession):
    user = await create_user(
        username=user_data.username, password=user_data.password, db=db
    )

    return user


@router.post("/login", response_model=Token)
async def login(
    user_data: Annotated[UserCreate, Body()], db: DBSession, response: Response
):
    username = user_data.username
    password = user_data.password

    try:
        tokens = await authenticate_user(username=username, password=password, db=db)
    except AuthenticationError as e:
        raise HTTPException(
            detail=e,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    except UnknownHashError:
        raise HTTPException(
            detail="Invalid credentials", status_code=status.HTTP_401_UNAUTHORIZED
        )

    response.set_cookie(tokens["access_token"])
    response.set_cookie(tokens["refresh_token"])
    return tokens


@router.post("/login/oauth")
async def login_oauth(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DBSession
):
    username = form_data.username
    password = form_data.password

    try:
        tokens = await authenticate_user(username=username, password=password, db=db)
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
    db: DBSession,
    response: Response,
    refresh_token_cookie: Annotated[
        Optional[str], Cookie(default=None, alias="refresh_token")
    ] = None,
    raw_token: Annotated[Optional[str], Body()] = None,
):
    token = raw_token or refresh_token_cookie
    try:
        token = raw_token or refresh_token_cookie
        if token is None:
            raise HTTPException(
                detail="Invalid credentials", status_code=status.HTTP_401_UNAUTHORIZED
            )

        new_tokens = await refresh_access_token(token=token, db=db)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    response.set_cookie(
        "access_token",
        new_tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.set_cookie(
        "refresh_token",
        new_tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return new_tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: DBCurrrentUser,
    db: DBSession,
    response: Response,
    refresh_token_cookie: Annotated[
        Optional[str], Cookie(default=None, alias="refresh_token")
    ] = None,
    raw_token: Annotated[Optional[str], Body()] = None,
):
    """
    Logout user by revoking their refresh token.

    Requires the refresh token to be present in the HTTP-only cookie.
    """
    token_to_revoke = refresh_token_cookie or raw_token

    if not current_user.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated"
        )

    if not token_to_revoke:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token is required"
        )

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

    # Clear the cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return {"message": "Logged out successfully"}
