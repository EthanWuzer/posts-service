import os
from dotenv import load_dotenv

load_dotenv()

# No localhost fallback: inside a container, localhost resolves to the
# container's own loopback interface, not the mongo service. Failing loudly
# here makes a missing env var immediately visible instead of producing a
# silent, hard-to-diagnose connection timeout.
MONGO_URI = os.environ["MONGO_URI"]
