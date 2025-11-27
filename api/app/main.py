"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, models, vendors, taxonomies, audit_logs, validation_workflow, validation_policies, workflow_sla, regions, model_regions, model_versions, model_delegates, model_change_taxonomy, model_types, dashboard, export_views, version_deployment_tasks, regional_compliance_report, analytics, saved_queries, model_hierarchy, model_dependencies, approver_roles, conditional_approval_rules, fry, map_applications, model_applications, overdue_commentary, overdue_revalidation_report, decommissioning, kpm, monitoring

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
app.include_router(model_types.router, tags=["model-types"])
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
# Model decommissioning workflow
app.include_router(decommissioning.router, tags=["decommissioning"])
# KPM (Key Performance Metrics) library
app.include_router(kpm.router, tags=["kpm"])
# Monitoring Plans and Teams
app.include_router(monitoring.router, tags=["monitoring"])


@app.get("/")
def read_root():
    return {"message": "MRM System v3 API"}
