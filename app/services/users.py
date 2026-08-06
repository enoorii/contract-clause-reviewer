from uuid import UUID

from app.core.enums import Role
from app.core.exceptions import AuthenticationError
from app.core.security import (
    hash_password_async,
    verify_password_async,
)
from app.db.database import DBSession
from app.repositories.user_repositories import (
    create_user_repo,
    delete_user_by_id_repo,
    get_user_by_id_repo,
    get_user_by_username_repo,
    get_users_repo,
    get_users_total,
    update_user_by_id_repo,
)
from app.schemas.users import PasswordChange, UserFilters, UserUpdate


async def get_user_by_username(username: str, db: DBSession):
    return await get_user_by_username_repo(username=username, db=db)


async def create_user(
    username: str,
    password: str,
    created_by: UUID,
    db: DBSession,
    role: Role,
    must_change_password: bool = True,
    is_active: bool = True,
):
    existing = await get_user_by_username_repo(username=username, db=db)
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

    total = await get_users_total(filters=filters, db=db)

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

    users = await get_users_repo(filters=filters, db=db)

    return {
        "items": users,
        "total": total,
        "page": filters.page,
        "size": filters.size,
        "pages": pages,
    }


async def get_user_by_id(user_id: UUID, db: DBSession):
    """Get a single user by ID."""
    user = await get_user_by_id_repo(user_id=user_id, db=db)

    return user


async def update_user_by_id(user_id: UUID, user_data: UserUpdate, db: DBSession):
    """Update an existing user."""
    update_data = user_data.model_dump(exclude_unset=True)
    user = await update_user_by_id_repo(user_id=user_id, user_data=update_data, db=db)
    return user


async def delete_user_by_id(user_id: UUID, db: DBSession):
    """Soft delete an existing user."""
    user = await delete_user_by_id_repo(user_id=user_id, db=db)
    return user


async def change_password_by_id(
    user_id: UUID, password_data: PasswordChange, db: DBSession
):
    user = await get_user_by_id_repo(user_id=user_id, db=db)

    if not await verify_password_async(
        password=password_data.old_password, password_hash=user.password_hash
    ):
        raise AuthenticationError("Your old password is wrong.")

    user = await update_user_by_id_repo(
        user_id=user_id,
        user_data={
            "password_hash": await hash_password_async(
                password=password_data.new_password
            ),
            "must_change_password": False,
        },
        db=db,
    )

    return user
