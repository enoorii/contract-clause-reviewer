import pytest


@pytest.fixture(scope="session")
def secret_key():
    return "THISISSECRETKEYforPYTESTfixutreGOOD"
