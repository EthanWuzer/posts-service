import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.db.mongo import get_db
from app.dependencies.auth import get_current_user_id


# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

SAMPLE_POST_ID = "550e8400-e29b-41d4-a716-446655440000"
CURRENT_USER_ID = "user-001"
OTHER_USER_ID = "user-999"

SAMPLE_POST_DOC = {
    "_id": SAMPLE_POST_ID,
    "userId": CURRENT_USER_ID,
    "username": "alice",
    "userProfilePictureUrl": "https://example.com/alice.jpg",
    "imgUrl": f"https://r2.example.com/{SAMPLE_POST_ID}.jpg",
    "caption": "Hello world",
    "timestamp": "2026-04-07T00:00:00+00:00",
    "likedBy": [],
    "comments": [],
}

# Minimal valid JPEG magic bytes — enough for content-type sniffing in tests
MINIMAL_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 10

VALID_POST_CREATE_DATA = {
    "username": "alice",
    "userProfilePictureUrl": "https://example.com/alice.jpg",
    "caption": "Hello world",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_collection_mock() -> AsyncMock:
    return AsyncMock()


def _override_db(mock_collection):
    app.dependency_overrides[get_db] = lambda: mock_collection


def _override_auth(user_id: str = CURRENT_USER_ID):
    app.dependency_overrides[get_current_user_id] = lambda: user_id


def _clear_overrides():
    app.dependency_overrides.clear()


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
    assert data[0]["likedBy"] == []


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
<<<<<<< Updated upstream
             patch("app.routes.posts.save_image", new=AsyncMock(return_value=f"https://pub.r2.dev/{SAMPLE_POST_ID}.jpg")):
=======
             patch("app.routes.posts.save_image", new=AsyncMock(return_value=f"{SAMPLE_POST_ID}.jpg")), \
             patch("app.routes.posts.get_image_url", return_value=f"https://r2.example.com/{SAMPLE_POST_ID}.jpg"):
>>>>>>> Stashed changes
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
    assert data["userId"] == CURRENT_USER_ID
    assert data["caption"] == "Hello world"
<<<<<<< Updated upstream
    assert data["imgUrl"] == f"https://pub.r2.dev/{SAMPLE_POST_ID}.jpg"
    assert data["likes"] == 0
=======
    assert data["likedBy"] == []
>>>>>>> Stashed changes
    assert data["comments"] == []
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_create_post_no_auth():
    mock_col = _make_collection_mock()
    _override_db(mock_col)
    # No auth override — dependency will try to fetch real JWT and fail

    try:
<<<<<<< Updated upstream
        with patch("app.routes.posts.validate_image", return_value="jpg"), \
             patch("app.routes.posts.save_image", new=AsyncMock(return_value=f"https://pub.r2.dev/{SAMPLE_POST_ID}.jpg")):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/posts",
                    data=VALID_POST_CREATE_DATA,
                    files={"image": ("photo.jpg", MINIMAL_JPEG_BYTES, "image/jpeg")},
                )
=======
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/posts",
                data=VALID_POST_CREATE_DATA,
                files={"image": ("photo.jpg", MINIMAL_JPEG_BYTES, "image/jpeg")},
            )
>>>>>>> Stashed changes
    finally:
        _clear_overrides()

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_post_bad_input():
    # Missing required form fields → 422
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
    _override_db(_make_collection_mock())
    _override_auth()
    try:
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
    assert data["likedBy"] == []
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
async def test_update_post_forbidden():
    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = dict(SAMPLE_POST_DOC)  # owned by CURRENT_USER_ID
    _override_db(mock_col)
    _override_auth(OTHER_USER_ID)  # different user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/posts/{SAMPLE_POST_ID}",
                data={"caption": "Sneaky update"},
            )
    finally:
        _clear_overrides()

    assert response.status_code == 403


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
    existing_doc["imgUrl"] = "https://r2.example.com/old-file.jpg"

    updated_doc = dict(existing_doc)
    updated_doc["imgUrl"] = f"https://r2.example.com/{SAMPLE_POST_ID}.jpg"

    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = existing_doc
    mock_col.find_one_and_update.return_value = updated_doc
    _override_db(mock_col)
    _override_auth()

    try:
        with patch("app.routes.posts.validate_image", return_value="jpg"), \
<<<<<<< Updated upstream
             patch("app.routes.posts.save_image", new=AsyncMock(return_value=f"https://pub.r2.dev/{SAMPLE_POST_ID}.jpg")), \
=======
             patch("app.routes.posts.save_image", new=AsyncMock(return_value=f"{SAMPLE_POST_ID}.jpg")), \
             patch("app.routes.posts.get_image_url", return_value=f"https://r2.example.com/{SAMPLE_POST_ID}.jpg"), \
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
    mock_delete.assert_called_once_with("http://test/uploads/old-file.jpg")
=======
>>>>>>> Stashed changes


# ---------------------------------------------------------------------------
# DELETE /posts/{post_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_post_happy_path():
    doc_with_img = dict(SAMPLE_POST_DOC)

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
<<<<<<< Updated upstream
    mock_col.find_one_and_delete.assert_called_once_with({"_id": SAMPLE_POST_ID})
    mock_delete.assert_called_once_with(f"http://test/uploads/{SAMPLE_POST_ID}.jpg")
=======
    mock_col.find_one.assert_called_once_with({"_id": SAMPLE_POST_ID})


@pytest.mark.asyncio
async def test_delete_post_forbidden():
    mock_col = _make_collection_mock()
    mock_col.find_one.return_value = dict(SAMPLE_POST_DOC)  # owned by CURRENT_USER_ID
    _override_db(mock_col)
    _override_auth(OTHER_USER_ID)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/posts/{SAMPLE_POST_ID}")
    finally:
        _clear_overrides()

    assert response.status_code == 403
>>>>>>> Stashed changes


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


# ---------------------------------------------------------------------------
# PUT /posts/{post_id}/likes  (like)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_like_post_happy_path():
    liked_doc = dict(SAMPLE_POST_DOC)
    liked_doc["likedBy"] = [CURRENT_USER_ID]

    mock_col = _make_collection_mock()
    mock_col.find_one_and_update.return_value = liked_doc
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
    assert CURRENT_USER_ID in response.json()["likedBy"]


@pytest.mark.asyncio
async def test_like_post_idempotent():
    # Liking again: $addToSet no-ops, doc still returned with user in likedBy
    liked_doc = dict(SAMPLE_POST_DOC)
    liked_doc["likedBy"] = [CURRENT_USER_ID]

    mock_col = _make_collection_mock()
    mock_col.find_one_and_update.return_value = liked_doc
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
    assert response.json()["likedBy"].count(CURRENT_USER_ID) == 1


@pytest.mark.asyncio
async def test_like_post_not_found():
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


# ---------------------------------------------------------------------------
# DELETE /posts/{post_id}/likes  (unlike)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unlike_post_happy_path():
    unliked_doc = dict(SAMPLE_POST_DOC)
    unliked_doc["likedBy"] = []

    mock_col = _make_collection_mock()
    mock_col.find_one_and_update.return_value = unliked_doc
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
    assert CURRENT_USER_ID not in response.json()["likedBy"]


@pytest.mark.asyncio
async def test_unlike_post_not_found():
    mock_col = _make_collection_mock()
    mock_col.find_one_and_update.return_value = None
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
