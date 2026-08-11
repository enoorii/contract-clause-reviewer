from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm.interfaces import ORMOption
from sqlmodel import select

from app.core.security import hash_token
from app.db.database import DBSession
from app.models.models import RefreshToken


async def get_refresh_token_by_hash(
    token_hash: str,
    db: DBSession,
    options: Optional[list[ORMOption]] = None,
) -> Optional[RefreshToken]:
    stm = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    if options:
        stm = stm.options(*options)
    return (await db.exec(stm)).first()


async def get_refresh_token(
    raw_token: str,
    db: DBSession,
    options: Optional[list[ORMOption]] = None,
) -> RefreshToken:
    token_hash = hash_token(raw_token)
    token = await get_refresh_token_by_hash(token_hash, db, options)
    if token is None:
        raise ValueError("Invalid Token")
    return token


async def create_refresh_token_record(
    *,
    raw_token: str,
    user_id: UUID,
    expires_at: datetime,
    created_ip: Optional[str],
    user_agent: Optional[str],
    db: DBSession,
) -> RefreshToken:
    refresh_token = RefreshToken(
        token_hash=hash_token(raw_token),
        user_id=user_id,
        expires_at=expires_at,
        created_ip=created_ip,
        user_agent=user_agent,
        is_revoked=False,
        last_used_at=datetime.now(),
    )
    db.add(refresh_token)
    return refresh_token


async def revoke_refresh_token_by_hash(token_hash: str, db: DBSession) -> Optional[RefreshToken]:
    token = await get_refresh_token_by_hash(token_hash, db)
    if token:
        token.is_revoked = True
        token.last_used_at = datetime.now()
        db.add(token)
    return token


async def update_refresh_token_usage_by_hash(token_hash: str, db: DBSession) -> Optional[RefreshToken]:
    token = await get_refresh_token_by_hash(token_hash, db)
    if token:
        token.last_used_at = datetime.now()
        db.add(token)
    return token