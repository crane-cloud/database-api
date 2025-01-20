#! /bin/bash


# apply migrations onto db
poetry run alembic upgrade head

# start server
poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program gunicorn --worker-tmp-dir /dev/shm --workers=4 --bind 0.0.0.0:8000 --timeout 240 main:app