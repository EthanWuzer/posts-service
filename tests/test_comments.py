import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.db.mongo import get_db
from tests.conftest import TEST_USER_ID, _clear_overrides, _override_auth, mock_get_username


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_post_id():
    return "post-abc-123"


@pytest.fixture
def sample_comment_id():
    return "comment-xyz-789"


@pytest.fixture
def sample_comment_body():
    return {"text": "Great post!"}


@pytest.fixture
def sample_comment_doc(sample_comment_id):
    return {
        "commentId": sample_comment_id,
        "userId": TEST_USER_ID,
        "username": "alice",
        "userProfilePictureUrl": "",
        "text": "Great post!",
        "likes": 0,
        "timestamp": "2026-04-07T00:00:00+00:00",
    }


@pytest.fixture
def sample_post_doc(sample_post_id, sample_comment_doc):
    return {
        "_id": sample_post_id,
        "postId": sample_post_id,
        "userId": TEST_USER_ID,
        "username": "alice",
        "userProfilePictureUrl": "",
        "imgUrl": "https://example.com/img.jpg",
        "caption": "Hello world",
        "timestamp": "2026-04-07T00:00:00+00:00",
        "likes": 0,
        "comments": [sample_comment_doc],
    }


def make_update_result(modified_count: int, matched_count: int = 1) -> MagicMock:
    result = MagicMock()
    result.modified_count = modified_count
    result.matched_count = matched_count
    return result


def make_mock_collection(**overrides) -> AsyncMock:
    collection = AsyncMock()
    collection.find_one = overrides.get("find_one", AsyncMock(return_value=None))
    collection.update_one = overrides.get(
        "update_one", AsyncMock(return_value=make_update_result(modified_count=1))
    )
    return collection


# ---------------------------------------------------------------------------
# POST /posts/{post_id}/comments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_comment_happy_path(sample_post_id, sample_post_doc, sample_comment_body):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=1)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        with mock_get_username():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/posts/{sample_post_id}/comments",
                    json=sample_comment_body,
                )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    data = response.json()
    assert "commentId" in data
    assert data["userId"] == TEST_USER_ID
    assert data["username"] == "alice"
    assert data["userProfilePictureUrl"] == ""
    assert data["text"] == sample_comment_body["text"]
    assert data["likes"] == 0
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_add_comment_not_found(sample_post_id, sample_comment_body):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=None),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/posts/{sample_post_id}/comments",
                json=sample_comment_body,
            )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert sample_post_id in data["detail"]


@pytest.mark.asyncio
async def test_add_comment_bad_input(sample_post_id):
    # Missing required field 'text' → 422
    app.dependency_overrides[get_db] = lambda: make_mock_collection()
    _override_auth()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/posts/{sample_post_id}/comments",
                json={},
            )
    finally:
        _clear_overrides()

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_comment_no_auth_returns_401(sample_post_id, sample_comment_body):
    app.dependency_overrides[get_db] = lambda: make_mock_collection()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/posts/{sample_post_id}/comments",
                json=sample_comment_body,
            )
    finally:
        _clear_overrides()

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /posts/{post_id}/comments/{comment_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_comment_happy_path(sample_post_id, sample_post_doc, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=1)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_comment_not_found_post(sample_post_id, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=None),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert sample_post_id in data["detail"]


@pytest.mark.asyncio
async def test_delete_comment_not_found_comment(sample_post_id, sample_post_doc, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=0)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/nonexistent-comment-id"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "nonexistent-comment-id" in data["detail"]


@pytest.mark.asyncio
async def test_delete_comment_wrong_user_returns_403(
    sample_post_id, sample_post_doc, sample_comment_id
):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth("different-user")

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# PUT /posts/{post_id}/comments/{comment_id}/likes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_like_comment_happy_path(sample_post_id, sample_post_doc, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=1)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}/likes"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_like_comment_not_found_post(sample_post_id, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=None),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}/likes"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert sample_post_id in data["detail"]


@pytest.mark.asyncio
async def test_like_comment_not_found_comment(sample_post_id, sample_post_doc):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=0)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{sample_post_id}/comments/nonexistent-comment-id/likes"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "nonexistent-comment-id" in data["detail"]


# ---------------------------------------------------------------------------
# DELETE /posts/{post_id}/comments/{comment_id}/likes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unlike_comment_happy_path(sample_post_id, sample_post_doc, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=1)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}/likes"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unlike_comment_likes_already_zero(
    sample_post_id, sample_post_doc, sample_comment_id
):
    post_find = AsyncMock(
        side_effect=[
            sample_post_doc,   # first find_one: post existence check
            sample_post_doc,   # second find_one: comment existence fallback check
        ]
    )
    mock_collection = make_mock_collection(
        find_one=post_find,
        update_one=AsyncMock(return_value=make_update_result(modified_count=0)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}/likes"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unlike_comment_not_found_post(sample_post_id, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=None),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}/likes"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert sample_post_id in data["detail"]


@pytest.mark.asyncio
async def test_unlike_comment_not_found_comment(sample_post_id, sample_post_doc):
    post_find = AsyncMock(
        side_effect=[
            sample_post_doc,   # first find_one: post existence check
            None,              # second find_one: comment existence fallback — not found
        ]
    )
    mock_collection = make_mock_collection(
        find_one=post_find,
        update_one=AsyncMock(return_value=make_update_result(modified_count=0)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/nonexistent-comment-id/likes"
            )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "nonexistent-comment-id" in data["detail"]
