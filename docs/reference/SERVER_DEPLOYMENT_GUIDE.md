# MRM Server Deployment & Management Guide

This guide documents how to deploy, update, and manage the MRM application on the production server.

## Server Details

| Property | Value |
|----------|-------|
| **SSH Host** | ssh.mrmqmistest.org |
| **SSH User** | mrm-admin |
| **Auth** | Cloudflare Access (service token for automation or browser login) |
| **OS** | Ubuntu 24.04 LTS |
| **Public URL** | https://app.mrmqmistest.org |
| **Access Method** | Cloudflare Tunnel (SSH + HTTP) |

## SSH Connection

```bash
ssh mrm-admin@ssh.mrmqmistest.org
```

See REMOTE_ACCESS.md for Cloudflare Access setup (service token / browser login).

## Architecture Overview

```
Internet → Cloudflare Tunnel → Nginx (port 80) → Docker Containers
                                    │
                                    ├── / → web container (port 3000)
                                    │       React frontend served by nginx
                                    │
                                    └── /api/ → api container (port 8001)
                                                FastAPI backend
                                                    │
                                                    └── db container (PostgreSQL)
```

## Directory Structure (on server)

```
/opt/mrm/                          # Application root
├── api/                           # FastAPI backend
│   ├── app/                       # Application code
│   ├── alembic/                   # Database migrations
│   └── Dockerfile                 # Backend container config
├── web/                           # React frontend
│   ├── src/                       # Source code
│   └── Dockerfile.prod            # Production frontend build
├── docker-compose.prod.yml        # Production Docker config
└── ...

/etc/nginx/sites-available/mrm     # Nginx reverse proxy config
```

---

## Common Operations

### Deploying Code Updates

Preferred: use the repo deployment script from your local machine (repeatable and includes health checks).

```bash
# Full flow (commit + push + deploy)
./scripts/deploy.sh

# Deploy to prod only (skip git operations)
./scripts/deploy.sh --prod-only
```

The deployment will fail fast if `/opt/mrm/.env.prod` is missing. Ensure the production env file exists and is locked down (mode 600, root-owned).

Fallback/manual deployment (if needed):

```bash
# 1. SSH into server
ssh mrm-admin@ssh.mrmqmistest.org

# 2. Navigate to app directory
cd /opt/mrm

# 3. Pull latest changes
git pull origin main

# 4. Rebuild and restart containers
# For backend changes:
sudo docker compose -f docker-compose.prod.yml up -d --build api

# For frontend changes:
sudo docker compose -f docker-compose.prod.yml up -d --build web

# For all changes:
sudo docker compose -f docker-compose.prod.yml up -d --build
```

### Running Database Migrations

After adding new Alembic migrations:

```bash
# SSH into server, then:
cd /opt/mrm
sudo docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Viewing Logs

```bash
# All container logs
sudo docker compose -f docker-compose.prod.yml logs

# Follow logs in real-time
sudo docker compose -f docker-compose.prod.yml logs -f

# Specific container logs
sudo docker compose -f docker-compose.prod.yml logs api
sudo docker compose -f docker-compose.prod.yml logs web
sudo docker compose -f docker-compose.prod.yml logs db

# Last 100 lines
sudo docker compose -f docker-compose.prod.yml logs --tail=100 api
```

### Container Management

```bash
# Check container status
sudo docker compose -f docker-compose.prod.yml ps

# Restart all containers
sudo docker compose -f docker-compose.prod.yml restart

# Restart specific container
sudo docker compose -f docker-compose.prod.yml restart api

# Stop all containers
sudo docker compose -f docker-compose.prod.yml down

# Start all containers
sudo docker compose -f docker-compose.prod.yml up -d

# Full rebuild (use after major changes)
sudo docker compose -f docker-compose.prod.yml down
sudo docker compose -f docker-compose.prod.yml up -d --build
```

### Database Operations

```bash
# Connect to PostgreSQL
sudo docker compose -f docker-compose.prod.yml exec db psql -U mrm -d mrm

# Create database backup (recommended: custom format)
sudo docker compose -f docker-compose.prod.yml exec -T db pg_dump -U mrm -d mrm -Fc > /tmp/mrm_backup_$(date +%Y%m%d_%H%M%S).dump

# Create database backup (plain SQL)
sudo docker compose -f docker-compose.prod.yml exec -T db pg_dump -U mrm -d mrm > /tmp/mrm_backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
cat backup_file.sql | sudo docker compose -f docker-compose.prod.yml exec -T db psql -U mrm -d mrm

# Run seed script (WARNING: may reset data)
sudo docker compose -f docker-compose.prod.yml exec api python -m app.seed
```

### Mirroring Dev → Production Database (preserve passwords)

Preferred: run the mirror script from your local machine:

```bash
./scripts/mirror_to_prod.sh
```

What it does:
- Dumps the local dev DB.
- Backs up production user password hashes to a CSV.
- Restores the dev dump into production.
- Restores production password hashes (users keep their prod passwords).
- Verifies services (expects HTTP 200 from frontend and API).

Recommended safety step: take a full production DB dump before mirroring (for rollback).

### Nginx Management

```bash
# Test nginx configuration
sudo nginx -t

# Reload nginx (after config changes)
sudo systemctl reload nginx

# Restart nginx
sudo systemctl restart nginx

# Check nginx status
sudo systemctl status nginx

# View nginx error logs
sudo tail -f /var/log/nginx/error.log
```

---

## Configuration Files

### docker-compose.prod.yml

Location: `/opt/mrm/docker-compose.prod.yml`

Contains:
- PostgreSQL database configuration
- API backend configuration
- Web frontend configuration
- Container port mappings (internal only - 127.0.0.1)

Production secrets are NOT stored in this file.

- `docker-compose.prod.yml` is tracked in git.
- Secrets are loaded via `env_file: .env.prod`.

### /opt/mrm/.env.prod (Production secrets)

Location: `/opt/mrm/.env.prod`

Requirements:
- Must exist on the server before deployment.
- Must not be committed to git.
- Permissions should be restricted (recommended: `600`, owned by `root:root`).

Expected variables (example shape; values are secrets):
```
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...

DATABASE_URL=postgresql://...@db:5432/...
SECRET_KEY=...
ENVIRONMENT=production
CORS_ORIGINS=https://app.mrmqmistest.org,https://mrmqmistest.org
```

### Nginx Configuration

Location: `/etc/nginx/sites-available/mrm`

Routes:
- `/` → Frontend container (port 3000)
- `/api/` → API container (port 8001) with path rewrite
- `/docs` → API documentation
- `/openapi.json` → OpenAPI schema

To edit:
```bash
sudo nano /etc/nginx/sites-available/mrm
sudo nginx -t
sudo systemctl reload nginx
```

### Frontend Environment

The frontend uses `VITE_API_URL=/api` (set during Docker build) to route API calls through the nginx proxy.

---

## Troubleshooting

### Container won't start

```bash
# Check container logs
sudo docker compose -f docker-compose.prod.yml logs api

# Check if port is in use
sudo lsof -i :8001
sudo lsof -i :3000

# Force rebuild
sudo docker compose -f docker-compose.prod.yml up -d --build --force-recreate
```

### Database connection issues

```bash
# Check if db container is healthy
sudo docker compose -f docker-compose.prod.yml ps db

# Check database logs
sudo docker compose -f docker-compose.prod.yml logs db

# Verify database is accepting connections
sudo docker compose -f docker-compose.prod.yml exec db pg_isready -U mrm
```

### API returning 502 Bad Gateway

1. Check if API container is running: `sudo docker compose -f docker-compose.prod.yml ps api`
2. Check API logs: `sudo docker compose -f docker-compose.prod.yml logs api`
3. Restart API: `sudo docker compose -f docker-compose.prod.yml restart api`

### Frontend not loading / stale content

```bash
# Rebuild frontend container
sudo docker compose -f docker-compose.prod.yml up -d --build web

# Clear browser cache or use incognito mode
```

### Migration errors

```bash
# Check current migration state
sudo docker compose -f docker-compose.prod.yml exec api alembic current

# View migration history
sudo docker compose -f docker-compose.prod.yml exec api alembic history

# Rollback one migration
sudo docker compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

---

## Security Notes

- SSH uses key-only authentication (password auth disabled)
- UFW firewall allows only ports 22 (SSH) and 80 (HTTP)
- Cloudflare Tunnel provides HTTPS termination
- Docker containers bind to 127.0.0.1 (not exposed externally)
- Database credentials stored in docker-compose.prod.yml (not in repo)

## Initial Deployment Steps (Reference)

If setting up a new server from scratch:

1. **Install Docker**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-plugin
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

2. **Clone repository**:
   ```bash
   sudo mkdir -p /opt/mrm
   sudo chown $USER:$USER /opt/mrm
   git clone https://github.com/mcintoshjames-sketch/MRM3.git /opt/mrm
   ```

3. **Create production config**:
   - Create `docker-compose.prod.yml` with secure passwords
   - Create `web/Dockerfile.prod` for production build

4. **Configure Nginx**:
   - Create `/etc/nginx/sites-available/mrm`
   - Link: `sudo ln -s /etc/nginx/sites-available/mrm /etc/nginx/sites-enabled/`
   - Remove default: `sudo rm /etc/nginx/sites-enabled/default`
   - Test and reload: `sudo nginx -t && sudo systemctl reload nginx`

5. **Build and start**:
   ```bash
   cd /opt/mrm
   sudo docker compose -f docker-compose.prod.yml up -d --build
   ```

6. **Run migrations**:
   ```bash
   sudo docker compose -f docker-compose.prod.yml exec api alembic upgrade head
   ```

7. **Seed database**:
   ```bash
   sudo docker compose -f docker-compose.prod.yml exec api python -m app.seed
   ```

---

## Default Credentials

After initial deployment with seed data:

- **Admin**: admin@example.com / admin123

**Note**: Change these credentials after deployment or disable test accounts.
