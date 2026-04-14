#!/bin/bash
cd /Users/ethanwu/Documents/softwareArch/posts/posts-service
MONGO_URI=x UPLOAD_DIR=/tmp python3 -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json
