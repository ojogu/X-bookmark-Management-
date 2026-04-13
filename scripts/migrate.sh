#!/bin/bash

cd "$(dirname "$0")/../backend"

MESSAGE="${1:-}"

if [ -z "$MESSAGE" ]; then
    echo "Usage: ./migrate.sh \"migration message\""
    exit 1
fi

echo "Generating migration: $MESSAGE"
alembic revision --autogenerate -m "$MESSAGE"

echo "Applying migration..."
alembic upgrade head