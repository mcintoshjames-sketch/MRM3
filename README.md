# MRM INV 3 - Minimal Starting Point

Barebones Model Risk Management system with just the essential framework and models table.

## Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.x, Alembic
- **Database:** PostgreSQL 15+
- **Frontend:** React 18 + TypeScript + Vite + TailwindCSS
- **Packaging:** Docker + docker-compose

## Quick Start

```bash
# Start all services
docker compose up --build

# Backend: http://localhost:8001
# Frontend: http://localhost:5174
# API docs: http://localhost:8001/docs
```

## Isolated Test Database

For Postgres-backed concurrency tests and performance benchmarks, use the
separate test container defined in `docker-compose.test.yml`.
See `docs/TESTING_POSTGRES.md` for setup, verification, and teardown steps.

## Default Login

- **Admin:** `admin@example.com` / `admin123`

## Features

- JWT authentication
- Basic RBAC (Admin, User roles)
- Models CRUD with minimal schema:
  - Model name
  - Description
  - Owner
  - Status
  - Created/updated timestamps

## Project Structure

```
mrm_inv_3/
├── api/                 # FastAPI backend
│   ├── app/
│   │   ├── api/        # Routes
│   │   ├── core/       # Config, security
│   │   ├── models/     # SQLAlchemy models
│   │   ├── schemas/    # Pydantic schemas
│   │   └── main.py
│   ├── alembic/        # Migrations
│   └── Dockerfile
├── web/                # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── main.tsx
│   └── Dockerfile
└── docker-compose.yml
```

## Extend This

This is a minimal starting point. Add features as needed:
- Additional tables (validations, approvals, etc.)
- More fields to models table
- Additional user roles
- File uploads
- Reports and dashboards
