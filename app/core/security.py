import hashlib
import secrets
from asyncio import to_thread
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol, runtime_checkable
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

# ---------- Password Utilities ----------
_password_hash = PasswordHash.recommended()


async def hash_password_async(password: str) -> str:
    """Hash password in thread pool."""
    return await to_thread(_password_hash.hash, password)


async def verify_password_async(password: str, password_hash: str) -> bool:
    """Verify password in thread pool."""
    return await to_thread(_password_hash.verify, password, password_hash)


def hash_token(token: str) -> str:
    """SHA256 hash of token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------- Data Transfer Objects ----------
@dataclass(frozen=True)
class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass
class RefreshTokenData:
    """Data for a refresh token (no DB model)."""

    token_hash: str
    user_id: str
    expires_at: datetime
    created_ip: Optional[str] = None
    user_agent: Optional[str] = None
    is_revoked: bool = False
    last_used_at: Optional[datetime] = None


@dataclass
class VerifiedRefreshToken:
    """Result of a successful refresh token validation."""

    user_id: str
    token_hash: str
    expires_at: datetime
    is_revoked: bool
    last_used_at: Optional[datetime] = None
    created_ip: Optional[str] = None
    user_agent: Optional[str] = None


# ---------- Token Store Protocol ----------
@runtime_checkable
class TokenStore(Protocol):
    """Interface for token storage operations."""

    async def get_refresh_token_by_hash(
        self, token_hash: str
    ) -> Optional[RefreshTokenData]: ...
    async def create_refresh_token(self, token_data: RefreshTokenData) -> None: ...
    async def revoke_refresh_token(self, token_hash: str) -> None: ...
    async def update_refresh_token_usage(self, token_hash: str) -> None: ...
    async def get_user_by_id(self, user_id: str) -> Optional[dict]: ...


# ---------- Token Creation ----------
async def create_access_token(
    username: str, secret_key: str, expiration_minutes: int
) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
    jti = str(uuid4())
    return jwt.encode(
        {"sub": username, "type": TokenType.ACCESS, "exp": exp, "jti": jti},
        secret_key,
        algorithm="HS256",
    )


async def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


# ---------- Token Verification ----------
async def verify_access_token(token: str, secret_key: str):
    """
    Validate JWT access token.
    Returns (jti, username) or raises.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        if payload.get("type") != TokenType.ACCESS:
            raise jwt.InvalidTokenError("Not an access token")
        jti = payload.get("jti")
        if not jti:
            raise jwt.InvalidTokenError("Missing JTI")
        username = payload.get("sub")
        if not username:
            raise jwt.InvalidTokenError("Missing subject claim")
        return jti, str(username)
    except (jwt.DecodeError, ValueError) as e:
        raise jwt.InvalidTokenError(f"Invalid access token: {e}") from e
    except jwt.ExpiredSignatureError as e:
        raise jwt.ExpiredSignatureError("Access token expired") from e
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f"Invalid access token: {e}") from e


async def verify_refresh_token(
    raw_token: str, token_store: TokenStore
) -> VerifiedRefreshToken:
    """
    Validate an opaque refresh token using the token store.
    Returns verified token data.
    """
    token_hash = hash_token(raw_token)
    token_data = await token_store.get_refresh_token_by_hash(token_hash)
    if token_data is None:
        raise ValueError("Refresh token not found")
    if token_data.is_revoked:
        raise ValueError("Refresh token has been revoked")
    if token_data.expires_at < datetime.now(timezone.utc):
        raise ValueError("Refresh token expired")
    return VerifiedRefreshToken(
        user_id=token_data.user_id,
        token_hash=token_data.token_hash,
        expires_at=token_data.expires_at,
        is_revoked=token_data.is_revoked,
        last_used_at=token_data.last_used_at,
        created_ip=token_data.created_ip,
        user_agent=token_data.user_agent,
    )


# ---------- Token Rotation & Creation (using TokenStore) ----------
async def rotate_refresh_token(
    old_raw_token: str,
    token_store: TokenStore,
    secret_key: str,
    access_expiration_minutes: int,
    refresh_expiration_days: int,
    new_ip: Optional[str] = None,
    new_user_agent: Optional[str] = None,
) -> dict:
    """
    Validate old token, revoke it, create new tokens with same expiry.
    Returns dict with access_token, refresh_token, and token_data for new refresh token.
    """
    verified = await verify_refresh_token(old_raw_token, token_store)
    user_data = await token_store.get_user_by_id(verified.user_id)
    if not user_data:
        raise ValueError("User not found")

    # Revoke old token
    await token_store.revoke_refresh_token(verified.token_hash)

    # Create new access token
    new_access = await create_access_token(
        username=user_data["username"],
        secret_key=secret_key,
        expiration_minutes=access_expiration_minutes,
    )

    # Create new refresh token
    new_raw_refresh = await create_refresh_token()
    new_token_hash = hash_token(new_raw_refresh)
    new_token_data = RefreshTokenData(
        token_hash=new_token_hash,
        user_id=verified.user_id,
        expires_at=verified.expires_at,  # preserve absolute expiry
        created_ip=new_ip or verified.created_ip,
        user_agent=new_user_agent or verified.user_agent,
        is_revoked=False,
        last_used_at=datetime.now(timezone.utc),
    )
    await token_store.create_refresh_token(new_token_data)

    return {
        "access_token": new_access,
        "refresh_token": new_raw_refresh,
        "token_type": "bearer",
    }


async def create_tokens_for_user(
    user_id: str,
    username: str,
    token_store: TokenStore,
    secret_key: str,
    access_expiration_minutes: int,
    refresh_expiration_days: int,
    created_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:
    """
    Generate new access and refresh tokens for a user.
    Stores the refresh token via token_store.
    """
    access_token = await create_access_token(
        username=username,
        secret_key=secret_key,
        expiration_minutes=access_expiration_minutes,
    )
    raw_refresh = await create_refresh_token()
    token_hash = hash_token(raw_refresh)
    expires_at = datetime.now(timezone.utc) + timedelta(days=refresh_expiration_days)
    token_data = RefreshTokenData(
        token_hash=token_hash,
        user_id=user_id,
        expires_at=expires_at,
        created_ip=created_ip,
        user_agent=user_agent,
        is_revoked=False,
        last_used_at=datetime.now(timezone.utc),
    )
    await token_store.create_refresh_token(token_data)
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
    }
