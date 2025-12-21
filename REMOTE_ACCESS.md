# Remote Server Access Guide

Quick reference for connecting to the MRM production server via Cloudflare Access.

## Connection Details

| Property | Value |
|----------|-------|
| **SSH Host** | `ssh.mrmqmistest.org` |
| **SSH User** | `mrm-admin` |
| **Auth Method** | Cloudflare Access (browser-based) + SSH key |
| **Public URL** | https://app.mrmqmistest.org |
| **Internal IP** | 192.168.0.67 (not accessible remotely) |

## Prerequisites

1. **cloudflared** must be installed:
   ```bash
   brew install cloudflared
   ```

2. **SSH config** must include the Cloudflare proxy (already configured):
   ```
   # ~/.ssh/config
   Host ssh.mrmqmistest.org
     User mrm-admin
     ProxyCommand /opt/homebrew/bin/cloudflared access ssh --hostname %h
   ```

## How to Connect

### Step 1: Authenticate with Cloudflare Access

Run this command to get a fresh authentication token:

```bash
cloudflared access login https://ssh.mrmqmistest.org
```

This opens a browser window. Complete the authentication (email/SSO).

### Step 2: SSH to the Server

```bash
ssh mrm-admin@ssh.mrmqmistest.org
```

The token is cached in `~/.cloudflared/` so subsequent connections work without re-authenticating (until the token expires).

## Quick Health Check

```bash
ssh mrm-admin@ssh.mrmqmistest.org "uptime && cd /opt/mrm && sudo docker compose -f docker-compose.prod.yml ps"
```

## Common Commands (on server)

```bash
# Navigate to app directory
cd /opt/mrm

# Check container status
sudo docker compose -f docker-compose.prod.yml ps

# View logs
sudo docker compose -f docker-compose.prod.yml logs --tail=100

# Restart all containers
sudo docker compose -f docker-compose.prod.yml restart

# Pull latest code and rebuild
git pull origin main
sudo docker compose -f docker-compose.prod.yml up -d --build

# Run database migrations
sudo docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

## Troubleshooting

### "Connection timed out during banner exchange"

The Cloudflare Access token may be expired or missing. Re-authenticate:

```bash
cloudflared access login https://ssh.mrmqmistest.org
```

### Public URL returning 502 Bad Gateway

SSH into the server and check/restart containers:

```bash
ssh mrm-admin@ssh.mrmqmistest.org
cd /opt/mrm
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs --tail=50
sudo docker compose -f docker-compose.prod.yml restart
```

### Token Storage Location

Cloudflare Access tokens are stored in:
```
~/.cloudflared/ssh.mrmqmistest.org-*-token
```

## See Also

- [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md) - Full deployment and management guide
