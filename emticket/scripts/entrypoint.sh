#!/usr/bin/env sh
set -e

echo "Waiting for database..."
while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 1
done
echo "Database is up."

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static..."
python manage.py collectstatic --noinput || true

echo "Starting app..."
exec "$@"