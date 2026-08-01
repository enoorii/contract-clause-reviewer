from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib.exceptions import UnknownHashError

from app.core.security import verify_password
from app.db.database import DBSession
from app.schemas.schemas import UserCreate, UserDetailedResponse, UserResponse
from app.services.services import create_user, get_user_by_username

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


@router.post("/login", response_model=UserDetailedResponse)
async def login(user_data: Annotated[UserCreate, Body()], db: DBSession):
    pass


@router.post("/login/oauth")
async def login_oauth(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DBSession
):
    username = form_data.username
    password = form_data.password

    user = await get_user_by_username(username=username, db=db)

    if not user:
        raise HTTPException(
            detail="No user found", status_code=status.HTTP_404_NOT_FOUND
        )

    try:
        if not verify_password(password=password, password_hash=user.password_hash):
            raise HTTPException(
                detail="No user found", status_code=status.HTTP_401_UNAUTHORIZED
            )
    except UnknownHashError:
        raise HTTPException(
            detail="No user found", status_code=status.HTTP_401_UNAUTHORIZED
        )

    return ["access token", "refresh token"]
