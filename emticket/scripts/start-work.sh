#!/usr/bin/env sh
set -e

echo "Starting Celery worker..."
exec celery -A emticket worker -l INFO --concurrency=2
