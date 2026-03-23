#!/bin/bash

set -e

echo "── Pulling latest changes ──────────────────────────"
# git pull

echo "── Taking down running containers ──────────────────"
docker compose down

echo "── Building frontend ───────────────────────────────"
cd frontend && npm run build && cd ..

echo "── Rebuilding frontend image ───────────────────────"
docker compose build frontend

echo "── Restarting all containers ───────────────────"
docker compose up -d 

echo "── Done. SaveStack is live. ────────────────────────"