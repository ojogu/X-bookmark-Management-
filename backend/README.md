# xfeeds API

## Overview
xfeeds: AI-Powered X Bookmarks Manager
xfeeds is an intelligent web application that transforms how users organize, discover, and interact with their X (formerly Twitter) bookmarks. 

This is achieved through AI-powered agents that understand, categorize, and enhance bookmarked content. The backend API service is built with Python using the FastAPI framework, leveraging OAuth 2.0 for secure authentication and Celery for efficient asynchronous processing of background tasks, docker for containerization.



## Features
- **Intelligent Organization**: Automatically categorizes bookmarks using AI understanding of content
- **Semantic Search**: Find bookmarks using natural language queries through the web app
- **Enhanced Productivity**: Transform bookmarks from a "black hole" into an intelligent knowledge base
- **Clean Architecture**: Backend-first design enables future frontend flexibility and potential API expansion


## Tools
- **FastAPI**: Serves a high-performance, asynchronous RESTful API.
- **SQLAlchemy**: Provides an asynchronous ORM for database interactions with PostgreSQL.
- **Celery**: Manages a distributed task queue for background jobs like fetching bookmarks.
- **Redis**: Acts as a message broker for Celery and a caching layer for OAuth sessions.
- **OAuth 2.0 (PKCE)**: Implements secure, delegated authentication with the X API.
- **JWT**: Handles stateless in-app user sessions using access and refresh tokens.
- **Alembic**: Manages database schema migrations.

## Getting Started
### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/ojogu/X-bookmark-Management-.git
    cd X-bookmark-Management-
    ```

2.  **Set Up Environment**
    Create a `.env` file in the root directory and populate it with the required variables (see the Environment Variables section below).

3.  **Install Dependencies**
    It is recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt 
    ```
    *Note: The project uses Poetry. If you have Poetry installed, you can use `poetry install`.*

4.  **Run Database Migrations**
    Ensure your `alembic.ini` is configured with the correct database URL.
    ```bash
    alembic upgrade head
    ```

5.  **Run the Application**
    ```bash
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    ```

6.  **Run Celery Workers**
    In separate terminals, start the Celery worker and the beat scheduler.
    ```bash
    # Terminal 1: Celery Worker
    celery -A src.celery.celery.bg_task worker -l info -Q fetch_user_id,fetch_user_bookmarks,default

    # Terminal 2: Celery Beat Scheduler
    celery -A src.celery.celery.bg_task beat --loglevel=info
    ```

### Environment Variables
Create a `.env` file in the project root and add the following variables:

| Variable               | Example                                                 | Description                                            |
| ---------------------- | ------------------------------------------------------- | ------------------------------------------------------ |
| `DATABASE_URL`         | `postgresql+asyncpg://user:password@localhost:5432/xfeeds` | The connection URL for your PostgreSQL database.       |
| `CLIENT_ID`            | `YOUR_TWITTER_CLIENT_ID`                                | Your X (Twitter) App's Client ID.                      |
| `CLIENT_SECRET`        | `YOUR_TWITTER_CLIENT_SECRET`                            | Your X (Twitter) App's Client Secret.                  |
| `API_KEY`              | `YOUR_TWITTER_API_KEY`                                  | Your X (Twitter) App's API Key.                        |
| `API_SECRET`           | `YOUR_TWITTER_API_SECRET`                               | Your X (Twitter) App's API Key Secret.                 |
| `REDIRECT_URI`         | `http://127.0.0.1:8000/auth/callback`                   | The callback URI configured in your X App settings.    |
| `REDIS_URL`            | `redis://localhost:6379/0`                              | The connection URL for your Redis instance.            |
| `JWT_SECRET_KEY`       | `a_very_secret_and_long_random_string`                  | Secret key for signing JWTs.                           |
| `JWT_ALGO`             | `HS256`                                                 | Algorithm used for JWT signing.                        |
| `ACCESS_TOKEN_EXPIRY`  | `900`                                                   | Expiry time for access tokens in seconds (e.g., 15 minutes). |
| `REFRESH_TOKEN_EXPIRY` | `7`                                                     | Expiry time for refresh tokens in days.                |
| `FRONTEND_URL`         | `http://localhost:3000`                                 | The base URL of your frontend application.             |
| `CELERY_BEAT_INTERVAL` | `30`                                                    | Interval in minutes for the Celery beat scheduler task. |

## API Documentation
### Base URL
`http://localhost:8000`

### Endpoints
#### GET /auth/login
Initiates the OAuth 2.0 authentication flow with X (Twitter).

**Request**:
No request body required.

**Response**:
`200 OK`
```json
{
  "url": "https://twitter.com/i/oauth2/authorize?response_type=code&client_id=...&redirect_uri=...&scope=...&state=...&code_challenge=...&code_challenge_method=S256"
}
```

**Errors**:
- `500 Internal Server Error`: If the authentication URL fails to generate.

---
#### GET /auth/callback
The callback endpoint that X (Twitter) redirects to after user authorization. It exchanges the authorization code for tokens, creates a user session, and redirects to the frontend.

**Request**:
This endpoint is not called directly. It receives `code` and `state` as query parameters from the X redirect.

**Response**:
`302 Found`
- A redirect to the frontend URL (`FRONTEND_URL`) with JWT `access-token` and `refresh-token` as query parameters.
- Example Redirect URL: `http://localhost:3000/dashboard?access-token=...&refresh-token=...`

**Errors**:
- `302 Found`: Redirects to a frontend error page (e.g., `http://localhost:3000/login?error=auth_failed`) if the callback processing fails.

---
#### GET /auth/refresh-token
Generates a new JWT access token using a valid refresh token.

**Request**:
- **Header**: `Authorization: Bearer <your_refresh_token>`

**Response**:
`200 OK`
```json
{
  "access_token": "new_jwt_access_token"
}
```

**Errors**:
- `401 Unauthorized`: If the refresh token is missing, invalid, or expired.

---
#### GET /twitter/user-info
Fetches the authenticated user's profile information from the X API.

**Request**:
- **Header**: `Authorization: Bearer <your_access_token>`

**Response**:
`200 OK`
```json
{
  "id": "2244994945",
  "username": "TwitterDev",
  "name": "Twitter Dev",
  "profile_image_url": "https://pbs.twimg.com/profile_images/...",
  "description": "The Real Twitter API. Tweets about API changes, events, and tools.",
  "followers_count": 645123,
  "following_count": 14,
  "tweet_count": 2758,
  "verified": true,
  "location": "127.0.0.1",
  "url": "https://t.co/...",
  "created_at": "2013-12-14T04:35:55.000Z"
}
```

**Errors**:
- `401 Unauthorized`: If the JWT access token is missing, invalid, or expired.
- `500 Internal Server Error`: If the request to the upstream X API fails.

---
#### GET /twitter/bookmarks
Fetches the authenticated user's bookmarks from the X API and stores them in the database.

**Request**:
- **Header**: `Authorization: Bearer <your_access_token>`
- **Query Parameters**:
  - `max_results` (optional, integer, default: 50): The maximum number of bookmarks to retrieve.

**Response**:
`200 OK`
```json
{
  "bookmarks": [
    {
      "internal_id": "user-uuid-string",
      "post": {
        "id": "1953057220632920535",
        "text": "If you're a software engineer who wants to upskill in system design, read these 12 articles: ↓ https://t.co/imiB4DNDxp",
        "author_id": "1344928554425987074",
        "created_at": "2025-08-06T11:35:02.000Z",
        "metrics": {
          "retweet_count": 382,
          "reply_count": 11,
          "like_count": 3594,
          "quote_count": 3,
          "bookmark_count": 7275,
          "impression_count": 224076
        },
        "lang": "en",
        "possibly_sensitive": false
      },
      "author": {
        "id": "1344928554425987074",
        "username": "Franc0Fernand0",
        "name": "Fernando 🇮🇹🇨🇭",
        "profile_image_url": "https://pbs.twimg.com/profile_images/..."
      }
    }
  ],
  "meta": {
    "result_count": 1,
    "next_token": "a_pagination_token_string"
  }
}
```

**Errors**:
- `401 Unauthorized`: If the JWT access token is missing, invalid, or expired.
- `404 Not Found`: If the user associated with the token does not exist in the database.
- `500 Internal Server Error`: If the request to the upstream X API fails or a database error occurs.