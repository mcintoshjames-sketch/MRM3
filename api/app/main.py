"""FastAPI application entry point."""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api import auth, users, roles, models, vendors, taxonomies, audit_logs, validation_workflow, validation_policies, workflow_sla, regions, model_regions, model_versions, model_delegates, model_change_taxonomy, model_types, methodology, dashboard, export_views, version_deployment_tasks, regional_compliance_report, analytics, saved_queries, model_hierarchy, model_dependencies, approver_roles, conditional_approval_rules, fry, map_applications, model_applications, overdue_commentary, overdue_revalidation_report, decommissioning, kpm, monitoring, recommendations, risk_assessment, qualitative_factors, scorecard, residual_risk_map, limitations, model_overlays, attestations, lob_units, kpi_report, irp, my_portfolio, exceptions, mrsa_review_policy, teams, tags, due_date_override
from app.core.database import get_db
from app.core.config import settings
from app.core.exception_detection import get_missing_closure_reason_codes

app = FastAPI(title="QMIS v0.1", version="0.1.0")

# CORS - uses environment-based origins from config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, tags=["users"])
app.include_router(roles.router, tags=["roles"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
app.include_router(regions.router, prefix="/regions", tags=["regions"])
app.include_router(model_regions.router, tags=["model-regions"])
app.include_router(model_versions.router, tags=["model-versions"])
app.include_router(model_delegates.router, tags=["model-delegates"])
app.include_router(model_change_taxonomy.router,
                   tags=["model-change-taxonomy"])
app.include_router(model_types.router, tags=["model-types"])
app.include_router(methodology.router, tags=["methodology-library"])
app.include_router(taxonomies.router, prefix="/taxonomies",
                   tags=["taxonomies"])
app.include_router(audit_logs.router, prefix="/audit-logs",
                   tags=["audit-logs"])
# Workflow-based validation endpoints
app.include_router(validation_workflow.router,
                   prefix="/validation-workflow", tags=["validation-workflow"])
# Validation policies endpoint
app.include_router(validation_policies.router,
                   prefix="/validation-workflow/policies", tags=["validation-policies"])
# Workflow SLA configuration
app.include_router(workflow_sla.router,
                   prefix="/workflow-sla", tags=["workflow-sla"])
# Export views for CSV exports
app.include_router(export_views.router,
                   prefix="/export-views", tags=["export-views"])
# Version deployment tasks for model owner ratification
app.include_router(version_deployment_tasks.router,
                   prefix="/deployment-tasks", tags=["deployment-tasks"])
# Regional compliance report
app.include_router(regional_compliance_report.router, tags=["reports"])
# Analytics
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
# Saved queries for analytics
app.include_router(saved_queries.router,
                   prefix="/saved-queries", tags=["saved-queries"])
# Model relationships (hierarchy and dependencies)
app.include_router(model_hierarchy.router, tags=["model-hierarchy"])
app.include_router(model_dependencies.router, tags=["model-dependencies"])
# Conditional model use approvals
app.include_router(approver_roles.router, tags=["additional-approvals"])
app.include_router(conditional_approval_rules.router, tags=["additional-approvals"])
# FRY 14 Reporting configuration
app.include_router(fry.router, tags=["fry-reporting"])
# MAP Applications (Managed Application Portfolio)
app.include_router(map_applications.router, tags=["map-applications"])
app.include_router(model_applications.router, tags=["model-applications"])
# Overdue revalidation commentary
app.include_router(overdue_commentary.router,
                   prefix="/validation-workflow", tags=["overdue-commentary"])
app.include_router(overdue_commentary.model_router,
                   prefix="/models", tags=["overdue-commentary"])
# Overdue revalidation report
app.include_router(overdue_revalidation_report.router, tags=["reports"])
# Due date overrides for validation scheduling
app.include_router(due_date_override.router,
                   prefix="/models", tags=["due-date-override"])
# Model decommissioning workflow
app.include_router(decommissioning.router, tags=["decommissioning"])
# KPM (Key Performance Metrics) library
app.include_router(kpm.router, tags=["kpm"])
# Monitoring Plans and Teams
app.include_router(monitoring.router, tags=["monitoring"])
# Model Recommendations
app.include_router(recommendations.router, tags=["recommendations"])
# Model Risk Assessment
app.include_router(risk_assessment.router, tags=["risk-assessment"])
# Qualitative Risk Factor Configuration (Admin)
app.include_router(qualitative_factors.router,
                   prefix="/risk-assessment/factors", tags=["risk-assessment"])
# Validation Scorecard
app.include_router(scorecard.router, prefix="/scorecard", tags=["scorecard"])
# Residual Risk Map Configuration
app.include_router(residual_risk_map.router, tags=["residual-risk-map"])
# Model Limitations
app.include_router(limitations.router, tags=["limitations"])
# Model Overlays
app.include_router(model_overlays.router, tags=["model-overlays"])
# Model Risk Attestations
app.include_router(attestations.router, prefix="/attestations", tags=["attestations"])
# LOB (Line of Business) Hierarchy
app.include_router(lob_units.router, prefix="/lob-units", tags=["lob-units"])
# Teams
app.include_router(teams.router, tags=["teams"])
# KPI Report
app.include_router(kpi_report.router, tags=["reports"])
# My Portfolio Report (for model owners)
app.include_router(my_portfolio.router, tags=["reports"])
# IRP (Independent Review Process) Management
app.include_router(irp.router, prefix="/irps", tags=["irps"])
# MRSA Review Policy and Exceptions
app.include_router(mrsa_review_policy.router, tags=["mrsa-review"])
# Model Exceptions
app.include_router(exceptions.router, prefix="/exceptions", tags=["exceptions"])
# Model Tags for categorization
app.include_router(tags.router, prefix="/tags", tags=["tags"])


@app.get("/")
def read_root():
    return {"message": "QMIS v0.1 API"}


@app.get("/health")
def healthcheck():
    """Lightweight liveness probe."""
    return {"status": "ok"}


@app.get("/ready")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe with DB connectivity check."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    missing_codes = get_missing_closure_reason_codes(db)
    if missing_codes:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Exception closure reasons missing",
                "missing_codes": missing_codes,
            },
        )
    return {"status": "ok", "checks": {"database": "ok", "exception_closure_reasons": "ok"}}


app.get("/healthz")(healthcheck)
app.get("/readyz")(readiness)
