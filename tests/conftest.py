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


def mock_get_user(username: str = TEST_USERNAME, profile_pic_url: str = ""):
    """Patch get_user — used by create_post and add_comment (single-user write-time lookup)."""
    return mock_patch(
        "app.services.users_client.get_user",
        new=AsyncMock(return_value={"username": username, "profilePicUrl": profile_pic_url}),
    )


def mock_get_users(user_id: str = TEST_USER_ID, username: str = TEST_USERNAME, profile_pic_url: str = ""):
    """Patch get_users — used by all read/mutate endpoints (batch lookup)."""
    return mock_patch(
        "app.services.users_client.get_users",
        new=AsyncMock(return_value={user_id: {"username": username, "profilePicUrl": profile_pic_url}}),
    )
