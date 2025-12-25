# Remote Server Access Guide

Quick reference for connecting to the MRM production server via Cloudflare Access.

## Connection Details

| Property | Value |
|----------|-------|
| **SSH Host** | `ssh.mrmqmistest.org` |
| **SSH User** | `mrm-admin` |
| **Auth Methods** | Service Token (automated) or Browser Login (interactive) |
| **Public URL** | https://app.mrmqmistest.org |
| **App Directory** | `/opt/mrm` |

## Prerequisites

**cloudflared** must be installed:
```bash
brew install cloudflared
```

---

## Authentication Methods

### Method 1: Service Token (Recommended for Automation)

Service tokens allow non-interactive SSH access without browser login. Ideal for Claude Code and automated deployments.

#### Setup (One-Time)

1. **Credentials are stored in** `~/.cloudflare/mrm-service-token`:
   ```
   CF_ACCESS_CLIENT_ID=<client-id>.access
   CF_ACCESS_CLIENT_SECRET=<secret>
   ```

   > ⚠️ **Security Note:** This file is parsed line-by-line. Only include the two
   > variable definitions shown above. Do not add shell commands, comments, or
   > any other content.

2. **SSH config** (`~/.ssh/config`) uses service token:
   ```
   Host ssh.mrmqmistest.org
     User mrm-admin
     ProxyCommand sh -c 'CF_ACCESS_CLIENT_ID=$(grep "^CF_ACCESS_CLIENT_ID=" ~/.cloudflare/mrm-service-token | cut -d= -f2) CF_ACCESS_CLIENT_SECRET=$(grep "^CF_ACCESS_CLIENT_SECRET=" ~/.cloudflare/mrm-service-token | cut -d= -f2) cloudflared access ssh --hostname %h --service-token-id "$CF_ACCESS_CLIENT_ID" --service-token-secret "$CF_ACCESS_CLIENT_SECRET"'
   ```

   > **Note:** This command safely parses the token file line-by-line rather than executing it.
   > Ensure `cloudflared` is in your PATH (install via `brew install cloudflared`).

#### Usage

Just SSH directly - no browser authentication required:
```bash
ssh mrm-admin@ssh.mrmqmistest.org
```

#### Security Notes
- Credentials stored in `~/.cloudflare/` with 600 permissions (outside repo)
- Never commit service token credentials to git
- Service tokens can be revoked in Cloudflare Access dashboard

#### Token Lifecycle Management

**Rotation Policy:**
- **Recommended rotation interval:** 90 days
- Rotate tokens immediately when:
  - Personnel with access leave the team
  - A potential compromise is suspected
  - The token is accidentally exposed (logs, screenshots, etc.)

**Revoking a Service Token:**
1. Log in to the [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com/)
2. Navigate to: **Access** → **Service Auth** → **Service Tokens**
3. Find the token (e.g., `mrm-ssh-service-token`)
4. Click **Revoke** to immediately invalidate all sessions
5. Generate a new token and update `~/.cloudflare/mrm-service-token` on all machines

**Scope Restrictions:**
- The service token should be limited to only the SSH application (`ssh.mrmqmistest.org`)
- Consider IP restrictions if your team uses a VPN or has static IPs

**File Permissions:**
Ensure the token file has restricted permissions:
```bash
chmod 600 ~/.cloudflare/mrm-service-token
ls -la ~/.cloudflare/mrm-service-token  # Should show: -rw-------
```

---

### Method 2: Browser Login (Interactive)

For users without service token access.

#### Step 1: Authenticate with Cloudflare Access

```bash
cloudflared access login https://ssh.mrmqmistest.org
```

This opens a browser window. Complete the authentication (email/SSO).

#### Step 2: SSH to the Server

```bash
ssh mrm-admin@ssh.mrmqmistest.org
```

The token is cached in `~/.cloudflared/` until it expires.

---

## Quick Commands

### Health Check
```bash
ssh mrm-admin@ssh.mrmqmistest.org "uptime && cd /opt/mrm && sudo docker compose -f docker-compose.prod.yml ps"
```

### View Container Status
```bash
ssh mrm-admin@ssh.mrmqmistest.org "cd /opt/mrm && sudo docker compose -f docker-compose.prod.yml ps"
```

### View Recent Logs
```bash
ssh mrm-admin@ssh.mrmqmistest.org "cd /opt/mrm && sudo docker compose -f docker-compose.prod.yml logs --tail=50"
```

---

## Common Deployment Operations

### Automated Deployment (Recommended)

Use the `deploy.sh` script from your local machine to commit, push, and deploy in one step:

```bash
# Full flow: commit + push + deploy (interactive)
./scripts/deploy.sh

# With commit message
./scripts/deploy.sh "fix: update validation workflow"

# Check status only
./scripts/deploy.sh --status

# Deploy to server only (skip git)
./scripts/deploy.sh --prod-only
```

The script handles SSH connection, git pull, Docker rebuild, and health verification automatically.

## Production Safety Checklist

- Ensure `ENVIRONMENT=production` is set in `/opt/mrm/docker-compose.prod.yml`.
- Do not run `python -m app.seed` in production unless `SEED_ADMIN_PASSWORD` is set and `SEED_DEMO_DATA=false`.
- Avoid mirroring local databases into production; if a restore is required, exclude `users`/auth tables and rotate credentials immediately.
- After any restore, reset default/demo accounts (`admin@example.com`, `validator@example.com`, `user@example.com`, `globalapprover@example.com`, `john.smith@contoso.com`).

### Manual Server Commands

If you need to run commands directly on the server after SSH:

```bash
# Navigate to app directory
cd /opt/mrm

# Check container status
sudo docker compose -f docker-compose.prod.yml ps

# View logs (all containers)
sudo docker compose -f docker-compose.prod.yml logs --tail=100

# View specific container logs
sudo docker compose -f docker-compose.prod.yml logs api --tail=100
sudo docker compose -f docker-compose.prod.yml logs web --tail=100

# Restart all containers
sudo docker compose -f docker-compose.prod.yml restart

# Pull latest code and rebuild
git pull origin main
sudo docker compose -f docker-compose.prod.yml up -d --build

# Run database migrations
sudo docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## Troubleshooting

### "websocket: bad handshake" or Authentication Errors

If using service token, verify credentials are correct:
```bash
cat ~/.cloudflare/mrm-service-token
```

If using browser login, re-authenticate:
```bash
cloudflared access login https://ssh.mrmqmistest.org
```

### "Connection timed out during banner exchange"

The Cloudflare tunnel may be down or the token expired. Try:
1. Re-authenticate with browser login
2. Check Cloudflare Access dashboard for service health
3. Verify cloudflared is installed: `which cloudflared`

### Public URL returning 502 Bad Gateway

SSH into the server and check/restart containers:
```bash
ssh mrm-admin@ssh.mrmqmistest.org
cd /opt/mrm
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs --tail=50
sudo docker compose -f docker-compose.prod.yml restart
```

### Token/Credential Storage Locations

| Type | Location |
|------|----------|
| Service Token | `~/.cloudflare/mrm-service-token` |
| Browser Token | `~/.cloudflared/ssh.mrmqmistest.org-*-token` |

---

## See Also

- [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md) - Full deployment and management guide
- [api/.env.example](api/.env.example) - Production environment variables template
