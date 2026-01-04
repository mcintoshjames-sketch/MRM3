"""
Regional Deployment & Compliance Report API

This endpoint generates a regulatory report showing:
- Models deployed in each region
- Version numbers deployed
- Validation status for those versions
- Regional approval status (region-specific)

This report fully answers the regulatory question:
"Show me all models deployed in region X, with deployed version,
validation status, and regional approval status for that version."

Key Features:
- Region-specific approval tracking via validation_approvals.region_id
- Distinguishes between Global and Regional approvals via approval_type
- Accurate mapping of which approver approved for which region
- Compliance flags for deployment status
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case, desc
from sqlalchemy.orm import Session, joinedload, aliased
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model import Model
from app.models.region import Region
from app.models.model_region import ModelRegion
from app.models.model_version import ModelVersion
from app.models.validation import ValidationRequest, ValidationApproval, validation_request_regions
from app.models.taxonomy import TaxonomyValue
from app.core.team_utils import get_models_team_map
from app.models.team import Team

router = APIRouter(prefix="/regional-compliance-report", tags=["Reports"])


class RegionalDeploymentRecord(BaseModel):
    """Single record in the regional deployment report."""
    # Region Information
    region_code: str = Field(..., description="Region code (e.g., 'US', 'EU')")
    region_name: str = Field(..., description="Full region name")
    requires_regional_approval: bool = Field(..., description="Does this region require regional approval?")

    # Model Information
    model_id: int
    model_name: str

    # Deployment Information
    deployed_version: Optional[str] = Field(None, description="Currently deployed version number")
    deployment_date: Optional[datetime] = Field(None, description="When this version was deployed")
    deployment_notes: Optional[str] = None

    # Validation Information (for the deployed version)
    validation_request_id: Optional[int] = Field(None, description="Validation request ID for this version")
    validation_status: Optional[str] = Field(None, description="Current validation workflow status")
    validation_status_code: Optional[str] = None
    validation_completion_date: Optional[datetime] = Field(None, description="When validation was completed")

    # Regional Approval Status (region-specific)
    has_regional_approval: bool = Field(False, description="Does this validation have regional approval for THIS region?")
    regional_approver_name: Optional[str] = Field(None, description="Name of regional approver for this region")
    regional_approver_role: Optional[str] = Field(None, description="Role of regional approver for this region")
    regional_approval_status: Optional[str] = Field(None, description="Regional approval status for this specific region")
    regional_approval_date: Optional[datetime] = Field(None, description="When regional approval was granted for this region")

    # Compliance Flags
    is_deployed_without_validation: bool = Field(False, description="Version deployed but no validation linked")
    is_validation_pending: bool = Field(False, description="Validation in progress")
    is_validation_approved: bool = Field(False, description="Validation fully approved")

    class Config:
        from_attributes = True


class RegionalComplianceReportResponse(BaseModel):
    """Complete regional compliance report."""
    report_generated_at: datetime
    region_filter: Optional[str]
    team_filter: Optional[str] = None
    total_records: int
    records: List[RegionalDeploymentRecord]


@router.get("/", response_model=RegionalComplianceReportResponse)
async def get_regional_deployment_compliance_report(
    region_code: Optional[str] = Query(None, description="Filter by region code (e.g., 'US')"),
    model_id: Optional[int] = Query(None, description="Filter by specific model"),
    team_id: Optional[int] = Query(None, description="Filter by team ID (0 = Unassigned)"),
    only_deployed: bool = Query(True, description="Show only models with deployed versions"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Regional Deployment & Compliance Report.

    **REGULATORY QUESTION:**
    "Show me all models deployed in region X, with deployed version,
    validation status, and regional approval status for that version."

    **What This Report Shows:**
    - ✅ Models deployed in each region
    - ✅ Currently deployed version numbers
    - ✅ Deployment dates
    - ✅ Validation workflow status for those versions
    - ✅ Region-specific approval status (Pending, Approved, Rejected)
    - ✅ Regional approver details for each specific region
    - ✅ Compliance flags (deployed without validation, validation pending, etc.)

    **Filters:**
    - Filter by specific region code (e.g., 'US', 'EU')
    - Filter by model ID
    - Show only models with deployed versions
    """

    # Build the base query
    query = (
        select(
            # Region fields
            Region.region_id,
            Region.code.label('region_code'),
            Region.name.label('region_name'),
            Region.requires_regional_approval,

            # Model fields
            Model.model_id,
            Model.model_name,

            # Deployment fields
            ModelRegion.version_id.label('deployed_version_id'),
            ModelVersion.version_number.label('deployed_version'),
            ModelRegion.deployed_at.label('deployment_date'),
            ModelRegion.deployment_notes,

            # Validation fields
            ValidationRequest.request_id.label('validation_request_id'),
            TaxonomyValue.label.label('validation_status'),
            TaxonomyValue.code.label('validation_status_code'),
            ValidationRequest.completion_date.label('validation_completion_date'),
        )
        .select_from(ModelRegion)
        .join(Region, ModelRegion.region_id == Region.region_id)
        .join(Model, ModelRegion.model_id == Model.model_id)
        .outerjoin(ModelVersion, ModelRegion.version_id == ModelVersion.version_id)
        .outerjoin(ValidationRequest, ModelVersion.validation_request_id == ValidationRequest.request_id)
        .outerjoin(TaxonomyValue, ValidationRequest.current_status_id == TaxonomyValue.value_id)
    )

    # Apply filters
    if region_code:
        query = query.where(Region.code == region_code.upper())

    if model_id:
        query = query.where(Model.model_id == model_id)

    if only_deployed:
        query = query.where(ModelRegion.version_id.isnot(None))

    # Order by region, then model name
    query = query.order_by(Region.code, Model.model_name)

    # Execute query
    results = db.execute(query).all()

    model_ids = list({row.model_id for row in results})
    model_team_map = get_models_team_map(db, model_ids)

    team_filter_name = None
    if team_id is not None:
        if team_id == 0:
            results = [row for row in results if model_team_map.get(row.model_id) is None]
            team_filter_name = "Unassigned"
        else:
            results = [
                row for row in results
                if (team_entry := model_team_map.get(row.model_id))
                and team_entry.get("team_id") == team_id
            ]
            team = db.query(Team).filter(Team.team_id == team_id).first()
            team_filter_name = team.name if team else f"Team {team_id}"

    # Pre-fetch region-specific approvals in a single query
    approval_map = {}
    approval_pairs = {
        (row.validation_request_id, row.region_id)
        for row in results
        if row.validation_request_id and row.requires_regional_approval
    }
    if approval_pairs:
        request_ids = {pair[0] for pair in approval_pairs}
        region_ids = {pair[1] for pair in approval_pairs}
        approvals = db.execute(
            select(
                ValidationApproval.request_id,
                ValidationApproval.region_id,
                ValidationApproval.approval_status,
                User.full_name.label('approver_name'),
                ValidationApproval.approver_role,
                ValidationApproval.approved_at,
            )
            .select_from(ValidationApproval)
            .join(User, ValidationApproval.approver_id == User.user_id)
            .where(ValidationApproval.request_id.in_(request_ids))
            .where(ValidationApproval.region_id.in_(region_ids))
            .where(ValidationApproval.approval_type == 'Regional')
            .order_by(desc(ValidationApproval.approved_at))
        ).all()

        for approval in approvals:
            key = (approval.request_id, approval.region_id)
            if key not in approval_map:
                approval_map[key] = approval

    # Now we need to get region-specific approval information
    records = []
    for row in results:
        # Get regional approval information for THIS specific region
        has_regional_approval = False
        regional_approver_name = None
        regional_approver_role = None
        regional_approval_status = None
        regional_approval_date = None

        if row.validation_request_id and row.requires_regional_approval:
            approval = approval_map.get((row.validation_request_id, row.region_id))
            if approval:
                has_regional_approval = True
                regional_approver_name = approval.approver_name
                regional_approver_role = approval.approver_role
                regional_approval_status = approval.approval_status
                regional_approval_date = approval.approved_at

        # Determine compliance flags
        is_deployed_without_validation = (row.deployed_version_id is not None
                                         and row.validation_request_id is None)
        is_validation_pending = (row.validation_status_code is not None
                               and row.validation_status_code not in ['APPROVED', 'CANCELLED'])
        is_validation_approved = (row.validation_status_code == 'APPROVED')

        record = RegionalDeploymentRecord(
            region_code=row.region_code,
            region_name=row.region_name,
            requires_regional_approval=row.requires_regional_approval,
            model_id=row.model_id,
            model_name=row.model_name,
            deployed_version=row.deployed_version,
            deployment_date=row.deployment_date,
            deployment_notes=row.deployment_notes,
            validation_request_id=row.validation_request_id,
            validation_status=row.validation_status,
            validation_status_code=row.validation_status_code,
            validation_completion_date=row.validation_completion_date,  # Use stored completion date
            has_regional_approval=has_regional_approval,
            regional_approver_name=regional_approver_name,
            regional_approver_role=regional_approver_role,
            regional_approval_status=regional_approval_status,
            regional_approval_date=regional_approval_date,
            is_deployed_without_validation=is_deployed_without_validation,
            is_validation_pending=is_validation_pending,
            is_validation_approved=is_validation_approved,
        )
        records.append(record)

    return RegionalComplianceReportResponse(
        report_generated_at=utc_now(),
        region_filter=region_code,
        team_filter=team_filter_name,
        total_records=len(records),
        records=records
    )
