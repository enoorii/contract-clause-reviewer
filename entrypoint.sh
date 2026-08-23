#!/bin/sh
set -e

# Ensure required directories exist with proper permissions
echo "Ensuring directories exist..."
mkdir -p /app/reports /app/logs
chown -R appuser:appgroup /app/reports /app/logs
chmod 750 /app/reports /app/logs

# Run migrations (only needed for API container, but safe to run in both)

if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    /app/.venv/bin/alembic upgrade head
fi

echo "Starting application as appuser..."
exec gosu appuser "$@"
