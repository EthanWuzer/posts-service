import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.db.mongo import get_db
from tests.conftest import TEST_USER_ID, _clear_overrides, _override_auth, mock_get_username


# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

SAMPLE_POST_ID = "550e8400-e29b-41d4-a716-446655440000"

SAMPLE_POST_DOC = {
    "_id": SAMPLE_POST_ID,
    "userId": TEST_USER_ID,
    "username": "alice",
    "userProfilePictureUrl": "",
    "imgUrl": f"http://test/uploads/{SAMPLE_POST_ID}.jpg",
    "caption": "Hello world",
    "timestamp": "2026-04-07T00:00:00+00:00",
    "likes": 5,
    "comments": [],
}

# Minimal valid JPEG magic bytes — enough for content-type sniffing in tests
MINIMAL_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 10

VALID_POST_CREATE_DATA = {
    "caption": "Hello world",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_collection_mock() -> AsyncMock:
    return AsyncMock()


def _override_db(mock_collection):
    app.dependency_overrides[get_db] = lambda: mock_collection


# ---------------------------------------------------------------------------
# GET /posts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_posts_happy_path():
    mock_col = _make_collection_mock()
    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[dict(SAMPLE_POST_DOC)])
    mock_col.find = MagicMock(return_value=cursor_mock)
    _override_db(mock_col)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/posts")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["postId"] == SAMPLE_POST_ID
    assert data[0]["likes"] == 5


@pytest.mark.asyncio
async def test_get_posts_not_found():
    mock_col = _make_collection_mock()
    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[])
    mock_col.find = MagicMock(return_value=cursor_mock)
    _override_db(mock_col)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/posts")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_posts_bad_input():
    mock_col = _make_collection_mock()
    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=[])
    mock_col.find = MagicMock(return_value=cursor_mock)
    _override_db(mock_col)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/posts?invalid_param=!!!")
    finally:
        _clear_overrides()

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /posts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_post_happy_path():
    mock_col = _make_collection_mock()
    mock_col.insert_one.return_value = MagicMock(inserted_id=SAMPLE_POST_ID)
    _override_db(mock_col)
    _override_auth()

    try:
        with patch("app.routes.posts.validate_image", return_value="jpg"), \
             patch("app.routes.posts.save_image", new=AsyncMock(return_value=f"{SAMPLE_POST_ID}.jpg")), \
             mock_get_username():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/posts",
                    data=VALID_POST_CREATE_DATA,
                    files={"image": ("photo.jpg", MINIMAL_JPEG_BYTES, "image/jpeg")},
                )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    data = response.json()
    assert "postId" in data
    assert data["userId"] == TEST_USER_ID
    assert data["username"] == "alice"
    assert data["caption"] == "Hello world"
    assert data["imgUrl"] == f"http://test/uploads/{SAMPLE_POST_ID}.jpg"
    assert data["likes"] == 0
    assert data["comments"] == []
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_create_post_not_found():
    mock_col = _make_collection_mock()
    mock_col.insert_one.return_value = MagicMock(inserted_id=SAMPLE_POST_ID)
    _override_db(mock_col)
    _override_auth()

    try:
        with patch("app.routes.posts.validate_image", return_value="jpg"), \
             patch("app.routes.posts.save_image", new=AsyncMock(return_value=f"{SAMPLE_POST_ID}.jpg")), \
             mock_get_username():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/posts",
                    data=VALID_POST_CREATE_DATA,
                    files={"image": ("photo.jpg", MINIMAL_JPEG_BYTES, "image/jpeg")},
                )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    mock_col.insert_one.assert_called_once()
    call_doc = mock_col.insert_one.call_args[0][0]
    assert "postId" in call_doc
    assert call_doc["userId"] == TEST_USER_ID


@pytest.mark.asyncio
async def test_create_post_bad_input():
    # Missing required form field (image) → 422
    _override_db(_make_collection_mock())
    _override_auth()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/posts",
                data={"caption": "only caption"},
            )
    finally:
        _clear_overrides()

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_post_invalid_image_type():
    # Sending a non-JPEG/PNG file should return 400
    _override_db(_make_collection_mock())
    _override_auth()
    try:
        with mock_get_username():
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/posts",
                    data=VALID_POST_CREATE_DATA,
                    files={"image": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
                )
    finally:
        _clear_overrides()

    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_create_post_no_auth_returns_401():
    _override_db(_make_collection_mock())
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/posts",
                data=VALID_POST_CREATE_DATA,
                files={"image": ("photo.jpg", MINIMAL_JPEG_BYTES, "image/jpeg")},
            )
    finally:
        _clear_overrides()

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /posts/{post_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_post_happy_path():
    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = dict(SAMPLE_POST_DOC)
    _override_db(mock_col)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/posts/{SAMPLE_POST_ID}")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    data = response.json()
    assert data["postId"] == SAMPLE_POST_ID
    assert data["likes"] == 5
    mock_col.find_one.assert_called_once_with({"_id": SAMPLE_POST_ID})


@pytest.mark.asyncio
async def test_get_post_not_found():
    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = None
    _override_db(mock_col)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/posts/nonexistent-id")
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_post_bad_input():
    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = None
    _override_db(mock_col)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/posts/   ")
    finally:
        _clear_overrides()

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /posts/{post_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_post_happy_path():
    updated_doc = dict(SAMPLE_POST_DOC)
    updated_doc["caption"] = "Updated caption"

    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = dict(SAMPLE_POST_DOC)
    mock_col.find_one_and_update.return_value = updated_doc
    _override_db(mock_col)
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{SAMPLE_POST_ID}",
                data={"caption": "Updated caption"},
            )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["caption"] == "Updated caption"


@pytest.mark.asyncio
async def test_update_post_not_found():
    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = None
    _override_db(mock_col)
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                "/posts/nonexistent-id",
                data={"caption": "Irrelevant"},
            )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_post_bad_input():
    # Sending an unsupported file type returns 400
    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = dict(SAMPLE_POST_DOC)
    _override_db(mock_col)
    _override_auth()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{SAMPLE_POST_ID}",
                files={"image": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
            )
    finally:
        _clear_overrides()

    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_update_post_with_new_image():
    existing_doc = dict(SAMPLE_POST_DOC)
    existing_doc["imgUrl"] = f"http://test/uploads/old-file.jpg"

    updated_doc = dict(existing_doc)
    updated_doc["imgUrl"] = f"http://test/uploads/{SAMPLE_POST_ID}.jpg"

    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = existing_doc
    mock_col.find_one_and_update.return_value = updated_doc
    _override_db(mock_col)
    _override_auth()

    try:
        with patch("app.routes.posts.validate_image", return_value="jpg"), \
             patch("app.routes.posts.save_image", new=AsyncMock(return_value=f"{SAMPLE_POST_ID}.jpg")), \
             patch("app.routes.posts.delete_image") as mock_delete:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    f"/posts/{SAMPLE_POST_ID}",
                    files={"image": ("new.jpg", MINIMAL_JPEG_BYTES, "image/jpeg")},
                )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    mock_delete.assert_called_once_with("old-file.jpg")


@pytest.mark.asyncio
async def test_update_post_wrong_user_returns_403():
    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = dict(SAMPLE_POST_DOC)  # userId == TEST_USER_ID
    _override_db(mock_col)
    _override_auth("different-user")

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{SAMPLE_POST_ID}",
                data={"caption": "hacked"},
            )
    finally:
        _clear_overrides()

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /posts/{post_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_post_happy_path():
    doc_with_img = dict(SAMPLE_POST_DOC)
    doc_with_img["imgUrl"] = f"http://test/uploads/{SAMPLE_POST_ID}.jpg"

    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = doc_with_img
    mock_col.find_one_and_delete.return_value = doc_with_img
    _override_db(mock_col)
    _override_auth()

    try:
        with patch("app.routes.posts.delete_image") as mock_delete:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete(f"/posts/{SAMPLE_POST_ID}")
    finally:
        _clear_overrides()

    assert response.status_code == 204
    assert response.content == b""
    mock_col.find_one_and_delete.assert_called_once_with({"_id": SAMPLE_POST_ID})
    mock_delete.assert_called_once_with(f"{SAMPLE_POST_ID}.jpg")


@pytest.mark.asyncio
async def test_delete_post_not_found():
    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = None
    _override_db(mock_col)
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete("/posts/nonexistent-id")
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_post_bad_input():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete("/posts")

    assert response.status_code == 405


@pytest.mark.asyncio
async def test_delete_post_wrong_user_returns_403():
    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = dict(SAMPLE_POST_DOC)  # userId == TEST_USER_ID
    _override_db(mock_col)
    _override_auth("different-user")

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/posts/{SAMPLE_POST_ID}")
    finally:
        _clear_overrides()

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# PUT /posts/{post_id}/likes  (increment)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_increment_likes_happy_path():
    incremented_doc = dict(SAMPLE_POST_DOC)
    incremented_doc["likes"] = 6

    mock_col = _make_collection_mock()
    mock_col.find_one_and_update.return_value = incremented_doc
    _override_db(mock_col)
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(f"/posts/{SAMPLE_POST_ID}/likes")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["likes"] == 6


@pytest.mark.asyncio
async def test_increment_likes_not_found():
    mock_col = _make_collection_mock()
    mock_col.find_one_and_update.return_value = None
    _override_db(mock_col)
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put("/posts/nonexistent-id/likes")
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


@pytest.mark.asyncio
async def test_increment_likes_bad_input():
    mock_col = _make_collection_mock()
    mock_col.find_one_and_update.return_value = None
    _override_db(mock_col)
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{SAMPLE_POST_ID}/likes",
                content=b"not-json",
                headers={"Content-Type": "text/plain"},
            )
    finally:
        _clear_overrides()

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /posts/{post_id}/likes  (decrement)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_decrement_likes_happy_path():
    decremented_doc = dict(SAMPLE_POST_DOC)
    decremented_doc["likes"] = 4

    mock_col = _make_collection_mock()
    mock_col.find_one_and_update.return_value = decremented_doc
    _override_db(mock_col)
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/posts/{SAMPLE_POST_ID}/likes")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["likes"] == 4


@pytest.mark.asyncio
async def test_decrement_likes_not_found():
    mock_col = _make_collection_mock()
    mock_col.find_one_and_update.return_value = None
    mock_col.find_one.return_value = None
    _override_db(mock_col)
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete("/posts/nonexistent-id/likes")
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


@pytest.mark.asyncio
async def test_decrement_likes_bad_input():
    floored_doc = dict(SAMPLE_POST_DOC)
    floored_doc["likes"] = 0

    mock_col = _make_collection_mock()
    mock_col.find_one_and_update.return_value = None
    mock_col.find_one.return_value = floored_doc
    _override_db(mock_col)
    _override_auth()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/posts/{SAMPLE_POST_ID}/likes")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["likes"] == 0
