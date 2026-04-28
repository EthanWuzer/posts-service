import os
from dotenv import load_dotenv

load_dotenv()

# No localhost fallback: inside a container, localhost resolves to the
# container's own loopback interface, not the mongo service. Failing loudly
# here makes a missing env var immediately visible instead of producing a
# silent, hard-to-diagnose connection timeout.
MONGO_URI = os.environ["MONGO_URI"]

# JWT verification (RS256). Key path is optional so the module imports cleanly
# in test environments where the dependency is overridden.
JWT_PUBLIC_KEY_PATH = os.getenv("JWT_PUBLIC_KEY_PATH", "")
JWT_ISSUER = os.getenv("JWT_ISSUER", "instaclone")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "instaclone-users")

# Users-service base URL (e.g. http://users-api:8080). Empty in tests — the
# dependency is mocked so no real connection is ever attempted.
USERS_SERVICE_BASE_URL = os.getenv("USERS_SERVICE_BASE_URL", "")

# Placeholder stored on new posts/comments until the users-service exposes
# a profile-picture field.
DEFAULT_PROFILE_PICTURE_URL = os.getenv("DEFAULT_PROFILE_PICTURE_URL", "")
