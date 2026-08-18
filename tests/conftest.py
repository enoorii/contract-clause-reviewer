import pytest

from app.core.config import setting


@pytest.fixture(scope="session")
def secret_key():
    return setting.SECRET_KEY
