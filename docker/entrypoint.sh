#!/bin/sh
set -e

DATABASE_HOST=${DATABASE_HOST:-db}
DATABASE_PORT=${DATABASE_PORT:-5432}
APP_DIR=${APP_DIR:-server}
FASTAPI_ENV=${FASTAPI_ENV:-prod}

echo "Waiting for PostgreSQL at ${DATABASE_HOST}:${DATABASE_PORT}..."
while ! nc -z "$DATABASE_HOST" "$DATABASE_PORT"; do
  sleep 0.1
done
echo "PostgreSQL is available."

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting API in ${FASTAPI_ENV} mode..."

if [ "$FASTAPI_ENV" = "dev" ]; then
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir "$APP_DIR" --reload
else
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir "$APP_DIR"
fi
