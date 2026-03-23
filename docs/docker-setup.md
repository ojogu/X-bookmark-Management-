# SaveStack — Dockerized Nginx Setup

A reference for running SaveStack with Nginx inside Docker, proxying to a React frontend and a FastAPI backend.

---

## Repository Structure

```
savestack/
├── backend/
│   ├── Dockerfile
│   ├── .env
│   └── ...
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── ...
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
│       └── savestack.conf
└── docker-compose.yml
```

---

## How It Works

```
Browser
  → Nginx container (:80 / :443)
      → /api/*   →  backend container (:5000)
      → /*       →  frontend container (:80, static files via Nginx)
```

- The **Nginx container** is the only service exposed to the internet (ports 80 and 443).
- The **frontend container** builds the React app and serves static files via its own internal Nginx.
- The **backend container** runs FastAPI on port 5000, reachable only inside Docker.
- SSL certificates from Certbot on the VPS are mounted into the Nginx container as a read-only volume.

---

## File Reference

### `frontend/Dockerfile`

Multi-stage build. The `dev` stage runs Vite dev server. The `prod` stage builds static files and serves them with Nginx.

```dockerfile
# dev stage
FROM node:20-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm install --legacy-peer-deps
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

# prod stage
FROM nginx:alpine AS prod
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### `frontend/nginx.conf`

Internal Nginx config inside the frontend container. Handles SPA routing and proxies `/api/` to the backend.

```nginx
server {
    listen 80;

    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback — all routes serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to FastAPI
    location /api/ {
        proxy_pass http://backend:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### `nginx/nginx.conf`

Main Nginx config for the outer Nginx container.

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    include /etc/nginx/conf.d/*.conf;
}
```

### `nginx/conf.d/savestack.conf`

Virtual host config. Redirects HTTP to HTTPS, terminates SSL, and routes traffic.

```nginx
upstream backend {
    server backend:5000;
}

upstream frontend {
    server frontend:80;
}

# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name savestack.ojogulabs.xyz;
    return 301 https://$host$request_uri;
}

# HTTPS — main entry point
server {
    listen 443 ssl;
    server_name savestack.ojogulabs.xyz;

    ssl_certificate /etc/letsencrypt/live/savestack.ojogulabs.xyz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/savestack.ojogulabs.xyz/privkey.pem;

    # API traffic → FastAPI
    location /api/ {
        proxy_pass http://backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Everything else → React frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### `docker-compose.yml` (relevant services)

```yaml
networks:
  app:
    driver: bridge

services:

  frontend:
    build:
      context: ./frontend
      target: prod       # use 'dev' for local development
    networks:
      - app

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    networks:
      - app
      - observability    # also on observability network for LGTM stack

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro   # Certbot certs from VPS
    depends_on:
      - frontend
      - backend
    networks:
      - app
```

---

## Networks

| Network | Purpose |
|---|---|
| `app` | Frontend, backend, and Nginx can talk to each other |
| `observability` | Backend + LGTM stack (Loki, Tempo, Prometheus, Grafana) |

Services not on the `app` network (e.g. Redis, RabbitMQ, otel-collector) are not reachable from Nginx — intentional.

---

## SSL Certificates

Certificates are issued by Certbot on the VPS and mounted into the Nginx container as read-only:

```yaml
- /etc/letsencrypt:/etc/letsencrypt:ro
```

To renew certificates, run on the VPS host (not inside Docker):

```bash
certbot renew
docker compose restart nginx
```

---

## Common Commands

```bash
# Build and start everything
docker compose up -d --build

# Start only frontend + nginx (for frontend work)
docker compose up frontend nginx

# Rebuild frontend after code changes
docker compose build frontend
docker compose up -d frontend

# View Nginx logs
docker compose logs nginx

# View frontend logs
docker compose logs frontend

# Restart Nginx after config change
docker compose restart nginx
```

---

## Dev vs Prod

| | Dev | Prod |
|---|---|---|
| Frontend | Vite dev server (`target: dev`) | Static build served by Nginx (`target: prod`) |
| Port | 5173 exposed directly | 80/443 via Nginx container |
| Hot reload | Yes | No |
| SSL | No | Yes (Certbot certs mounted) |

To switch between dev and prod, change `target` in the `frontend` service in `docker-compose.yml`.

---

## Troubleshooting

**Nginx can't reach backend** — confirm both are on the `app` network. Service names (`backend`, `frontend`) are used as hostnames inside Docker.

**SSL cert not found** — confirm Certbot has issued certs for `savestack.ojogulabs.xyz` on the VPS before starting the Nginx container. Check `/etc/letsencrypt/live/` on the host.

**Frontend shows blank page** — likely a SPA routing issue. Confirm `try_files $uri $uri/ /index.html` is in `frontend/nginx.conf`.

**API calls returning 502** — backend container may not be ready. Check `docker compose logs backend`.