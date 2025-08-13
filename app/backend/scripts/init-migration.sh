#!/bin/bash

# Script to initialize database migrations
# This script runs before starting any backend services

set -e

echo "Starting database migration process..."

# Wait for database to be ready
while ! pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB > /dev/null 2>&1; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

echo "PostgreSQL is ready. Running migrations..."

# Run Alembic migrations
cd /app
python -m alembic upgrade head

echo "✅ Database migrations completed successfully!"