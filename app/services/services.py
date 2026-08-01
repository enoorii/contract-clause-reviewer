from app.core.security import hash_password
from app.db.database import DBSession
from app.repositories.user_repositories import (
    create_user_repo,
    get_user_by_username_repo,
)


async def create_user(username: str, password: str, db: DBSession):
    existing = await get_user_by_username_repo(username=username, db=db)
    if existing:
        raise ValueError("Username already exist")
    password_hash = hash_password(password=password)
    user = await create_user_repo(username=username, password_hash=password_hash, db=db)

    return user


async def get_user_by_username(username: str, db: DBSession):
    return await get_user_by_username_repo(username=username, db=db)
