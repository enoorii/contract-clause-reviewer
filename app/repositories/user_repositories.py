from sqlmodel import select

from app.db.database import DBSession
from app.models.models import Users


async def create_user_repo(username: str, password_hash: str, db: DBSession):
    user = Users(username=username, password_hash=password_hash)

    db.add(user)

    return user


async def get_user_by_username_repo(username: str, db: DBSession):
    stm = select(Users).where(Users.username == username)

    result = (await db.exec(stm)).first()

    return result
