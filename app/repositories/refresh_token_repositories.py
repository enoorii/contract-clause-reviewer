from datetime import datetime

from sqlalchemy.orm.interfaces import ORMOption
from sqlmodel import select

from app.core.security import hash_token
from app.db.database import DBSession
from app.models.models import RefreshToken


async def get_refresh_token(
    raw_token: str, db: DBSession, options: list[ORMOption] | None = None
):
    stm = select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token))

    if options is not None:
        stm = stm.options(*options)

    refresh_token = (await db.exec(stm)).first()

    if refresh_token is None:
        raise ValueError("Invalid Token")

    return refresh_token


async def create_refresh_token(
    *,
    raw_token: str,
    user_id,
    expires_at: datetime,
    created_ip: str | None,
    user_agent: str | None,
    db: DBSession,
) -> RefreshToken:
    refresh_token = RefreshToken(
        token_hash=hash_token(raw_token),
        user_id=user_id,
        expires_at=expires_at,
        created_ip=created_ip,
        user_agent=user_agent,
    )

    db.add(refresh_token)

    return refresh_token
