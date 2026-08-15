# app/services/users.py
from typing import cast
from uuid import UUID

from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from app.core.enums import Role
from app.core.exceptions import AuthenticationError
from app.core.security import (
    hash_password_async,
    verify_password_async,
)
from app.db.database import DBSession
from app.models.models import User
from app.repositories.user_repositories import (
    create_user_repo,
    delete_user_by_id_repo,
    get_user_by_id_repo,
    get_user_by_username_repo,
    get_users_repo,
    get_users_total,
)
from app.schemas.users import PasswordChange, UserFilters, UserUpdate


async def get_user_by_username(username: str, db: DBSession):
    try:
        return await get_user_by_username_repo(
            username=username,
            db=db,
            options=[selectinload(cast(InstrumentedAttribute, User.analyses))],
        )
    except (NoResultFound, MultipleResultsFound):
        raise AuthenticationError("Invalid credentials")


async def create_user(
    username: str,
    password: str,
    created_by: UUID,
    db: DBSession,
    role: Role,
    must_change_password: bool = True,
    is_active: bool = True,
):
    try:
        existing = await get_user_by_username_repo(username=username, db=db)
    except (NoResultFound, MultipleResultsFound):
        existing = None
    if existing:
        raise ValueError("Username already exist")
    password_hash = await hash_password_async(password=password)
    user = await create_user_repo(
        username=username,
        password_hash=password_hash,
        db=db,
        role=role,
        created_by=created_by,
        must_change_password=must_change_password,
        is_active=is_active,
    )

    return user


async def get_users(db: DBSession, filters: UserFilters) -> dict:
    """Get all tasks with filtering, ordering, and pagination."""

    try:
        total = await get_users_total(filters=filters, db=db)
    except (NoResultFound, MultipleResultsFound):
        total = 0

    assert isinstance(filters.size, int) and isinstance(filters.page, int)
    # Calculate pages
    if total >= 1:
        pages = (total + filters.size - 1) // filters.size
        max_page = pages
    else:
        pages = 1
        max_page = 1

    if filters.page > max_page and total > 0:
        raise ValueError(f"Page {filters.page} not found. Max page is {max_page}")

    try:
        users = await get_users_repo(filters=filters, db=db)
    except (NoResultFound, MultipleResultsFound):
        users = []

    return {
        "items": users,
        "total": total,
        "page": filters.page,
        "size": filters.size,
        "pages": pages,
    }


async def get_user_by_id(user_id: UUID, db: DBSession):
    """Get a single user by ID."""
    try:
        user = await get_user_by_id_repo(user_id=user_id, db=db)
    except (NoResultFound, MultipleResultsFound):
        raise AuthenticationError("Invalid credentials")
    return user


async def update_user_by_id(user_id: UUID, user_data: UserUpdate, db: DBSession):
    """Update an existing user."""
    update_data = user_data.model_dump(exclude_unset=True)
    try:
        user = await get_user_by_id_repo(user_id=user_id, db=db)
    except (NoResultFound, MultipleResultsFound):
        raise AuthenticationError("Invalid credentials")

    user.sqlmodel_update(update_data)

    return user


async def delete_user_by_id(user_id: UUID, db: DBSession):
    """Soft delete an existing user."""
    try:
        user = await delete_user_by_id_repo(user_id=user_id, db=db)
    except (NoResultFound, MultipleResultsFound):
        raise AuthenticationError("Invalid credentials")
    return user


async def change_password_by_id(
    user_id: UUID, password_data: PasswordChange, db: DBSession
):
    try:
        user = await get_user_by_id_repo(user_id=user_id, db=db)
    except (NoResultFound, MultipleResultsFound):
        raise AuthenticationError("Invalid credentials")

    if not await verify_password_async(
        password=password_data.old_password, password_hash=user.password_hash
    ):
        raise AuthenticationError("Your old password is wrong.")

    user.sqlmodel_update(
        {
            "password_hash": await hash_password_async(
                password=password_data.new_password
            ),
            "must_change_password": False,
        }
    )

    return user
