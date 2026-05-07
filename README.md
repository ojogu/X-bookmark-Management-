# SaveStack

**Your personal bookmark library for X (formerly Twitter).**

SaveStack solves the problem of lost and disorganized bookmarks on X. When you save a post on X, it disappears into an unsearchable list with zero organization. SaveStack syncs your bookmarks into a personal library where you can search, filter, organize into folders, tag for categorization, and track what you've read.

---

## The Problem

X (Twitter) lets you bookmark posts, but:

- **No search** — Scroll endlessly to find something you saved last week
- **No folders or tags** — Everything is a flat, chronological list
- **No filtering** — Can't filter by read/unread, media type, or author
- **No offline access** — Requiring an internet connection every time

SaveStack gives you a personal, organized bookmark library with all of these features — automatically synced from your X account.

---

## Key Features

- **Automatic Sync** — Connect your X account via OAuth and bookmarks sync continuously in the background
- **Full-Text Search** — Instantly find saved content by post text, author name, or username
- **Folder Organization** — Create folders to categorize bookmarks your way
- **Tagging System** — Apply multiple tags to any bookmark for flexible organization
- **Read/Unread Tracking** — Mark bookmarks as read to track what you've reviewed
- **Multiple Sort Options** — Sort by date (newest/oldest) or alphabetically
- **Filter by Tags/Folders** — Narrow down to specific categories

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python + FastAPI |
| Frontend | React + TypeScript + Vite |
| Database | PostgreSQL (via SQLAlchemy async) |
| Task Queue | Celery + Redis |
| Observability | OpenTelemetry → Grafana / Tempo / Loki / Prometheus |
| External API | X API (Twitter/X API v2) |

**Why these choices?**

- **FastAPI** — Async-native for high I/O throughput with background workers
- **React + TypeScript** — Type-safe frontend with modern React patterns
- **Celery + Redis** — Proven pattern for background task scheduling and rate limiting
- **PostgreSQL** — Relational integrity for complex queries (folders, tags, bookmarks)
- **OpenTelemetry** — Structured observability from day one

---

## System Architecture

```
┌──────────────┐     ┌──────────────┐
│  X (Twitter) │────▶│  SaveStack  │
│     API      │     │   Backend   │
└──────────────┘     └──────┬─────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
        ┌─────▼──────┐            ┌──────▼──────┐
        │  Celery    │            │ PostgreSQL   │
        │  Workers  │            │  Database   │
        └───────────┘            └─────────────┘
```

**Flow:**

1. **User authenticates** via X OAuth → Tokens stored securely
2. **Celery workers** fetch bookmarks from X API (front sync for new, backfill for historical)
3. **Bookmarks persisted** to PostgreSQL with author, media, and metadata
4. **Frontend displays** via REST API → User searches, filters, organizes

For engineering deep-dives (sync architecture, production incidents, migrations), see the [`docs/`](docs/) directory.

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for local development without Docker)
- An X (Twitter) account (for OAuth)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/savestack.git
cd savestack

# 2. Set up environment variables
cp backend/.env.example backend/.env
# Edit .env with your credentials (X API keys, database URL, etc.)

# 3. Start all services with Docker Compose
docker-compose up --build
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | SaveStack web app |
| API | http://localhost:5000 | REST API endpoints |
| API Docs | http://localhost:5000/docs | Swagger / OpenAPI |
| Flower | http://localhost:5555 | Celery task monitoring |
| Grafana | http://localhost:3000 | Observability dashboards |

---

## Project Structure

```
savestack/
├── backend/
│   ├── src/
│   │   ├── v1/
│   │   │   ├── model/          # SQLAlchemy models (User, Bookmark, Post, etc.)
│   │   │   ├── route/          # API route handlers
│   │   │   ├── service/       # Business logic
│   │   │   └── schema/         # Pydantic request/response schemas
│   │   ├── celery/            # Celery tasks (sync, backfill)
│   │   └── utils/            # Shared utilities (DB, config, telemetry)
│   └── migrations/           # Alembic database migrations
├── frontend/
│   └── src/
│       ├── pages/             # Route pages
│       ├── components/        # React components
│       ├── api/              # API client
│       └── hooks/            # Custom React hooks
├── docs/                     # Engineering documentation
├── docker-compose.yml        # All services definition
└── README.md                # This file
```

---

## Development Commands

```bash
# Run linting
ruff check

# Type checking
mypy

# Run tests
pytest
```

---

## Deployment

Currently deployed via **Docker Compose** on a single VPS.

Services included:

- Backend API (FastAPI)
- Frontend (React static)
- Celery workers (sync tasks)
- Celery beat (scheduled tasks)
- PostgreSQL
- Redis
- Observability stack (Grafana, Tempo, Loki, Prometheus)
- OpenTelemetry Collector

---

## What's Saved vs. What's Lost

In building this, I encountered several real production challenges:

1. **X API Pagination** — X doesn't support timestamp filtering for bookmarks. Built a dual-state sync system: front sync fetches newest only, backfill handles historical via pagination tokens, tracking `front_watermark_id` to detect boundaries.

2. **Worker Memory** — Celery workers exceeded container memory (512MB). Resolved by increasing to 1GB and limiting concurrency to 2 workers.

3. **Task Accumulation** — Tasks retrying infinitely caused queue backup. Added `max_retries=3` and Redis-based per-user rate limiting (5 requests/60s).

For the full engineering story, see [`docs/`](docs/).

---

## Contact & License

- **Author:** Your Name
- **License:** Private — All rights reserved

For technical details on architecture, sync engine, and production incidents, see the [`docs/`](docs/) directory.