#!/bin/sh
set -e

DATABASE_HOST=${DATABASE_HOST:-db}
DATABASE_PORT=${DATABASE_PORT:-5432}
APP_DIR=${APP_DIR:-server}
FASTAPI_ENV=${FASTAPI_ENV:-prod}

echo "Waiting for PostgreSQL DNS at ${DATABASE_HOST}..."
until getent hosts "$DATABASE_HOST" >/dev/null 2>&1; do
  sleep 1
done

echo "Waiting for PostgreSQL at ${DATABASE_HOST}:${DATABASE_PORT}..."
until nc -z "$DATABASE_HOST" "$DATABASE_PORT"; do
  sleep 1
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
