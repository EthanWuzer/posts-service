# Posts Service

## API Reference

The Posts microservice provides a REST API for managing social-media-style posts and their associated comments. It supports full CRUD operations on posts, nested comment creation and deletion, and independent like/unlike actions on both posts and comments. Posts are stored in MongoDB, with all identifiers server-generated as UUIDs and all timestamps recorded in UTC ISO 8601 format. The service exposes 11 endpoints across two route groups: `/posts` for post-level operations and `/posts/{post_id}/comments` for comment-level operations.

---

### GET /posts

Retrieves all posts in the collection as an array.

**Response**

```json
[
  {
    "postId": "a3f1c2d4-58e6-4b7a-9c0d-1e2f3a4b5c6d",
    "userId": "user_001",
    "username": "jane_doe",
    "userProfilePictureUrl": "https://cdn.example.com/avatars/jane_doe.jpg",
    "imgUrl": "https://cdn.example.com/posts/sunset_hike.jpg",
    "caption": "Golden hour on the trail. Worth every step.",
    "timestamp": "2026-04-06T18:32:10.123456+00:00",
    "likes": 42,
    "comments": []
  },
  {
    "postId": "b7e9d1f0-23c4-4a5b-8e6f-7d8c9a0b1c2e",
    "userId": "user_002",
    "username": "john_smith",
    "userProfilePictureUrl": "https://cdn.example.com/avatars/john_smith.jpg",
    "imgUrl": "https://cdn.example.com/posts/morning_coffee.jpg",
    "caption": "Monday fuel. Strong and black.",
    "timestamp": "2026-04-07T08:15:00.000000+00:00",
    "likes": 7,
    "comments": [
      {
        "commentId": "c1a2b3d4-e5f6-7890-abcd-ef1234567890",
        "userId": "user_003",
        "username": "alice_w",
        "userProfilePictureUrl": "https://cdn.example.com/avatars/alice_w.jpg",
        "text": "Same! Cannot function without it.",
        "likes": 2,
        "timestamp": "2026-04-07T08:20:00.000000+00:00"
      }
    ]
  }
]
```

---

### POST /posts

Creates a new post with a server-generated `postId` and UTC timestamp, initializing `likes` to `0` and `comments` to an empty array.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `userId` | string | Yes | Unique identifier of the user creating the post. |
| `username` | string | Yes | Display name of the author shown on the post. |
| `userProfilePictureUrl` | string | Yes | Fully-qualified URL to the author's profile picture. |
| `imgUrl` | string | Yes | Fully-qualified URL to the post's primary image. |
| `caption` | string | Yes | Text caption accompanying the post image. |

**Response**

```json
{
  "postId": "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
  "userId": "user_001",
  "username": "jane_doe",
  "userProfilePictureUrl": "https://cdn.example.com/avatars/jane_doe.jpg",
  "imgUrl": "https://cdn.example.com/posts/mountain_view.jpg",
  "caption": "Peak bagged. Views absolutely unreal up here.",
  "timestamp": "2026-04-07T14:05:22.847291+00:00",
  "likes": 0,
  "comments": []
}
```

**Error Responses**

- `422 Unprocessable Entity`: One or more required fields are missing or fail Pydantic type validation.

---

### GET /posts/{post_id}

Retrieves the post with the specified `post_id`.

**Response**

```json
{
  "postId": "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
  "userId": "user_001",
  "username": "jane_doe",
  "userProfilePictureUrl": "https://cdn.example.com/avatars/jane_doe.jpg",
  "imgUrl": "https://cdn.example.com/posts/mountain_view.jpg",
  "caption": "Peak bagged. Views absolutely unreal up here.",
  "timestamp": "2026-04-07T14:05:22.847291+00:00",
  "likes": 12,
  "comments": []
}
```

**Error Responses**

- `404 Not Found`: No post exists with the given `post_id`.

---

### PUT /posts/{post_id}

Updates the `caption`, `imgUrl`, or both on the post with the specified `post_id`; omitted fields are left unchanged.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `caption` | string | No | Replacement caption text for the post. |
| `imgUrl` | string | No | Replacement URL for the post's primary image. |

**Response**

```json
{
  "postId": "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
  "userId": "user_001",
  "username": "jane_doe",
  "userProfilePictureUrl": "https://cdn.example.com/avatars/jane_doe.jpg",
  "imgUrl": "https://cdn.example.com/posts/mountain_view_v2.jpg",
  "caption": "Updated: this view never gets old.",
  "timestamp": "2026-04-07T14:05:22.847291+00:00",
  "likes": 12,
  "comments": []
}
```

**Error Responses**

- `404 Not Found`: No post exists with the given `post_id`.
- `422 Unprocessable Entity`: Request body fails Pydantic type validation.

---

### DELETE /posts/{post_id}

Permanently deletes the post with the specified `post_id`, including all its comments.

**Response**

No response body. Returns `204 No Content` on success.

**Error Responses**

- `404 Not Found`: No post exists with the given `post_id`.

---

### PUT /posts/{post_id}/likes

Increments the like count on the post with the specified `post_id` by 1.

**Response**

```json
{
  "postId": "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
  "userId": "user_001",
  "username": "jane_doe",
  "userProfilePictureUrl": "https://cdn.example.com/avatars/jane_doe.jpg",
  "imgUrl": "https://cdn.example.com/posts/mountain_view.jpg",
  "caption": "Peak bagged. Views absolutely unreal up here.",
  "timestamp": "2026-04-07T14:05:22.847291+00:00",
  "likes": 13,
  "comments": []
}
```

**Error Responses**

- `404 Not Found`: No post exists with the given `post_id`.

---

### DELETE /posts/{post_id}/likes

Decrements the like count on the post with the specified `post_id` by 1, floored at 0; if `likes` is already `0` the post is returned unchanged.

**Response**

```json
{
  "postId": "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
  "userId": "user_001",
  "username": "jane_doe",
  "userProfilePictureUrl": "https://cdn.example.com/avatars/jane_doe.jpg",
  "imgUrl": "https://cdn.example.com/posts/mountain_view.jpg",
  "caption": "Peak bagged. Views absolutely unreal up here.",
  "timestamp": "2026-04-07T14:05:22.847291+00:00",
  "likes": 12,
  "comments": []
}
```

**Error Responses**

- `404 Not Found`: No post exists with the given `post_id`.

---

### POST /posts/{post_id}/comments

Adds a new comment to the post with the specified `post_id` and returns the created comment.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `userId` | string | Yes | Unique identifier of the user submitting the comment. |
| `username` | string | Yes | Display name of the commenter shown alongside the comment. |
| `userProfilePictureUrl` | string | Yes | Fully-qualified URL to the commenter's profile picture. |
| `text` | string | Yes | Body text of the comment. |

**Response**

```json
{
  "commentId": "e9f0a1b2-c3d4-4e5f-6a7b-8c9d0e1f2a3b",
  "userId": "user_003",
  "username": "alice_w",
  "userProfilePictureUrl": "https://cdn.example.com/avatars/alice_w.jpg",
  "text": "Absolutely breathtaking! Which trail is this?",
  "likes": 0,
  "timestamp": "2026-04-07T15:10:05.612300+00:00"
}
```

**Error Responses**

- `404 Not Found`: No post exists with the given `post_id`.
- `422 Unprocessable Entity`: One or more required fields are missing or fail Pydantic type validation.

---

### DELETE /posts/{post_id}/comments/{comment_id}

Removes the comment with the specified `comment_id` from the post with the specified `post_id`.

**Response**

No response body. Returns `204 No Content` on success.

**Error Responses**

- `404 Not Found`: No post exists with the given `post_id`, or no comment exists with the given `comment_id` on that post.

---

### PUT /posts/{post_id}/comments/{comment_id}/likes

Increments the like count on the specified comment by 1.

**Response**

```json
{
  "message": "Comment liked successfully."
}
```

**Error Responses**

- `404 Not Found`: No post exists with the given `post_id`, or no comment exists with the given `comment_id` on that post.

---

### DELETE /posts/{post_id}/comments/{comment_id}/likes

Decrements the like count on the specified comment by 1, floored at 0; if `likes` is already `0` the operation is silently skipped.

**Response**

```json
{
  "message": "Comment unliked successfully."
}
```

**Error Responses**

- `404 Not Found`: No post exists with the given `post_id`, or no comment exists with the given `comment_id` on that post.

---

## Running Locally

**Prerequisites:** Docker and Docker Compose must be installed.

1. Navigate to the service directory:
   ```bash
   cd posts-service
   ```

2. Copy the environment file and fill in any required values:
   ```bash
   cp .env.example .env
   ```

3. Build and start all services:
   ```bash
   docker-compose up --build
   ```

4. The API will be available at `http://localhost:8000`.

5. Interactive Swagger UI docs are available at `http://localhost:8000/docs`.

6. To stop all services and remove containers:
   ```bash
   docker-compose down
   ```

---

## Project Structure

```
posts-service/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point; registers routers
│   ├── config.py                # Environment variable loading and settings
│   ├── db/
│   │   ├── __init__.py
│   │   └── mongo.py             # MongoDB client setup and get_db dependency
│   ├── models/
│   │   ├── __init__.py
│   │   ├── post.py              # Pydantic models: Post, PostCreate, PostUpdate
│   │   └── comment.py           # Pydantic models: Comment, CommentCreate
│   └── routes/
│       ├── __init__.py
│       ├── posts.py             # CRUD routes and like/unlike routes for posts
│       └── comments.py          # Add/delete comment routes and comment like/unlike routes
├── tests/
│   ├── test_posts.py            # Unit/integration tests for post endpoints
│   └── test_comments.py         # Unit/integration tests for comment endpoints
├── .env.example                 # Template for required environment variables
├── docker-compose.yml           # Defines the app service and MongoDB service
├── Dockerfile                   # Multi-stage build for the FastAPI application
└── requirements.txt             # Python package dependencies
```
