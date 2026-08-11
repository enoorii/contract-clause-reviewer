import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest
from freezegun import freeze_time
from pwdlib.exceptions import UnknownHashError

from app.core.security import (
    RefreshTokenData,
    TokenType,
    VerifiedRefreshToken,
    create_access_token,
    create_refresh_token,
    create_tokens_for_user,
    hash_password_async,
    hash_token,
    rotate_refresh_token,
    verify_access_token,
    verify_password_async,
    verify_refresh_token,
)

# ---------------------------------------------------------------------------
# Fixtures only used in this file
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_token_store():
    """Return an AsyncMock that satisfies the TokenStore protocol."""
    return AsyncMock()


@pytest.fixture
def fixed_now():
    """Return a fixed UTC datetime for tests that need frozen time."""
    return datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def valid_refresh_token_string():
    """Return a valid raw refresh token string."""
    return "valid-refresh-token-123"


@pytest.fixture
def valid_refresh_token_data(fixed_now, valid_refresh_token_string):
    """Sample RefreshTokenData that passes validation."""
    return RefreshTokenData(
        token_hash=hash_token(valid_refresh_token_string),  # Use actual hash
        user_id="user-1",
        expires_at=fixed_now + timedelta(days=7),
        created_ip="127.0.0.1",
        user_agent="pytest",
        is_revoked=False,
        last_used_at=fixed_now,
    )


@pytest.fixture
def expired_refresh_token_data(fixed_now, valid_refresh_token_string):
    """Sample RefreshTokenData that's expired."""
    return RefreshTokenData(
        token_hash=hash_token(valid_refresh_token_string),
        user_id="user-1",
        expires_at=fixed_now - timedelta(days=1),  # Expired yesterday
        created_ip="127.0.0.1",
        user_agent="pytest",
        is_revoked=False,
        last_used_at=fixed_now,
    )


# ---------------------------------------------------------------------------
# Password hashing & verification
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    @pytest.mark.asyncio
    async def test_hash_password_returns_different_string(self):
        password = "mysecret"
        hashed = await hash_password_async(password)
        assert isinstance(hashed, str)
        assert hashed != password

    @pytest.mark.asyncio
    async def test_verify_password_with_correct_password(self):
        password = "mysecret"
        hashed = await hash_password_async(password)
        assert await verify_password_async(password, hashed) is True

    @pytest.mark.asyncio
    async def test_verify_password_with_wrong_password(self):
        password = "mysecret"
        hashed = await hash_password_async(password)
        assert await verify_password_async("wrongsecret", hashed) is False

    @pytest.mark.asyncio
    async def test_verify_password_with_invalid_hash(self):
        # Using a completely invalid hash should return False (or raise? pwdlib returns False)
        with pytest.raises(UnknownHashError):
            await verify_password_async("anything", "not-a-valid-hash")


class TestHashToken:
    def test_hash_token_produces_sha256_hex(self):
        token = "raw-token"
        result = hash_token(token)
        expected = hashlib.sha256(token.encode()).hexdigest()
        assert result == expected
        assert len(result) == 64

    def test_hash_token_is_deterministic(self):
        token = "raw-token"
        assert hash_token(token) == hash_token(token)


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    @pytest.mark.asyncio
    async def test_contains_required_claims(self, secret_key):
        username = "john"
        token = await create_access_token(username, secret_key, expiration_minutes=30)
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert payload["sub"] == username
        assert payload["type"] == TokenType.ACCESS
        assert "jti" in payload
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_jti_is_uuid_format(self, secret_key):
        token = await create_access_token("user", secret_key, 30)
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        jti = payload["jti"]
        # UUID4 is 36 chars with hyphens
        assert len(jti) == 36
        assert jti.count("-") == 4

    @freeze_time("2026-08-11 12:00:00")
    @pytest.mark.asyncio
    async def test_expiration_is_set_correctly(self, secret_key):
        token = await create_access_token("user", secret_key, expiration_minutes=15)
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        exp = payload["exp"]
        expected = datetime(2026, 8, 11, 12, 15, 0, tzinfo=timezone.utc).timestamp()
        assert exp == pytest.approx(expected, 1)  # allow 1 second tolerance

    @pytest.mark.asyncio
    async def test_different_tokens_for_same_user(self, secret_key):
        token1 = await create_access_token("user", secret_key, 30)
        token2 = await create_access_token("user", secret_key, 30)
        assert token1 != token2  # because jti differs


class TestCreateRefreshToken:
    @pytest.mark.asyncio
    async def test_returns_urlsafe_string(self):
        token = await create_refresh_token()
        assert isinstance(token, str)
        # token_urlsafe(32) returns 43 characters (no padding)
        assert len(token) == 43

    @pytest.mark.asyncio
    async def test_tokens_are_unique(self):
        token1 = await create_refresh_token()
        token2 = await create_refresh_token()
        assert token1 != token2


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------


class TestVerifyAccessToken:
    @pytest.mark.asyncio
    async def test_valid_token_returns_jti_and_username(self, secret_key):
        token = await create_access_token("alice", secret_key, 30)
        jti, username = await verify_access_token(token, secret_key)
        assert username == "alice"
        assert isinstance(jti, str)

    @pytest.mark.asyncio
    async def test_invalid_signature_raises_invalid_token(self, secret_key):
        token = await create_access_token("alice", secret_key, 30)
        # Tamper with the token
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with pytest.raises(jwt.InvalidTokenError):
            await verify_access_token(tampered, secret_key)

    @pytest.mark.asyncio
    async def test_expired_token_raises_expired_signature(self, secret_key):
        with freeze_time("2026-01-01"):
            token = await create_access_token("alice", secret_key, 1)
        with freeze_time("2026-01-01 00:02:00"):
            with pytest.raises(jwt.ExpiredSignatureError):
                await verify_access_token(token, secret_key)

    @pytest.mark.asyncio
    async def test_token_with_wrong_type_raises_invalid_token(self, secret_key):
        # Create a token with type "refresh" manually
        payload = {
            "sub": "alice",
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "jti": "some-jti",
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        with pytest.raises(jwt.InvalidTokenError, match="Not an access token"):
            await verify_access_token(token, secret_key)

    @pytest.mark.asyncio
    async def test_missing_jti_raises_invalid_token(self, secret_key):
        payload = {
            "sub": "alice",
            "type": TokenType.ACCESS,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        with pytest.raises(jwt.InvalidTokenError, match="Missing JTI"):
            await verify_access_token(token, secret_key)

    @pytest.mark.asyncio
    async def test_missing_sub_raises_invalid_token(self, secret_key):
        payload = {
            "type": TokenType.ACCESS,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "jti": "some-jti",
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        with pytest.raises(jwt.InvalidTokenError, match="Missing subject claim"):
            await verify_access_token(token, secret_key)

    @pytest.mark.asyncio
    async def test_malformed_token_raises_invalid_token(self, secret_key):
        with pytest.raises(jwt.InvalidTokenError):
            await verify_access_token("not.a.token", secret_key)


class TestVerifyRefreshToken:
    @pytest.mark.asyncio
    async def test_valid_token_returns_verified_data(
        self, mock_token_store, valid_refresh_token_data, valid_refresh_token_string
    ):
        raw_token = valid_refresh_token_string
        token_hash = hash_token(raw_token)
        mock_token_store.get_refresh_token_by_hash.return_value = (
            valid_refresh_token_data
        )

        result = await verify_refresh_token(raw_token, mock_token_store)

        assert isinstance(result, VerifiedRefreshToken)
        assert result.user_id == valid_refresh_token_data.user_id
        assert result.token_hash == valid_refresh_token_data.token_hash
        mock_token_store.get_refresh_token_by_hash.assert_awaited_once_with(token_hash)

    @pytest.mark.asyncio
    async def test_nonexistent_token_raises_value_error(self, mock_token_store):
        mock_token_store.get_refresh_token_by_hash.return_value = None
        with pytest.raises(ValueError, match="Refresh token not found"):
            await verify_refresh_token("nonexistent", mock_token_store)

    @pytest.mark.asyncio
    async def test_revoked_token_raises_value_error(
        self, mock_token_store, valid_refresh_token_data, valid_refresh_token_string
    ):
        valid_refresh_token_data.is_revoked = True
        mock_token_store.get_refresh_token_by_hash.return_value = (
            valid_refresh_token_data
        )
        with pytest.raises(ValueError, match="Refresh token has been revoked"):
            await verify_refresh_token(valid_refresh_token_string, mock_token_store)

    @pytest.mark.asyncio
    async def test_expired_token_raises_value_error(
        self, mock_token_store, expired_refresh_token_data, valid_refresh_token_string
    ):
        """Test that an expired token raises ValueError."""
        mock_token_store.get_refresh_token_by_hash.return_value = (
            expired_refresh_token_data
        )

        with pytest.raises(ValueError, match="Refresh token expired"):
            await verify_refresh_token(valid_refresh_token_string, mock_token_store)

    @freeze_time("2026-09-18 00:00:00")  # after expiry
    @pytest.mark.asyncio
    async def test_expired_token_raises_value_error_with_freeze(
        self, mock_token_store, valid_refresh_token_data, valid_refresh_token_string
    ):
        """Test that an tokens are expired correctly."""
        mock_token_store.get_refresh_token_by_hash.return_value = (
            valid_refresh_token_data
        )
        with pytest.raises(ValueError, match="Refresh token expired"):
            await verify_refresh_token(valid_refresh_token_string, mock_token_store)


# ---------------------------------------------------------------------------
# Token rotation
# ---------------------------------------------------------------------------


class TestRotateRefreshToken:
    @pytest.mark.asyncio
    async def test_successful_rotation_returns_new_tokens(
        self,
        mock_token_store,
        secret_key,
        valid_refresh_token_data,
        valid_refresh_token_string,
    ):
        old_raw = valid_refresh_token_string
        old_hash = hash_token(old_raw)
        mock_token_store.get_refresh_token_by_hash.return_value = (
            valid_refresh_token_data
        )
        mock_token_store.get_user_by_id.return_value = {
            "id": "user-1",
            "username": "alice",
        }

        result = await rotate_refresh_token(
            old_raw_token=old_raw,
            token_store=mock_token_store,
            secret_key=secret_key,
            access_expiration_minutes=15,
        )

        # Check result structure
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"

        # Old token revoked
        mock_token_store.revoke_refresh_token.assert_awaited_once_with(old_hash)

        # New refresh token stored - check it was called
        assert mock_token_store.create_refresh_token.call_count == 1
        args, _ = mock_token_store.create_refresh_token.call_args
        new_token_data = args[0]
        assert isinstance(new_token_data, RefreshTokenData)
        assert new_token_data.token_hash == hash_token(result["refresh_token"])
        assert new_token_data.user_id == valid_refresh_token_data.user_id
        assert new_token_data.is_revoked is False
        # Preserved expiry
        assert new_token_data.expires_at == valid_refresh_token_data.expires_at

    @pytest.mark.asyncio
    async def test_rotation_preserves_ip_and_user_agent_if_not_provided(
        self,
        mock_token_store,
        secret_key,
        valid_refresh_token_data,
        valid_refresh_token_string,
    ):
        valid_refresh_token_data.created_ip = "10.0.0.1"
        valid_refresh_token_data.user_agent = "Firefox"
        mock_token_store.get_refresh_token_by_hash.return_value = (
            valid_refresh_token_data
        )
        mock_token_store.get_user_by_id.return_value = {"username": "bob"}

        await rotate_refresh_token(
            old_raw_token=valid_refresh_token_string,
            token_store=mock_token_store,
            secret_key=secret_key,
            access_expiration_minutes=15,
        )
        stored = mock_token_store.create_refresh_token.call_args[0][0]
        assert stored.created_ip == "10.0.0.1"
        assert stored.user_agent == "Firefox"

    @pytest.mark.asyncio
    async def test_rotation_overrides_ip_and_user_agent_when_provided(
        self,
        mock_token_store,
        secret_key,
        valid_refresh_token_data,
        valid_refresh_token_string,
    ):
        mock_token_store.get_refresh_token_by_hash.return_value = (
            valid_refresh_token_data
        )
        mock_token_store.get_user_by_id.return_value = {"username": "bob"}

        await rotate_refresh_token(
            old_raw_token=valid_refresh_token_string,
            token_store=mock_token_store,
            secret_key=secret_key,
            access_expiration_minutes=15,
            new_ip="192.168.1.1",
            new_user_agent="Chrome",
        )
        stored = mock_token_store.create_refresh_token.call_args[0][0]
        assert stored.created_ip == "192.168.1.1"
        assert stored.user_agent == "Chrome"

    @pytest.mark.asyncio
    async def test_rotation_user_not_found_raises(
        self,
        mock_token_store,
        secret_key,
        valid_refresh_token_data,
        valid_refresh_token_string,
    ):
        mock_token_store.get_refresh_token_by_hash.return_value = (
            valid_refresh_token_data
        )
        mock_token_store.get_user_by_id.return_value = None  # user gone

        with pytest.raises(ValueError, match="User not found"):
            await rotate_refresh_token(
                old_raw_token=valid_refresh_token_string,
                token_store=mock_token_store,
                secret_key=secret_key,
                access_expiration_minutes=15,
            )


# ---------------------------------------------------------------------------
# create_tokens_for_user
# ---------------------------------------------------------------------------


class TestCreateTokensForUser:
    @pytest.mark.asyncio
    async def test_returns_tokens_and_stores_refresh(
        self, mock_token_store, secret_key
    ):
        user_id = "user-123"
        username = "charlie"

        result = await create_tokens_for_user(
            user_id=user_id,
            username=username,
            token_store=mock_token_store,
            secret_key=secret_key,
            access_expiration_minutes=30,
            refresh_expiration_days=14,
        )

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"

        # Verify the store was called
        mock_token_store.create_refresh_token.assert_awaited_once()
        stored_data = mock_token_store.create_refresh_token.call_args[0][0]
        assert stored_data.user_id == user_id
        assert stored_data.token_hash == hash_token(result["refresh_token"])
        assert stored_data.is_revoked is False
        # Check expiration roughly 14 days in the future
        now = datetime.now(timezone.utc)
        assert stored_data.expires_at > now + timedelta(days=13)
        assert stored_data.expires_at < now + timedelta(days=15)

    @pytest.mark.asyncio
    async def test_sets_optional_metadata(self, mock_token_store, secret_key):
        await create_tokens_for_user(
            user_id="u1",
            username="dave",
            token_store=mock_token_store,
            secret_key=secret_key,
            access_expiration_minutes=30,
            refresh_expiration_days=7,
            created_ip="192.168.0.1",
            user_agent="TestRunner",
        )
        stored = mock_token_store.create_refresh_token.call_args[0][0]
        assert stored.created_ip == "192.168.0.1"
        assert stored.user_agent == "TestRunner"
