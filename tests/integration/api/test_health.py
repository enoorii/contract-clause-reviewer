# tests/integration/api/test_health.py

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.database import get_db
from app.main import app


@pytest.fixture(scope="function")
async def client(pglite_async_session):
    """Create test client with async dependency override."""

    # Store original overrides
    original_overrides = app.dependency_overrides.copy()

    async def override_get_db():
        return pglite_async_session

    app.dependency_overrides[get_db] = override_get_db

    # Create async client with the correct base URL
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Test the health endpoint."""

    async def test_health_endpoint_success(self, client):
        """Test health endpoint returns 200 OK."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Service is running"

    async def test_health_endpoint_response_format(self, client):
        """Test health endpoint response format."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)
