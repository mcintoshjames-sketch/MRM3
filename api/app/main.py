"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, models, vendors, taxonomies, audit_logs, validations, validation_workflow, workflow_sla, regions, model_regions, model_versions, model_delegates, model_change_taxonomy, dashboard, export_views, version_deployment_tasks, regional_compliance_report, analytics, saved_queries

app = FastAPI(title="MRM System v3", version="3.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
app.include_router(regions.router, prefix="/regions", tags=["regions"])
app.include_router(model_regions.router, tags=["model-regions"])
app.include_router(model_versions.router, tags=["model-versions"])
app.include_router(model_delegates.router, tags=["model-delegates"])
app.include_router(model_change_taxonomy.router,
                   tags=["model-change-taxonomy"])
app.include_router(taxonomies.router, prefix="/taxonomies",
                   tags=["taxonomies"])
app.include_router(audit_logs.router, prefix="/audit-logs",
                   tags=["audit-logs"])
# Legacy validation endpoints (deprecated)
app.include_router(validations.router, prefix="/validations",
                   tags=["validations-legacy"])
# New workflow-based validation endpoints
app.include_router(validation_workflow.router,
                   prefix="/validation-workflow", tags=["validation-workflow"])
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
app.include_router(saved_queries.router, prefix="/saved-queries", tags=["saved-queries"])


@app.get("/")
def read_root():
    return {"message": "MRM System v3 API"}
