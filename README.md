# MRM Inventory System

Model Risk Management (MRM) inventory system for cataloging, validating, and governing enterprise models. Built with FastAPI, React/TypeScript, and PostgreSQL.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.x, Alembic, JWT auth
- **Frontend:** React 18 + TypeScript + Vite + TailwindCSS
- **Database:** PostgreSQL 15+
- **Packaging:** Docker + docker-compose

## Quick Start

```bash
# Start all services
docker compose up --build

# Backend: http://localhost:8001
# Frontend: http://localhost:5174
# API docs: http://localhost:8001/docs
```

## Default Login

- **Admin:** `admin@example.com` / `admin123`

## Core Features

### Model Inventory
- Model cataloging with owner, developer, vendor relationships
- Risk tier classification and regulatory categories
- Model versioning with change type tracking
- Parent-child hierarchy and data flow dependencies (DAG-enforced)
- Regional deployment tracking with per-region approvals
- Teams and LOB (Line of Business) hierarchy

### Validation Workflow
- Full lifecycle: Intake → Planning → In Progress → Review → Pending Approval → Approved
- Validator assignments with independence checks
- Validation plans with configurable components
- Scorecard rating system with weighted criteria
- Conditional approvals (committee/role-based)
- SLA tracking and compliance reporting

### Performance Monitoring
- Monitoring plans with KPM (Key Performance Metrics) library
- Recurring cycles (Monthly/Quarterly/Semi-Annual/Annual)
- Threshold breach tracking (Yellow/Red)
- PDF report generation

### Recommendations & Findings
- Action plans and rebuttals
- Closure workflow with evidence
- Priority configuration with regional overrides

### Additional Modules
- **Attestation**: Cycles, scheduling rules, bulk submission
- **Decommissioning**: Two-stage approval workflow with gap analysis
- **Risk Assessment**: Qualitative/quantitative scoring, inherent risk matrix
- **Model Limitations**: Critical limitations tracking and retirement
- **Model Overlays**: Underperformance overlays with effectiveness tracking
- **Exceptions**: Detection and workflow management
- **IRP**: Independent Review Process for MRSA governance
- **Tags**: Flexible model categorization system

### Reporting & Analytics
- KPI Report (23 metrics across inventory, validation, monitoring, governance)
- Regional compliance, deviation trends, overdue revalidation
- Critical limitations, name changes, model tags reports
- My Portfolio report with PDF export
- Custom analytics with saved queries

## User Roles

| Role | Access |
|------|--------|
| Admin | Full system access |
| Validator | Validation workflow management |
| Global Approver | Cross-region approvals |
| Regional Approver | Region-specific approvals |
| User | Model owner/contributor access |

## Project Structure

```
mrm_inv_3/
├── api/                  # FastAPI backend
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Config, security, dependencies
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── seed.py       # Database seeding
│   ├── alembic/          # Database migrations
│   └── Dockerfile
├── web/                  # React frontend
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Page components
│   │   ├── contexts/     # React contexts (auth)
│   │   └── api/          # Axios client
│   └── Dockerfile
├── docs/                 # Documentation
│   ├── plans/            # Implementation plans
│   ├── analysis/         # Audit reports, analysis
│   ├── reference/        # API docs, data dictionaries
│   ├── assets/           # Images, diagrams
│   └── USER_GUIDE_*.md   # User guides by module
├── scripts/              # Deployment and utility scripts
└── docker-compose.yml
```

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed system architecture, data models, and API reference
- **[CLAUDE.md](CLAUDE.md)** - Development guidelines and common commands
- **[REMOTE_ACCESS.md](REMOTE_ACCESS.md)** - Production deployment and SSH access
- **[REGRESSION_TESTS.md](REGRESSION_TESTS.md)** - Test coverage and testing workflow
- **[docs/](docs/)** - User guides, plans, and reference documentation

## Testing

```bash
# Backend tests (pytest)
cd api && python -m pytest

# Frontend type checking
cd web && npx tsc --noEmit

# Isolated Postgres tests
# See docs/reference/TESTING_POSTGRES.md
```

## Production Deployment

```bash
# Deploy to production (interactive)
./scripts/deploy.sh

# Or with custom commit message
./scripts/deploy.sh "fix: resolve validation workflow bug"
```

See [REMOTE_ACCESS.md](REMOTE_ACCESS.md) for SSH configuration and server details.
