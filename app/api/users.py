from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import ActiveUser, AdminUser, CurrrentUser
from app.db.database import DBSession
from app.schemas.base import PaginatedResponse
from app.schemas.users import (
    PasswordChange,
    UserCreate,
    UserDetailedResponse,
    UserFilters,
    UserResponse,
    UserUpdate,
)
from app.services.users import (
    change_password_by_id,
    delete_user_by_id,
    get_user_by_id,
    get_user_by_username,
    get_users,
    update_user_by_id,
)
from app.services.users import create_user as create_user_service

router = APIRouter(prefix="/users")


@router.post("", response_model=UserResponse)
async def create_user(user_data: UserCreate, admin: AdminUser, db: DBSession):
    try:
        result = await create_user_service(
            username=user_data.username,
            password=user_data.password,
            db=db,
            created_by=admin.id,
            must_change_password=True,
            is_active=True,
            role=user_data.role,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return result


@router.get("", response_model=PaginatedResponse[UserResponse])
async def get_users_list(
    admin: AdminUser,
    db: DBSession,
    filters: Annotated[UserFilters, Query()],
):
    try:
        users = await get_users(filters=filters, db=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return users


@router.get("/{user_id}", response_model=UserDetailedResponse)
async def get_user(admin: AdminUser, user_id: UUID, db: DBSession):
    user = await get_user_by_id(user_id=user_id, db=db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"there is no user with id= {user_id}",
        )
    return user


@router.patch("/{user_id}", response_model=UserDetailedResponse)
async def update_user(
    admin: AdminUser, user_id: UUID, user_data: UserUpdate, db: DBSession
):
    user = await update_user_by_id(user_id=user_id, user_data=user_data, db=db)
    return user


@router.patch("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(admin: AdminUser, user_id: UUID, db: DBSession):
    await delete_user_by_id(user_id=user_id, db=db)


@router.post("/{user_id}/password", response_model=UserResponse)
async def change_password(
    admin: AdminUser, user_id: UUID, password_data: PasswordChange, db: DBSession
):
    user = await change_password_by_id(
        user_id=user_id, password_data=password_data, db=db
    )

    return user


@router.get("/me", response_model=UserDetailedResponse)
async def get_profile(user: CurrrentUser, db: DBSession):
    user_data = await get_user_by_username(username=user.username, db=db)
    return user_data


@router.patch("/me", response_model=UserDetailedResponse)
async def update_profile(user: ActiveUser, new_username: str, db: DBSession):
    user_data = UserUpdate(username=new_username)
    return await update_user_by_id(user_id=user.id, user_data=user_data, db=db)


@router.patch("/me/password", response_model=UserResponse)
async def change_own_password(
    user: CurrrentUser, password_data: PasswordChange, db: DBSession
):
    auth_user = await change_password_by_id(
        user_id=user.id, password_data=password_data, db=db
    )

    return {"id": auth_user.id, "username": auth_user.username}
