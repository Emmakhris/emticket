#!/usr/bin/env sh
set -e

echo "Starting Celery beat..."
exec celery -A emticket beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
