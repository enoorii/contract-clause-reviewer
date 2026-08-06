from uuid import UUID

from sqlalchemy.orm.interfaces import ORMOption
from sqlmodel import func, select

from app.core.enums import Role
from app.db.database import DBSession
from app.models.models import Users
from app.schemas.users import UserFilters


async def create_user_repo(
    username: str,
    password_hash: str,
    created_by: UUID,
    db: DBSession,
    role: Role,
    must_change_password: bool = True,
    is_active: bool = True,
):
    user = Users(username=username, password_hash=password_hash)
    db.add(user)
    return user


async def get_user_by_username_repo(
    username: str, db: DBSession, options: list[ORMOption] | None = None
):
    stm = select(Users).where(Users.username == username)
    result = (await db.exec(stm)).one()
    return result


async def get_user_by_id_repo(
    user_id: UUID, db: DBSession, options: list[ORMOption] | None = None
):
    stm = select(Users).where(Users.id == user_id)

    if options is not None:
        stm = stm.options(*options)

    result = (await db.exec(stm)).one()
    return result


async def update_user_by_id_repo(user_id: UUID, user_data: dict, db: DBSession):
    """Update an existing user."""
    user = await get_user_by_id_repo(user_id=user_id, db=db)

    user.sqlmodel_update(user_data)

    db.add(user)
    await db.flush()
    await db.refresh(user)

    return user


async def get_users_repo(filters: UserFilters, db: DBSession):
    # Build base statement
    stm = select(Users)

    # Apply filtering
    stm = filters.apply_to_query(stm=stm)

    # Apply ordering
    stm = filters.apply_ordering(stm)

    # Apply pagination
    stm = stm.offset((filters.page - 1) * filters.size).limit(filters.size)

    result = await db.exec(stm)
    items = result.all()

    return items


async def get_users_total(filters: UserFilters, db: DBSession):
    # Build base statement
    stm = select(Users)

    # Apply filtering
    stm = filters.apply_to_query(stm=stm)

    # Apply pagination
    count_stm = select(func.count()).select_from(stm.subquery())
    total = await db.scalar(count_stm) or 0

    return total


async def delete_user_by_id_repo(user_id: UUID, db: DBSession):
    user = await get_user_by_id_repo(user_id=user_id, db=db)

    user.is_active = False

    db.add(user)
