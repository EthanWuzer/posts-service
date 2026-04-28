from unittest.mock import AsyncMock, patch as mock_patch

from app.auth import get_current_user_id
from app.main import app

# Matches the userId stored in all test fixtures so ownership checks pass.
TEST_USER_ID = "user-001"
TEST_USERNAME = "alice"


def _override_auth(user_id: str = TEST_USER_ID):
    app.dependency_overrides[get_current_user_id] = lambda: user_id


def _clear_overrides():
    app.dependency_overrides.clear()


def mock_get_username(username: str = TEST_USERNAME):
    """Context manager that replaces the users-service HTTP call in tests."""
    return mock_patch(
        "app.services.users_client.get_username",
        new=AsyncMock(return_value=username),
    )
