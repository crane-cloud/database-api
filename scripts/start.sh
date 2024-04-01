#!/bin/bash

# Run Migrations
poetry run alembic upgrade head

# Start the server
poetry run python uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4