# tests/unit/services/test_auth.py

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import jwt
import pytest
from freezegun import freeze_time
from pwdlib.exceptions import UnknownHashError

from app.core.exceptions import AuthenticationError
from app.core.security import (
    RefreshTokenData,
    TokenStore,
    hash_token,
)
from app.models.models import RefreshToken, User
from app.schemas.base import ClientInfo
from app.services.auth import (
    DatabaseTokenStore,
    authenticate_user,
    authenticate_user_by_token,
    expire_user_sessions,
    logout_user,
    refresh_access_token,
)

# ---------- Fixtures ----------


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def client_info():
    """Create client info fixture."""
    return ClientInfo(created_ip="127.0.0.1", user_agent="test-agent/1.0")


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = UUID("12345678-1234-5678-1234-567812345678")
    user.username = "testuser"
    user.password_hash = "$2b$12$hashedpassword1234567890"
    user.role = "user"
    user.is_active = True
    user.must_change_password = False
    user.refresh_tokens = []
    return user


@pytest.fixture
def mock_refresh_token(mock_user):
    """Create a mock refresh token."""
    token = MagicMock(spec=RefreshToken)
    token.token_hash = "abc123def456"
    token.user_id = mock_user.id
    token.user = mock_user
    token.expires_at = datetime.now(UTC) + timedelta(days=7)
    token.created_ip = "127.0.0.1"
    token.user_agent = "test-agent/1.0"
    token.is_revoked = False
    token.last_used_at = datetime.now(UTC)
    return token


@pytest.fixture
def mock_token_store():
    """Create a mock token store."""
    store = AsyncMock(spec=TokenStore)
    return store


@pytest.fixture
def access_token(secret_key):
    """Create a valid access token."""
    with freeze_time("2024-01-01 12:00:00"):
        token = jwt.encode(
            {
                "sub": "testuser",
                "type": "access",
                "exp": datetime.now(UTC) + timedelta(minutes=30),
                "jti": "test-jti-123",
            },
            secret_key,
            algorithm="HS256",
        )
    return token


@pytest.fixture
def refresh_token():
    """Create a raw refresh token."""
    return "raw_refresh_token_123"


@pytest.fixture
def refresh_token_hash(refresh_token):
    """Create hash of refresh token."""
    return hash_token(refresh_token)


# ---------- Test Classes ----------


class TestDatabaseTokenStore:
    """Tests for DatabaseTokenStore class."""

    @pytest.mark.asyncio
    async def test_get_refresh_token_by_hash_found(self, mock_db, mock_refresh_token):
        """Test getting refresh token by hash when found."""
        with patch(
            "app.services.auth.get_refresh_token_by_hash",
            AsyncMock(return_value=mock_refresh_token),
        ):
            store = DatabaseTokenStore(mock_db)
            result = await store.get_refresh_token_by_hash("abc123")

            assert result is not None
            assert result.token_hash == mock_refresh_token.token_hash
            assert result.user_id == str(mock_refresh_token.user_id)
            assert result.expires_at == mock_refresh_token.expires_at
            assert result.is_revoked == mock_refresh_token.is_revoked

    @pytest.mark.asyncio
    async def test_get_refresh_token_by_hash_not_found(self, mock_db):
        """Test getting refresh token by hash when not found."""
        with patch(
            "app.services.auth.get_refresh_token_by_hash", AsyncMock(return_value=None)
        ):
            store = DatabaseTokenStore(mock_db)
            result = await store.get_refresh_token_by_hash("abc123")
            assert result is None

    @pytest.mark.asyncio
    async def test_create_refresh_token(self, mock_db):
        """Test creating a refresh token."""
        store = DatabaseTokenStore(mock_db)
        token_data = RefreshTokenData(
            token_hash="abc123",
            user_id="12345678-1234-5678-1234-567812345678",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            created_ip="127.0.0.1",
            user_agent="test-agent",
            is_revoked=False,
            last_used_at=datetime.now(UTC),
        )

        await store.create_refresh_token(token_data)
        mock_db.add.assert_called_once()
        added_token = mock_db.add.call_args[0][0]
        assert added_token.token_hash == token_data.token_hash
        assert str(added_token.user_id) == token_data.user_id

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self, mock_db):
        """Test revoking a refresh token."""
        with patch(
            "app.services.auth.revoke_refresh_token_by_hash", AsyncMock()
        ) as mock_revoke:
            store = DatabaseTokenStore(mock_db)
            await store.revoke_refresh_token("abc123")
            mock_revoke.assert_called_once_with(token_hash="abc123", db=mock_db)

    @pytest.mark.asyncio
    async def test_update_refresh_token_usage(self, mock_db):
        """Test updating refresh token usage."""
        with patch(
            "app.services.auth.update_refresh_token_usage_by_hash", AsyncMock()
        ) as mock_update:
            store = DatabaseTokenStore(mock_db)
            await store.update_refresh_token_usage("abc123")
            mock_update.assert_called_once_with(token_hash="abc123", db=mock_db)

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self, mock_db, mock_user):
        """Test getting user by ID when found."""
        with patch(
            "app.services.auth.get_user_by_id_repo", AsyncMock(return_value=mock_user)
        ):
            store = DatabaseTokenStore(mock_db)
            result = await store.get_user_by_id(str(mock_user.id))

            assert result is not None
            assert result["id"] == str(mock_user.id)
            assert result["username"] == mock_user.username
            assert result["role"] == mock_user.role
            assert result["is_active"] == mock_user.is_active

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, mock_db):
        """Test getting user by ID when not found."""
        with patch(
            "app.services.auth.get_user_by_id_repo", AsyncMock(return_value=None)
        ):
            store = DatabaseTokenStore(mock_db)
            result = await store.get_user_by_id("12345678-1234-5678-1234-567812345678")
            assert result is None


class TestAuthenticateUser:
    """Tests for authenticate_user function."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, mock_db, mock_user, client_info):
        """Test successful user authentication."""
        with patch(
            "app.services.auth.get_user_by_username_repo",
            AsyncMock(return_value=mock_user),
        ):
            with patch(
                "app.services.auth.verify_password_async", AsyncMock(return_value=True)
            ):
                with patch(
                    "app.services.auth.create_tokens_for_user",
                    AsyncMock(
                        return_value={
                            "access_token": "access123",
                            "refresh_token": "refresh123",
                            "token_type": "bearer",
                        }
                    ),
                ):
                    result = await authenticate_user(
                        username="testuser",
                        password="correctpassword",
                        db=mock_db,
                        client_info=client_info,
                    )

                    assert result["access_token"] == "access123"
                    assert result["refresh_token"] == "refresh123"
                    assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_authenticate_user_user_not_found(self, mock_db, client_info):
        """Test authentication with non-existent user."""
        with patch(
            "app.services.auth.get_user_by_username_repo", AsyncMock(return_value=None)
        ):
            with pytest.raises(AuthenticationError, match="Invalid credentials"):
                await authenticate_user(
                    username="nonexistent",
                    password="password",
                    db=mock_db,
                    client_info=client_info,
                )

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(
        self, mock_db, mock_user, client_info
    ):
        """Test authentication with invalid password."""
        with patch(
            "app.services.auth.get_user_by_username_repo",
            AsyncMock(return_value=mock_user),
        ):
            with patch(
                "app.services.auth.verify_password_async", AsyncMock(return_value=False)
            ):
                with pytest.raises(AuthenticationError, match="Invalid credentials"):
                    await authenticate_user(
                        username="testuser",
                        password="wrongpassword",
                        db=mock_db,
                        client_info=client_info,
                    )

    @pytest.mark.asyncio
    async def test_authenticate_user_unknown_hash_error(
        self, mock_db, mock_user, client_info
    ):
        """Test authentication when password hash is unknown format."""
        with patch(
            "app.services.auth.get_user_by_username_repo",
            AsyncMock(return_value=mock_user),
        ):
            # Create the exception with the required hash argument
            with patch(
                "app.services.auth.verify_password_async",
                AsyncMock(side_effect=UnknownHashError("invalid_hash_format")),
            ):
                with patch("app.services.auth.logger") as mock_logger:
                    with pytest.raises(
                        AuthenticationError, match="Invalid credentials"
                    ):
                        await authenticate_user(
                            username="testuser",
                            password="password",
                            db=mock_db,
                            client_info=client_info,
                        )
                    mock_logger.error.assert_called_once_with(
                        "Unknown password hash for user: %s", "testuser"
                    )


class TestAuthenticateUserByToken:
    """Tests for authenticate_user_by_token function."""

    @pytest.mark.asyncio
    async def test_authenticate_user_by_token_success(
        self, mock_db, mock_user, access_token, secret_key
    ):
        """Test successful authentication via access token."""
        with patch(
            "app.services.auth.verify_access_token",
            AsyncMock(return_value=("test-jti-123", "testuser")),
        ):
            with patch(
                "app.services.auth.get_user_by_username_repo",
                AsyncMock(return_value=mock_user),
            ):
                jti, user_data = await authenticate_user_by_token(access_token, mock_db)

                assert jti == "test-jti-123"
                assert user_data["id"] == mock_user.id
                assert user_data["username"] == mock_user.username
                assert user_data["role"] == mock_user.role
                assert user_data["is_active"] == mock_user.is_active
                assert (
                    user_data["must_change_password"] == mock_user.must_change_password
                )

    @pytest.mark.asyncio
    async def test_authenticate_user_by_token_invalid_token(self, mock_db):
        """Test authentication with invalid token."""
        with patch(
            "app.services.auth.verify_access_token",
            AsyncMock(side_effect=jwt.InvalidTokenError("Invalid token")),
        ):
            with pytest.raises(jwt.InvalidTokenError, match="Invalid token"):
                await authenticate_user_by_token("invalid_token", mock_db)

    @pytest.mark.asyncio
    async def test_authenticate_user_by_token_expired_token(self, mock_db):
        """Test authentication with expired token."""
        with patch(
            "app.services.auth.verify_access_token",
            AsyncMock(side_effect=jwt.ExpiredSignatureError("Token expired")),
        ):
            with pytest.raises(jwt.ExpiredSignatureError, match="Token expired"):
                await authenticate_user_by_token("expired_token", mock_db)

    @pytest.mark.asyncio
    async def test_authenticate_user_by_token_missing_username(self, mock_db):
        """Test authentication when token has no username."""
        with pytest.raises(jwt.InvalidTokenError):
            await authenticate_user_by_token("some_token", mock_db)


class TestLogoutUser:
    """Tests for logout_user function."""

    @pytest.mark.asyncio
    async def test_logout_user_success(
        self, mock_db, mock_user, mock_refresh_token, refresh_token
    ):
        """Test successful user logout."""
        with patch(
            "app.services.auth.get_user_by_username_repo",
            AsyncMock(return_value=mock_user),
        ):
            with patch("app.services.auth.hash_token", return_value="hashed_token"):
                with patch(
                    "app.services.auth.get_refresh_token_by_hash",
                    AsyncMock(return_value=mock_refresh_token),
                ):
                    await logout_user("testuser", refresh_token, mock_db)

                    assert mock_refresh_token.is_revoked is True
                    mock_db.add.assert_called_once_with(mock_refresh_token)

    @pytest.mark.asyncio
    async def test_logout_user_user_not_found(self, mock_db):
        """Test logout with non-existent user."""
        with patch(
            "app.services.auth.get_user_by_username_repo", AsyncMock(return_value=None)
        ):
            with pytest.raises(AuthenticationError, match="Invalid credentials"):
                await logout_user("nonexistent", "refresh_token", mock_db)

    @pytest.mark.asyncio
    async def test_logout_user_token_not_found(self, mock_db, mock_user):
        """Test logout when refresh token not found."""
        with patch(
            "app.services.auth.get_user_by_username_repo",
            AsyncMock(return_value=mock_user),
        ):
            with patch("app.services.auth.hash_token", return_value="hashed_token"):
                with patch(
                    "app.services.auth.get_refresh_token_by_hash",
                    AsyncMock(return_value=None),
                ):
                    with pytest.raises(
                        AuthenticationError, match="Invalid credentials"
                    ):
                        await logout_user("testuser", "refresh_token", mock_db)

    @pytest.mark.asyncio
    async def test_logout_user_token_does_not_match_user(
        self, mock_db, mock_user, mock_refresh_token
    ):
        """Test logout when token doesn't belong to the user."""
        # Create a different user for the token
        other_user = MagicMock(spec=User)
        other_user.username = "otheruser"
        mock_refresh_token.user = other_user

        with patch(
            "app.services.auth.get_user_by_username_repo",
            AsyncMock(return_value=mock_user),
        ):
            with patch("app.services.auth.hash_token", return_value="hashed_token"):
                with patch(
                    "app.services.auth.get_refresh_token_by_hash",
                    AsyncMock(return_value=mock_refresh_token),
                ):
                    with pytest.raises(
                        AuthenticationError, match="Invalid credentials"
                    ):
                        await logout_user("testuser", "refresh_token", mock_db)


class TestRefreshAccessToken:
    """Tests for refresh_access_token function."""

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, mock_db, client_info):
        """Test successful token refresh."""
        with patch("app.services.auth.DatabaseTokenStore", MagicMock()):
            with patch(
                "app.services.auth.verify_refresh_token",
                AsyncMock(return_value=MagicMock()),
            ):
                with patch(
                    "app.services.auth.rotate_refresh_token",
                    AsyncMock(
                        return_value={
                            "access_token": "new_access123",
                            "refresh_token": "new_refresh123",
                            "token_type": "bearer",
                        }
                    ),
                ):
                    result = await refresh_access_token(
                        token="refresh_token",
                        db=mock_db,
                        client_info=client_info,
                    )

                    assert result["access_token"] == "new_access123"
                    assert result["refresh_token"] == "new_refresh123"
                    assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_access_token_success_without_client_info(self, mock_db):
        """Test token refresh without client info."""
        with patch("app.services.auth.DatabaseTokenStore", MagicMock()):
            with patch(
                "app.services.auth.verify_refresh_token",
                AsyncMock(return_value=MagicMock()),
            ):
                with patch(
                    "app.services.auth.rotate_refresh_token",
                    AsyncMock(
                        return_value={
                            "access_token": "new_access123",
                            "refresh_token": "new_refresh123",
                            "token_type": "bearer",
                        }
                    ),
                ):
                    result = await refresh_access_token(
                        token="refresh_token",
                        db=mock_db,
                        client_info=None,
                    )

                    assert result["access_token"] == "new_access123"

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self, mock_db):
        """Test token refresh with invalid token."""
        with patch("app.services.auth.DatabaseTokenStore", MagicMock()):
            with patch(
                "app.services.auth.verify_refresh_token",
                AsyncMock(side_effect=ValueError("Invalid token")),
            ):
                with pytest.raises(AuthenticationError, match="Invalid credentials"):
                    await refresh_access_token(
                        token="invalid_token",
                        db=mock_db,
                        client_info=None,
                    )


class TestExpireUserSessions:
    """Tests for expire_user_sessions function."""

    @pytest.mark.asyncio
    async def test_expire_user_sessions_success(self, mock_db, mock_user):
        """Test successful expiration of all user sessions."""
        token1 = MagicMock(spec=RefreshToken)
        token1.is_revoked = False
        token2 = MagicMock(spec=RefreshToken)
        token2.is_revoked = False
        mock_user.refresh_tokens = [token1, token2]

        with patch(
            "app.services.auth.get_user_by_id_repo", AsyncMock(return_value=mock_user)
        ):
            result = await expire_user_sessions(mock_user.id, mock_db)

            assert token1.is_revoked is True
            assert token2.is_revoked is True
            assert result == mock_user

    @pytest.mark.asyncio
    async def test_expire_user_sessions_user_not_found(self, mock_db):
        """Test expiring sessions for non-existent user."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        with patch(
            "app.services.auth.get_user_by_id_repo", AsyncMock(return_value=None)
        ):
            with pytest.raises(AuthenticationError, match="User not found"):
                await expire_user_sessions(user_id, mock_db)

    @pytest.mark.asyncio
    async def test_expire_user_sessions_only_revokes_active_tokens(
        self, mock_db, mock_user
    ):
        """Test that only non-revoked tokens are marked as revoked."""
        token1 = MagicMock(spec=RefreshToken)
        token1.is_revoked = False
        token2 = MagicMock(spec=RefreshToken)
        token2.is_revoked = True  # Already revoked
        mock_user.refresh_tokens = [token1, token2]

        with patch(
            "app.services.auth.get_user_by_id_repo", AsyncMock(return_value=mock_user)
        ):
            await expire_user_sessions(mock_user.id, mock_db)

            assert token1.is_revoked is True
            # token2 should remain revoked (not changed)
            assert token2.is_revoked is True
