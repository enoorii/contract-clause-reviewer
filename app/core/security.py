import hashlib
import secrets
from asyncio import to_thread
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pwdlib import PasswordHash
from sqlmodel import select

from app.core.config import Settings
from app.db.database import DBSession
from app.models.models import RefreshToken, Users


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


password_hash = PasswordHash.recommended()

hash_password = PasswordHash.recommended().hash


def verify_password(password_hash: str, password: str):
    return PasswordHash.recommended().verify(hash=password_hash, password=password)


# Async public API
async def hash_password_async(password: str) -> str:
    """Hash password in thread pool to avoid blocking event loop"""
    return await to_thread(hash_password, password)


async def verify_password_async(password_hash: str, password: str) -> bool:
    """Verify password in thread pool to avoid blocking event loop"""
    return await to_thread(verify_password, password_hash, password)


@dataclass
class TokenType(str):
    ACCESS = "access"
    REFRESH = "refresh"


async def create_access_token(user: Users) -> str:
    exp = datetime.now(timezone.utc) + timedelta(
        minutes=Settings.ACCESS_TOKEN_EXPIRATION_MINUTES
    )
    jti = str(uuid4())
    token = jwt.encode(
        {"sub": str(user.username), "type": TokenType.ACCESS, "exp": exp, "jti": jti},
        Settings.SECRET_KEY,
        algorithm="HS256",
    )
    return token


async def create_refresh_token() -> str:
    """Create an opaque refresh token (id + random string)."""
    return secrets.token_urlsafe(16)


async def store_refresh_token(
    user: Users,
    raw_token: str,
    db: DBSession,
) -> RefreshToken:
    """Hash and store a refresh token in the database. Returns the stored token object."""
    token_hash = await to_thread(password_hash.hash, raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=Settings.REFRESH_TOKEN_EXPIRATION_DAYS
    )
    refresh_token = RefreshToken(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=expires_at,
        is_revoked=False,
        last_used_at=datetime.now(timezone.utc),
    )
    db.add(refresh_token)

    return refresh_token


# ---------- Verification ----------
async def verify_access_token(token: str, db: DBSession):
    """Validate JWT access token and return the associated User."""
    try:
        payload = jwt.decode(token, Settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != TokenType.ACCESS:
            raise jwt.InvalidTokenError("Not an access token")
        jti = payload.get("jti")
        if not jti:
            raise jwt.InvalidTokenError("Missing JTI")

        username_str = payload.get("sub")
        if not username_str:
            raise jwt.InvalidTokenError("Missing subject claim")

        username = str(username_str)

    except (jwt.DecodeError, ValueError) as e:
        raise jwt.InvalidTokenError(f"Invalid access token: {e}") from e
    except jwt.ExpiredSignatureError as e:
        raise jwt.ExpiredSignatureError("Access token expired") from e
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f"Invalid access token: {e}") from e

    return jti, username


@dataclass
class VerifiedRefreshToken:
    """Result of a successful refresh token validation."""

    user: Users
    token_record: RefreshToken


async def verify_refresh_token(raw_token: str, db: DBSession) -> VerifiedRefreshToken:
    """
    Validate an opaque refresh token without modifying it.
    Returns both the user and the token record (needed for rotation).
    """
    token_hash = await to_thread(password_hash.hash, raw_token)

    result = await db.exec(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    try:
        stored_token = result.one()
    except Exception as e:
        raise ValueError("Refresh token not found") from e

    if stored_token.is_revoked:
        raise ValueError("Refresh token has been revoked")
    if stored_token.expires_at < datetime.now(timezone.utc):
        raise ValueError("Refresh token expired")

    return VerifiedRefreshToken(user=stored_token.user, token_record=stored_token)


# ---------- Rotation ----------
async def rotate_refresh_token(old_raw_token: str, db: DBSession) -> dict:
    """
    Revoke the old refresh token, create a new one that inherits the SAME absolute expiry,
    and return new access + refresh tokens.
    """
    # Validate the old token and get its record
    verified = await verify_refresh_token(old_raw_token, db)
    old_token = verified.token_record
    user = verified.user

    # Revoke the old token
    old_token.is_revoked = True
    old_token.last_used_at = datetime.now(timezone.utc)
    db.add(old_token)

    # Create new tokens
    new_access = await create_access_token(user)
    new_raw_refresh = await create_refresh_token()

    # Hash the new token and store it with the SAME absolute expiry as the old one
    new_token_hash = await to_thread(password_hash.hash, new_raw_refresh)

    new_refresh_token = RefreshToken(
        token_hash=new_token_hash,
        user_id=user.id,
        created_ip=old_token.created_ip,
        expires_at=old_token.expires_at,  # ← crucial: preserve original expiry
        is_revoked=False,
        last_used_at=datetime.now(timezone.utc),
    )
    db.add(new_refresh_token)

    return {
        "access_token": new_access,
        "refresh_token": new_raw_refresh,
        "token_type": "bearer",
    }


async def create_tokens_for_user(user: Users, db: DBSession) -> dict:
    """Generate new access and refresh tokens for a user (login)."""
    access_token = await create_access_token(user)
    raw_refresh = await create_refresh_token()
    await store_refresh_token(user=user, raw_token=raw_refresh, db=db)
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
    }
