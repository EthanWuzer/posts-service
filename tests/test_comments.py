import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.db.mongo import get_db


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
    return {
        "userId": "user-001",
        "username": "alice",
        "userProfilePictureUrl": "https://example.com/alice.jpg",
        "text": "Great post!",
    }


@pytest.fixture
def sample_comment_doc(sample_comment_id):
    return {
        "commentId": sample_comment_id,
        "userId": "user-001",
        "username": "alice",
        "userProfilePictureUrl": "https://example.com/alice.jpg",
        "text": "Great post!",
        "likes": 0,
        "timestamp": "2026-04-07T00:00:00+00:00",
    }


@pytest.fixture
def sample_post_doc(sample_post_id, sample_comment_doc):
    return {
        "_id": sample_post_id,
        "postId": sample_post_id,
        "userId": "user-001",
        "username": "alice",
        "userProfilePictureUrl": "https://example.com/alice.jpg",
        "imgUrl": "https://example.com/img.jpg",
        "caption": "Hello world",
        "timestamp": "2026-04-07T00:00:00+00:00",
        "likes": 0,
        "comments": [sample_comment_doc],
    }


def make_update_result(modified_count: int, matched_count: int = 1) -> MagicMock:
    """Return a mock that looks like a Motor UpdateResult."""
    result = MagicMock()
    result.modified_count = modified_count
    result.matched_count = matched_count
    return result


def make_mock_collection(**overrides) -> AsyncMock:
    """
    Return an AsyncMock wired up to behave like a Motor collection.
    Pass keyword arguments to override specific method return values.
    """
    collection = AsyncMock()
    collection.find_one = overrides.get("find_one", AsyncMock(return_value=None))
    collection.update_one = overrides.get(
        "update_one", AsyncMock(return_value=make_update_result(modified_count=1))
    )
    return collection


# ---------------------------------------------------------------------------
# POST /posts/{post_id}/comments
# ---------------------------------------------------------------------------

# Verify that adding a comment to an existing post returns 201 with the new comment body
@pytest.mark.asyncio
async def test_add_comment_happy_path(sample_post_id, sample_post_doc, sample_comment_body):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=1)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/posts/{sample_post_id}/comments",
                json=sample_comment_body,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert "commentId" in data
    assert data["userId"] == sample_comment_body["userId"]
    assert data["username"] == sample_comment_body["username"]
    assert data["userProfilePictureUrl"] == sample_comment_body["userProfilePictureUrl"]
    assert data["text"] == sample_comment_body["text"]
    assert data["likes"] == 0
    assert "timestamp" in data


# Verify that adding a comment to a non-existent post returns 404 with a detail message
@pytest.mark.asyncio
async def test_add_comment_not_found(sample_post_id, sample_comment_body):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=None),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/posts/{sample_post_id}/comments",
                json=sample_comment_body,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert sample_post_id in data["detail"]


# Verify that a comment request with missing required fields returns 422
@pytest.mark.asyncio
async def test_add_comment_bad_input(sample_post_id):
    # FastAPI resolves Depends(get_db) before body validation — mock is required
    app.dependency_overrides[get_db] = lambda: make_mock_collection()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/posts/{sample_post_id}/comments",
                json={"text": "Missing userId and username fields"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /posts/{post_id}/comments/{comment_id}
# ---------------------------------------------------------------------------

# Verify that deleting an existing comment from an existing post returns 204
@pytest.mark.asyncio
async def test_delete_comment_happy_path(sample_post_id, sample_post_doc, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=1)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204


# Verify that deleting a comment from a non-existent post returns 404 with a detail message
@pytest.mark.asyncio
async def test_delete_comment_not_found_post(sample_post_id, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=None),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert sample_post_id in data["detail"]


# Verify that deleting a comment that does not exist in the post returns 404 with a detail message
@pytest.mark.asyncio
async def test_delete_comment_not_found_comment(sample_post_id, sample_post_doc, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=0)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/nonexistent-comment-id"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "nonexistent-comment-id" in data["detail"]


# ---------------------------------------------------------------------------
# PUT /posts/{post_id}/comments/{comment_id}/likes
# ---------------------------------------------------------------------------

# Verify that liking a comment on an existing post returns 200
@pytest.mark.asyncio
async def test_like_comment_happy_path(sample_post_id, sample_post_doc, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=1)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}/likes"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


# Verify that liking a comment on a non-existent post returns 404 with a detail message
@pytest.mark.asyncio
async def test_like_comment_not_found_post(sample_post_id, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=None),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}/likes"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert sample_post_id in data["detail"]


# Verify that liking a non-existent comment on an existing post returns 404 with a detail message
@pytest.mark.asyncio
async def test_like_comment_not_found_comment(sample_post_id, sample_post_doc):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=0)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{sample_post_id}/comments/nonexistent-comment-id/likes"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "nonexistent-comment-id" in data["detail"]


# ---------------------------------------------------------------------------
# DELETE /posts/{post_id}/comments/{comment_id}/likes
# ---------------------------------------------------------------------------

# Verify that unliking a comment with likes > 0 decrements the count and returns 200
@pytest.mark.asyncio
async def test_unlike_comment_happy_path(sample_post_id, sample_post_doc, sample_comment_id):
    # Post has the comment; update succeeds (likes was > 0, decrement applied)
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=sample_post_doc),
        update_one=AsyncMock(return_value=make_update_result(modified_count=1)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}/likes"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


# Verify that unliking a comment whose likes is already 0 is a no-op and returns 200
@pytest.mark.asyncio
async def test_unlike_comment_likes_already_zero(
    sample_post_id, sample_post_doc, sample_comment_id
):
    # update_one returns modified_count=0 because array_filters excludes likes==0;
    # the follow-up find_one confirms the comment exists, so the route returns 200 silently.
    post_find = AsyncMock(
        side_effect=[
            sample_post_doc,           # first find_one: post existence check
            sample_post_doc,           # second find_one: comment existence fallback check
        ]
    )
    mock_collection = make_mock_collection(
        find_one=post_find,
        update_one=AsyncMock(return_value=make_update_result(modified_count=0)),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}/likes"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


# Verify that unliking a comment on a non-existent post returns 404 with a detail message
@pytest.mark.asyncio
async def test_unlike_comment_not_found_post(sample_post_id, sample_comment_id):
    mock_collection = make_mock_collection(
        find_one=AsyncMock(return_value=None),
    )
    app.dependency_overrides[get_db] = lambda: mock_collection

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/{sample_comment_id}/likes"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert sample_post_id in data["detail"]


# Verify that unliking a non-existent comment on an existing post returns 404 with a detail message
@pytest.mark.asyncio
async def test_unlike_comment_not_found_comment(sample_post_id, sample_post_doc):
    # update_one misses (modified_count=0) and the fallback find_one also returns None,
    # meaning the comment does not exist at all.
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

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                f"/posts/{sample_post_id}/comments/nonexistent-comment-id/likes"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "nonexistent-comment-id" in data["detail"]
