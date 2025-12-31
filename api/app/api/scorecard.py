"""API endpoints for Validation Scorecard."""
from io import BytesIO
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin, is_validator
from app.core.time import utc_now
from app.core.pdf_reports import generate_validation_scorecard_pdf
from app.core.scorecard import (
    compute_scorecard,
    load_scorecard_config,
    rating_to_score,
    score_to_rating,
    VALID_RATINGS as VALID_RATING_VALUES,
)
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.scorecard import (
    ScorecardSection,
    ScorecardCriterion,
    ValidationScorecardRating,
    ValidationScorecardResult,
    ScorecardConfigVersion,
    ScorecardSectionSnapshot,
    ScorecardCriterionSnapshot,
)
from app.models.validation import ValidationRequest
from app.models.model import Model
from app.models.model_feed_dependency import ModelFeedDependency
from app.schemas.scorecard import (
    ScorecardSectionResponse,
    ScorecardSectionWithCriteria,
    ScorecardSectionCreate,
    ScorecardSectionUpdate,
    ScorecardCriterionResponse,
    ScorecardCriterionCreate,
    ScorecardCriterionUpdate,
    ScorecardConfigResponse,
    ScorecardRatingsCreate,
    CriterionRatingInput,
    CriterionRatingUpdate,
    CriterionRatingResponse,
    ScorecardFullResponse,
    CriterionDetailResponse,
    SectionSummaryResponse,
    OverallAssessmentResponse,
    OverallNarrativeUpdate,
    ScorecardResultResponse,
    # Configuration versioning schemas
    ScorecardConfigVersionResponse,
    ScorecardConfigVersionDetailResponse,
    ScorecardSectionSnapshotResponse,
    ScorecardCriterionSnapshotResponse,
    PublishScorecardVersionRequest,
)

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

def create_audit_log(
    db: Session, entity_type: str, entity_id: int,
    action: str, user_id: int, changes: dict = None
):
    """Create an audit log entry for scorecard changes."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def require_admin_or_validator(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be an Admin or Validator."""
    if not (is_admin(current_user) or is_validator(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Validator role required"
        )
    return current_user


def get_request_or_404(db: Session, request_id: int) -> ValidationRequest:
    """Get validation request, or raise 404."""
    validation_request = (
        db.query(ValidationRequest)
        .options(
            joinedload(ValidationRequest.scorecard_ratings),
            joinedload(ValidationRequest.scorecard_result)
        )
        .filter(ValidationRequest.request_id == request_id)
        .first()
    )
    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")
    return validation_request


def get_scorecard_config_from_db(db: Session) -> dict:
    """Load scorecard configuration from database."""
    sections = (
        db.query(ScorecardSection)
        .filter(ScorecardSection.is_active == True)
        .order_by(ScorecardSection.sort_order)
        .all()
    )

    criteria = (
        db.query(ScorecardCriterion)
        .filter(ScorecardCriterion.is_active == True)
        .order_by(ScorecardCriterion.sort_order)
        .all()
    )

    # Build config dict matching SCORE_CRITERIA.json format
    config = {
        "sections": [
            {"code": s.code, "name": s.name}
            for s in sections
        ],
        "criteria": [
            {
                "code": c.code,
                "section": db.query(ScorecardSection).filter(
                    ScorecardSection.section_id == c.section_id
                ).first().code,
                "name": c.name,
                "description_prompt": c.description_prompt,
                "comments_prompt": c.comments_prompt,
                "include_in_summary": c.include_in_summary,
                "allow_zero": c.allow_zero,
                "weight": float(c.weight),
            }
            for c in criteria
        ]
    }

    return config


def compute_and_store_result(
    db: Session,
    request: ValidationRequest,
    config: dict
) -> ValidationScorecardResult:
    """Compute scorecard and store/update result."""
    # Build ratings dict from stored ratings
    ratings_dict = {}
    for rating in request.scorecard_ratings:
        ratings_dict[rating.criterion_code] = rating.rating

    # Compute scorecard
    computed = compute_scorecard(ratings_dict, config)

    # Create or update result
    result = request.scorecard_result
    if not result:
        result = ValidationScorecardResult(request_id=request.request_id)
        db.add(result)

    # Get active config version to link this scorecard
    active_version = (
        db.query(ScorecardConfigVersion)
        .filter(ScorecardConfigVersion.is_active == True)
        .first()
    )

    # Update result
    result.overall_numeric_score = computed["overall_assessment"]["numeric_score"]
    result.overall_rating = computed["overall_assessment"]["rating"]
    result.section_summaries = {
        s["section_code"]: s for s in computed["section_summaries"]
    }
    result.config_snapshot = {
        "sections": config["sections"],
        "criteria": config["criteria"],
        "snapshot_timestamp": utc_now().isoformat()
    }
    result.computed_at = utc_now()

    # Link to active config version (if exists and not already linked)
    if active_version and not result.config_version_id:
        result.config_version_id = active_version.version_id

    return result


# ============================================================================
# Configuration Endpoints
# ============================================================================

@router.get("/config", response_model=ScorecardConfigResponse)
def get_scorecard_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current scorecard configuration (sections and criteria).

    Returns all active sections with their nested criteria.
    """
    sections = (
        db.query(ScorecardSection)
        .filter(ScorecardSection.is_active == True)
        .options(joinedload(ScorecardSection.criteria))
        .order_by(ScorecardSection.sort_order)
        .all()
    )

    # Build response with nested criteria
    section_responses = []
    for section in sections:
        active_criteria = [c for c in section.criteria if c.is_active]
        active_criteria.sort(key=lambda c: c.sort_order)

        section_responses.append(
            ScorecardSectionWithCriteria(
                section_id=section.section_id,
                code=section.code,
                name=section.name,
                description=section.description,
                sort_order=section.sort_order,
                is_active=section.is_active,
                created_at=section.created_at,
                updated_at=section.updated_at,
                criteria=[
                    ScorecardCriterionResponse(
                        criterion_id=c.criterion_id,
                        code=c.code,
                        section_id=c.section_id,
                        name=c.name,
                        description_prompt=c.description_prompt,
                        comments_prompt=c.comments_prompt,
                        include_in_summary=c.include_in_summary,
                        allow_zero=c.allow_zero,
                        weight=float(c.weight),
                        sort_order=c.sort_order,
                        is_active=c.is_active,
                        created_at=c.created_at,
                        updated_at=c.updated_at,
                    )
                    for c in active_criteria
                ]
            )
        )

    return ScorecardConfigResponse(sections=section_responses)


# ============================================================================
# Scorecard Rating Endpoints
# ============================================================================

@router.post(
    "/validation/{request_id}",
    response_model=ScorecardFullResponse,
    status_code=status.HTTP_201_CREATED
)
def create_or_update_scorecard(
    request_id: int,
    data: ScorecardRatingsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator)
):
    """
    Create or update all scorecard ratings for a validation request.

    This replaces all existing ratings with the provided ones.
    The scorecard result is automatically recomputed.

    Requires Admin or Validator role.
    """
    validation_request = get_request_or_404(db, request_id)

    # Get configuration
    config = get_scorecard_config_from_db(db)
    if not config["criteria"]:
        # Fall back to JSON config if DB is empty
        config = load_scorecard_config()

    # Build set of valid criterion codes
    valid_codes = {c["code"] for c in config["criteria"]}

    # Delete existing ratings
    db.query(ValidationScorecardRating).filter(
        ValidationScorecardRating.request_id == validation_request.request_id
    ).delete()

    # Create new ratings
    for rating_input in data.ratings:
        if rating_input.criterion_code not in valid_codes:
            # Ignore unknown criterion codes (per design decision)
            continue

        rating = ValidationScorecardRating(
            request_id=validation_request.request_id,
            criterion_code=rating_input.criterion_code,
            rating=rating_input.rating,
            description=rating_input.description,
            comments=rating_input.comments,
        )
        db.add(rating)

    db.flush()

    # Recompute and store result
    result = compute_and_store_result(db, validation_request, config)

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="ValidationScorecard",
        entity_id=validation_request.request_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "ratings_count": len(data.ratings),
            "overall_score": result.overall_numeric_score,
            "overall_rating": result.overall_rating
        }
    )

    db.commit()

    # Build response
    return _build_scorecard_response(db, validation_request, config)


@router.get(
    "/validation/{request_id}",
    response_model=ScorecardFullResponse
)
def get_scorecard(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the scorecard ratings and computed results for a validation request.

    Returns per-criterion ratings, section summaries, and overall assessment.
    """
    validation_request = get_request_or_404(db, request_id)

    # Get configuration
    config = get_scorecard_config_from_db(db)
    if not config["criteria"]:
        config = load_scorecard_config()

    # If no result exists yet, compute it
    if not validation_request.scorecard_result:
        result = compute_and_store_result(db, validation_request, config)
        db.commit()

    return _build_scorecard_response(db, validation_request, config)


@router.get("/validation/{request_id}/export-pdf")
def export_validation_scorecard_pdf(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> StreamingResponse:
    """
    Export validation scorecard as PDF.

    Returns a one-page PDF containing:
    - Model metadata (owner, name, submission type)
    - Overall assessment with rating badge
    - Criteria ratings table organized by section
    - Related models (upstream/downstream dependencies)
    - Region metadata
    """
    # Get validation request with models relationship
    validation_request = (
        db.query(ValidationRequest)
        .options(
            joinedload(ValidationRequest.scorecard_ratings),
            joinedload(ValidationRequest.scorecard_result),
            joinedload(ValidationRequest.models),
            joinedload(ValidationRequest.validation_type),
        )
        .filter(ValidationRequest.request_id == request_id)
        .first()
    )

    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Get the primary model (first model in the request)
    if not validation_request.models:
        raise HTTPException(
            status_code=400,
            detail="No model associated with this validation request"
        )
    model = validation_request.models[0]

    # Reload model with all relationships
    model = (
        db.query(Model)
        .options(
            joinedload(Model.owner),
            joinedload(Model.model_type),
            joinedload(Model.model_regions),
            joinedload(Model.inbound_dependencies).joinedload(ModelFeedDependency.feeder_model),
            joinedload(Model.outbound_dependencies).joinedload(ModelFeedDependency.consumer_model),
        )
        .filter(Model.model_id == model.model_id)
        .first()
    )

    # Get scorecard configuration and data
    config = get_scorecard_config_from_db(db)
    if not config["criteria"]:
        config = load_scorecard_config()

    # Ensure scorecard result exists
    if not validation_request.scorecard_result:
        compute_and_store_result(db, validation_request, config)
        db.commit()

    # Build scorecard response data
    scorecard_response = _build_scorecard_response(db, validation_request, config)

    # Build validation request dict for PDF
    validation_request_dict = {
        "request_id": validation_request.request_id,
        "validation_type": (
            validation_request.validation_type.label
            if validation_request.validation_type else None
        ),
    }

    # Build model dict for PDF
    model_dict = {
        "model_id": model.model_id,
        "model_name": model.model_name,
        "owner_name": model.owner.full_name if model.owner else None,
        "model_type": model.model_type.label if model.model_type else None,
        "regions": [
            {"region_name": mr.region.name}
            for mr in model.model_regions
            if mr.region
        ] if model.model_regions else [],
    }

    # Build dependencies dict for PDF
    upstream_models = []
    downstream_models = []

    for dep in model.inbound_dependencies or []:
        if dep.feeder_model:
            upstream_models.append({
                "model_id": dep.feeder_model.model_id,
                "model_name": dep.feeder_model.model_name,
            })

    for dep in model.outbound_dependencies or []:
        if dep.consumer_model:
            downstream_models.append({
                "model_id": dep.consumer_model.model_id,
                "model_name": dep.consumer_model.model_name,
            })

    dependencies_dict = {
        "upstream": upstream_models,
        "downstream": downstream_models,
    }

    # Build scorecard data dict for PDF
    scorecard_dict = {
        "criteria_details": [
            {
                "criterion_code": cd.criterion_code,
                "criterion_name": cd.criterion_name,
                "section_code": cd.section_code,
                "rating": cd.rating,
                "numeric_score": cd.numeric_score,
                "description": cd.description,
                "comments": cd.comments,
            }
            for cd in scorecard_response.criteria_details
        ],
        "section_summaries": [
            {
                "section_code": ss.section_code,
                "section_name": ss.section_name,
                "rating": ss.rating,
            }
            for ss in scorecard_response.section_summaries
        ],
        "overall_assessment": {
            "numeric_score": scorecard_response.overall_assessment.numeric_score,
            "rating": scorecard_response.overall_assessment.rating,
            "overall_assessment_narrative": scorecard_response.overall_assessment.overall_assessment_narrative,
        },
        "computed_at": scorecard_response.computed_at.isoformat() if scorecard_response.computed_at else None,
    }

    # Generate PDF
    pdf_bytes = generate_validation_scorecard_pdf(
        validation_request=validation_request_dict,
        model=model_dict,
        scorecard_data=scorecard_dict,
        dependencies=dependencies_dict,
    )

    # Build filename
    model_name_safe = "".join(
        c if c.isalnum() or c in " -_" else "_"
        for c in (model.model_name or "model")
    ).strip()
    filename = f"Scorecard_{model_name_safe}_{request_id}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.patch(
    "/validation/{request_id}/ratings/{criterion_code}",
    response_model=ScorecardFullResponse
)
def update_single_rating(
    request_id: int,
    criterion_code: str,
    data: CriterionRatingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator)
):
    """
    Update a single criterion rating.

    The scorecard result is automatically recomputed.

    Requires Admin or Validator role.
    """
    validation_request = get_request_or_404(db, request_id)

    # Get configuration
    config = get_scorecard_config_from_db(db)
    if not config["criteria"]:
        config = load_scorecard_config()

    # Validate criterion code
    valid_codes = {c["code"] for c in config["criteria"]}
    if criterion_code not in valid_codes:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown criterion code: {criterion_code}"
        )

    # Find or create rating
    rating = (
        db.query(ValidationScorecardRating)
        .filter(
            ValidationScorecardRating.request_id == validation_request.request_id,
            ValidationScorecardRating.criterion_code == criterion_code
        )
        .first()
    )

    if not rating:
        rating = ValidationScorecardRating(
            request_id=validation_request.request_id,
            criterion_code=criterion_code,
        )
        db.add(rating)

    # Update fields
    if data.rating is not None:
        rating.rating = data.rating
    if data.description is not None:
        rating.description = data.description
    if data.comments is not None:
        rating.comments = data.comments
    rating.updated_at = utc_now()

    db.flush()

    # Recompute result
    result = compute_and_store_result(db, validation_request, config)

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="ValidationScorecard",
        entity_id=validation_request.request_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes={
            "criterion_code": criterion_code,
            "rating": data.rating,
            "overall_score": result.overall_numeric_score,
            "overall_rating": result.overall_rating
        }
    )

    db.commit()

    return _build_scorecard_response(db, validation_request, config)


@router.patch(
    "/validation/{request_id}/overall-narrative",
    response_model=ScorecardFullResponse
)
def update_overall_narrative(
    request_id: int,
    data: OverallNarrativeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator)
):
    """
    Update the overall assessment narrative for a validation scorecard.

    This endpoint allows updating just the narrative text without affecting
    ratings or recomputing scores. Ideal for auto-save functionality.

    Requires Admin or Validator role.
    """
    validation_request = get_request_or_404(db, request_id)

    # Get configuration
    config = get_scorecard_config_from_db(db)
    if not config["criteria"]:
        config = load_scorecard_config()

    # Get or create result
    result = validation_request.scorecard_result
    if not result:
        result = compute_and_store_result(db, validation_request, config)

    # Update narrative
    old_narrative = result.overall_assessment_narrative
    result.overall_assessment_narrative = data.overall_assessment_narrative

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="ValidationScorecard",
        entity_id=validation_request.request_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes={
            "field": "overall_assessment_narrative",
            "old": old_narrative[:100] + "..." if old_narrative and len(old_narrative) > 100 else old_narrative,
            "new": data.overall_assessment_narrative[:100] + "..." if data.overall_assessment_narrative and len(data.overall_assessment_narrative) > 100 else data.overall_assessment_narrative
        }
    )

    db.commit()

    return _build_scorecard_response(db, validation_request, config)


# ============================================================================
# Response Builder
# ============================================================================

def _build_scorecard_response(
    db: Session,
    validation_request: ValidationRequest,
    config: dict
) -> ScorecardFullResponse:
    """Build the full scorecard response from request and config."""
    # Build ratings dict
    ratings_dict = {}
    descriptions_dict = {}
    comments_dict = {}
    for rating in validation_request.scorecard_ratings:
        ratings_dict[rating.criterion_code] = rating.rating
        descriptions_dict[rating.criterion_code] = rating.description
        comments_dict[rating.criterion_code] = rating.comments

    # Compute scorecard
    computed = compute_scorecard(ratings_dict, config)

    # Build criteria details with descriptions and comments
    criteria_details = []
    for detail in computed["criteria_details"]:
        criteria_details.append(
            CriterionDetailResponse(
                criterion_code=detail["criterion_code"],
                criterion_name=detail["criterion_name"],
                section_code=detail["section_code"],
                rating=detail["rating"],
                numeric_score=detail["numeric_score"],
                description=descriptions_dict.get(detail["criterion_code"]),
                comments=comments_dict.get(detail["criterion_code"]),
            )
        )

    # Build section summaries
    section_summaries = [
        SectionSummaryResponse(**s) for s in computed["section_summaries"]
    ]

    # Build overall assessment
    overall = OverallAssessmentResponse(**computed["overall_assessment"])

    # Add stored narrative from result if exists
    if validation_request.scorecard_result:
        overall.overall_assessment_narrative = validation_request.scorecard_result.overall_assessment_narrative

    # Get computed_at from result if exists
    computed_at = validation_request.scorecard_result.computed_at if validation_request.scorecard_result else utc_now()

    return ScorecardFullResponse(
        request_id=validation_request.request_id,
        criteria_details=criteria_details,
        section_summaries=section_summaries,
        overall_assessment=overall,
        computed_at=computed_at,
    )


# ============================================================================
# Admin: Section CRUD Endpoints
# ============================================================================

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be an Admin."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


@router.get("/sections", response_model=List[ScorecardSectionWithCriteria])
def list_sections(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all scorecard sections with their criteria.

    By default, only active sections are returned.
    Set include_inactive=true to include inactive sections.
    """
    query = (
        db.query(ScorecardSection)
        .options(joinedload(ScorecardSection.criteria))
        .order_by(ScorecardSection.sort_order)
    )
    if not include_inactive:
        query = query.filter(ScorecardSection.is_active == True)

    sections = query.all()

    return [
        ScorecardSectionWithCriteria(
            section_id=s.section_id,
            code=s.code,
            name=s.name,
            description=s.description,
            sort_order=s.sort_order,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
            criteria=[
                ScorecardCriterionResponse(
                    criterion_id=c.criterion_id,
                    code=c.code,
                    section_id=c.section_id,
                    name=c.name,
                    description_prompt=c.description_prompt,
                    comments_prompt=c.comments_prompt,
                    include_in_summary=c.include_in_summary,
                    allow_zero=c.allow_zero,
                    weight=float(c.weight),
                    sort_order=c.sort_order,
                    is_active=c.is_active,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in sorted(s.criteria, key=lambda x: x.sort_order)
            ]
        )
        for s in sections
    ]


@router.get("/sections/{section_id}", response_model=ScorecardSectionWithCriteria)
def get_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single section with its criteria."""
    section = (
        db.query(ScorecardSection)
        .options(joinedload(ScorecardSection.criteria))
        .filter(ScorecardSection.section_id == section_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Sort criteria by sort_order
    criteria = sorted(section.criteria, key=lambda c: c.sort_order)

    return ScorecardSectionWithCriteria(
        section_id=section.section_id,
        code=section.code,
        name=section.name,
        description=section.description,
        sort_order=section.sort_order,
        is_active=section.is_active,
        created_at=section.created_at,
        updated_at=section.updated_at,
        criteria=[
            ScorecardCriterionResponse(
                criterion_id=c.criterion_id,
                code=c.code,
                section_id=c.section_id,
                name=c.name,
                description_prompt=c.description_prompt,
                comments_prompt=c.comments_prompt,
                include_in_summary=c.include_in_summary,
                allow_zero=c.allow_zero,
                weight=float(c.weight),
                sort_order=c.sort_order,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in criteria
        ]
    )


@router.post("/sections", response_model=ScorecardSectionResponse, status_code=status.HTTP_201_CREATED)
def create_section(
    data: ScorecardSectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new scorecard section. Admin only."""
    # Check for duplicate code
    existing = db.query(ScorecardSection).filter(ScorecardSection.code == data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Section with code '{data.code}' already exists"
        )

    section = ScorecardSection(
        code=data.code,
        name=data.name,
        description=data.description,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(section)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="ScorecardSection",
        entity_id=section.section_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"code": data.code, "name": data.name}
    )

    db.commit()
    db.refresh(section)
    return section


@router.patch("/sections/{section_id}", response_model=ScorecardSectionResponse)
def update_section(
    section_id: int,
    data: ScorecardSectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a scorecard section. Admin only."""
    section = db.query(ScorecardSection).filter(ScorecardSection.section_id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    changes = {}
    if data.name is not None and data.name != section.name:
        changes["name"] = {"old": section.name, "new": data.name}
        section.name = data.name
    if data.description is not None and data.description != section.description:
        changes["description"] = {"old": section.description, "new": data.description}
        section.description = data.description
    if data.sort_order is not None and data.sort_order != section.sort_order:
        changes["sort_order"] = {"old": section.sort_order, "new": data.sort_order}
        section.sort_order = data.sort_order
    if data.is_active is not None and data.is_active != section.is_active:
        changes["is_active"] = {"old": section.is_active, "new": data.is_active}
        section.is_active = data.is_active

    if changes:
        section.updated_at = utc_now()
        create_audit_log(
            db=db,
            entity_type="ScorecardSection",
            entity_id=section.section_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )
        db.commit()
        db.refresh(section)

    return section


@router.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete a scorecard section. Admin only.

    This will also delete all criteria belonging to this section.
    Use with caution - consider deactivating instead.
    """
    section = db.query(ScorecardSection).filter(ScorecardSection.section_id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    create_audit_log(
        db=db,
        entity_type="ScorecardSection",
        entity_id=section.section_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"code": section.code, "name": section.name}
    )

    db.delete(section)
    db.commit()


# ============================================================================
# Admin: Criterion CRUD Endpoints
# ============================================================================

@router.get("/criteria", response_model=List[ScorecardCriterionResponse])
def list_criteria(
    section_id: Optional[int] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all scorecard criteria.

    Optionally filter by section_id.
    By default, only active criteria are returned.
    """
    query = db.query(ScorecardCriterion).order_by(
        ScorecardCriterion.section_id,
        ScorecardCriterion.sort_order
    )
    if section_id is not None:
        query = query.filter(ScorecardCriterion.section_id == section_id)
    if not include_inactive:
        query = query.filter(ScorecardCriterion.is_active == True)

    criteria = query.all()
    return [
        ScorecardCriterionResponse(
            criterion_id=c.criterion_id,
            code=c.code,
            section_id=c.section_id,
            name=c.name,
            description_prompt=c.description_prompt,
            comments_prompt=c.comments_prompt,
            include_in_summary=c.include_in_summary,
            allow_zero=c.allow_zero,
            weight=float(c.weight),
            sort_order=c.sort_order,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in criteria
    ]


@router.get("/criteria/{criterion_id}", response_model=ScorecardCriterionResponse)
def get_criterion(
    criterion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single criterion."""
    criterion = db.query(ScorecardCriterion).filter(
        ScorecardCriterion.criterion_id == criterion_id
    ).first()
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found")

    return ScorecardCriterionResponse(
        criterion_id=criterion.criterion_id,
        code=criterion.code,
        section_id=criterion.section_id,
        name=criterion.name,
        description_prompt=criterion.description_prompt,
        comments_prompt=criterion.comments_prompt,
        include_in_summary=criterion.include_in_summary,
        allow_zero=criterion.allow_zero,
        weight=float(criterion.weight),
        sort_order=criterion.sort_order,
        is_active=criterion.is_active,
        created_at=criterion.created_at,
        updated_at=criterion.updated_at,
    )


@router.post("/criteria", response_model=ScorecardCriterionResponse, status_code=status.HTTP_201_CREATED)
def create_criterion(
    data: ScorecardCriterionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new scorecard criterion. Admin only."""
    # Verify section exists
    section = db.query(ScorecardSection).filter(ScorecardSection.section_id == data.section_id).first()
    if not section:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Section with id {data.section_id} not found"
        )

    # Check for duplicate code
    existing = db.query(ScorecardCriterion).filter(ScorecardCriterion.code == data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Criterion with code '{data.code}' already exists"
        )

    criterion = ScorecardCriterion(
        code=data.code,
        section_id=data.section_id,
        name=data.name,
        description_prompt=data.description_prompt,
        comments_prompt=data.comments_prompt,
        include_in_summary=data.include_in_summary,
        allow_zero=data.allow_zero,
        weight=data.weight,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(criterion)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="ScorecardCriterion",
        entity_id=criterion.criterion_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"code": data.code, "name": data.name, "section_id": data.section_id}
    )

    db.commit()
    db.refresh(criterion)

    return ScorecardCriterionResponse(
        criterion_id=criterion.criterion_id,
        code=criterion.code,
        section_id=criterion.section_id,
        name=criterion.name,
        description_prompt=criterion.description_prompt,
        comments_prompt=criterion.comments_prompt,
        include_in_summary=criterion.include_in_summary,
        allow_zero=criterion.allow_zero,
        weight=float(criterion.weight),
        sort_order=criterion.sort_order,
        is_active=criterion.is_active,
        created_at=criterion.created_at,
        updated_at=criterion.updated_at,
    )


@router.patch("/criteria/{criterion_id}", response_model=ScorecardCriterionResponse)
def update_criterion(
    criterion_id: int,
    data: ScorecardCriterionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a scorecard criterion. Admin only."""
    criterion = db.query(ScorecardCriterion).filter(
        ScorecardCriterion.criterion_id == criterion_id
    ).first()
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found")

    changes = {}
    if data.name is not None and data.name != criterion.name:
        changes["name"] = {"old": criterion.name, "new": data.name}
        criterion.name = data.name
    if data.description_prompt is not None and data.description_prompt != criterion.description_prompt:
        changes["description_prompt"] = {"old": criterion.description_prompt, "new": data.description_prompt}
        criterion.description_prompt = data.description_prompt
    if data.comments_prompt is not None and data.comments_prompt != criterion.comments_prompt:
        changes["comments_prompt"] = {"old": criterion.comments_prompt, "new": data.comments_prompt}
        criterion.comments_prompt = data.comments_prompt
    if data.include_in_summary is not None and data.include_in_summary != criterion.include_in_summary:
        changes["include_in_summary"] = {"old": criterion.include_in_summary, "new": data.include_in_summary}
        criterion.include_in_summary = data.include_in_summary
    if data.allow_zero is not None and data.allow_zero != criterion.allow_zero:
        changes["allow_zero"] = {"old": criterion.allow_zero, "new": data.allow_zero}
        criterion.allow_zero = data.allow_zero
    if data.weight is not None and data.weight != float(criterion.weight):
        changes["weight"] = {"old": float(criterion.weight), "new": data.weight}
        criterion.weight = data.weight
    if data.sort_order is not None and data.sort_order != criterion.sort_order:
        changes["sort_order"] = {"old": criterion.sort_order, "new": data.sort_order}
        criterion.sort_order = data.sort_order
    if data.is_active is not None and data.is_active != criterion.is_active:
        changes["is_active"] = {"old": criterion.is_active, "new": data.is_active}
        criterion.is_active = data.is_active

    if changes:
        criterion.updated_at = utc_now()
        create_audit_log(
            db=db,
            entity_type="ScorecardCriterion",
            entity_id=criterion.criterion_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )
        db.commit()
        db.refresh(criterion)

    return ScorecardCriterionResponse(
        criterion_id=criterion.criterion_id,
        code=criterion.code,
        section_id=criterion.section_id,
        name=criterion.name,
        description_prompt=criterion.description_prompt,
        comments_prompt=criterion.comments_prompt,
        include_in_summary=criterion.include_in_summary,
        allow_zero=criterion.allow_zero,
        weight=float(criterion.weight),
        sort_order=criterion.sort_order,
        is_active=criterion.is_active,
        created_at=criterion.created_at,
        updated_at=criterion.updated_at,
    )


@router.delete("/criteria/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_criterion(
    criterion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete a scorecard criterion. Admin only.

    Use with caution - existing scorecard ratings that reference this criterion
    by code will become orphaned (but preserved for historical accuracy).
    Consider deactivating instead.
    """
    criterion = db.query(ScorecardCriterion).filter(
        ScorecardCriterion.criterion_id == criterion_id
    ).first()
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found")

    create_audit_log(
        db=db,
        entity_type="ScorecardCriterion",
        entity_id=criterion.criterion_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"code": criterion.code, "name": criterion.name}
    )

    db.delete(criterion)
    db.commit()


# ============================================================================
# Scorecard Config Version Endpoints
# ============================================================================


@router.get("/versions", response_model=List[ScorecardConfigVersionResponse])
def list_config_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all scorecard configuration versions.

    Returns versions ordered by version_number descending (newest first).
    Includes has_unpublished_changes for the active version.
    """
    versions = (
        db.query(ScorecardConfigVersion)
        .order_by(ScorecardConfigVersion.version_number.desc())
        .all()
    )

    # Find the active version and check for unpublished changes
    active_version = next((v for v in versions if v.is_active), None)
    active_has_changes = _check_unpublished_changes(db, active_version) if active_version else False

    return [
        ScorecardConfigVersionResponse(
            version_id=v.version_id,
            version_number=v.version_number,
            version_name=v.version_name,
            description=v.description,
            published_by_name=v.published_by.full_name if v.published_by else None,
            published_at=v.published_at,
            is_active=v.is_active,
            sections_count=len(v.section_snapshots),
            criteria_count=len(v.criterion_snapshots),
            scorecards_count=len(v.scorecard_results),
            created_at=v.created_at,
            has_unpublished_changes=active_has_changes if v.is_active else False,
        )
        for v in versions
    ]


@router.get("/versions/active", response_model=Optional[ScorecardConfigVersionDetailResponse])
def get_active_config_version(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the currently active scorecard configuration version with all snapshots.

    Returns None if no active version exists.
    Includes has_unpublished_changes flag to indicate if config changed since publish.
    """
    version = (
        db.query(ScorecardConfigVersion)
        .options(
            joinedload(ScorecardConfigVersion.section_snapshots),
            joinedload(ScorecardConfigVersion.criterion_snapshots),
            joinedload(ScorecardConfigVersion.published_by),
        )
        .filter(ScorecardConfigVersion.is_active == True)
        .first()
    )

    if not version:
        return None

    # Check if there are unpublished changes
    has_changes = _check_unpublished_changes(db, version)

    return _build_version_detail_response(version, db, has_changes)


@router.get("/versions/{version_id}", response_model=ScorecardConfigVersionDetailResponse)
def get_config_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific scorecard configuration version with all snapshots.
    """
    version = (
        db.query(ScorecardConfigVersion)
        .options(
            joinedload(ScorecardConfigVersion.section_snapshots),
            joinedload(ScorecardConfigVersion.criterion_snapshots),
            joinedload(ScorecardConfigVersion.published_by),
        )
        .filter(ScorecardConfigVersion.version_id == version_id)
        .first()
    )

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Only check unpublished changes for active version
    has_changes = _check_unpublished_changes(db, version) if version.is_active else False

    return _build_version_detail_response(version, db, has_changes)


@router.post("/versions/publish", response_model=ScorecardConfigVersionResponse, status_code=status.HTTP_201_CREATED)
def publish_config_version(
    data: PublishScorecardVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Publish a new scorecard configuration version.

    This snapshots all current active sections and criteria.
    The new version becomes the active version, and previous versions are deactivated.

    Admin only.
    """
    # Get next version number
    max_version = db.query(func.max(ScorecardConfigVersion.version_number)).scalar() or 0
    new_version_number = max_version + 1

    # Deactivate previous active version
    db.query(ScorecardConfigVersion).filter(
        ScorecardConfigVersion.is_active == True
    ).update({"is_active": False})

    # Create new version
    version_name = data.version_name or f"Version {new_version_number}"

    new_version = ScorecardConfigVersion(
        version_number=new_version_number,
        version_name=version_name,
        description=data.description,
        published_by_user_id=current_user.user_id,
        is_active=True,
    )
    db.add(new_version)
    db.flush()

    # Snapshot all active sections
    sections = (
        db.query(ScorecardSection)
        .filter(ScorecardSection.is_active == True)
        .order_by(ScorecardSection.sort_order)
        .all()
    )

    for section in sections:
        snapshot = ScorecardSectionSnapshot(
            version_id=new_version.version_id,
            original_section_id=section.section_id,
            code=section.code,
            name=section.name,
            description=section.description,
            sort_order=section.sort_order,
            is_active=section.is_active,
        )
        db.add(snapshot)

    # Snapshot all active criteria
    criteria = (
        db.query(ScorecardCriterion)
        .join(ScorecardSection)
        .filter(ScorecardCriterion.is_active == True)
        .order_by(ScorecardCriterion.sort_order)
        .all()
    )

    for criterion in criteria:
        section_code = criterion.section.code
        snapshot = ScorecardCriterionSnapshot(
            version_id=new_version.version_id,
            original_criterion_id=criterion.criterion_id,
            section_code=section_code,
            code=criterion.code,
            name=criterion.name,
            description_prompt=criterion.description_prompt,
            comments_prompt=criterion.comments_prompt,
            include_in_summary=criterion.include_in_summary,
            allow_zero=criterion.allow_zero,
            weight=float(criterion.weight),
            sort_order=criterion.sort_order,
            is_active=criterion.is_active,
        )
        db.add(snapshot)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="ScorecardConfigVersion",
        entity_id=new_version.version_id,
        action="PUBLISH",
        user_id=current_user.user_id,
        changes={
            "version_number": new_version_number,
            "version_name": version_name,
            "sections_count": len(sections),
            "criteria_count": len(criteria),
        }
    )

    db.commit()
    db.refresh(new_version)

    return ScorecardConfigVersionResponse(
        version_id=new_version.version_id,
        version_number=new_version.version_number,
        version_name=new_version.version_name,
        description=new_version.description,
        published_by_name=current_user.full_name,
        published_at=new_version.published_at,
        is_active=new_version.is_active,
        sections_count=len(sections),
        criteria_count=len(criteria),
        scorecards_count=0,
        created_at=new_version.created_at,
    )


def _check_unpublished_changes(db: Session, version: ScorecardConfigVersion) -> bool:
    """Check if there are unpublished changes since this version was published."""
    if not version or not version.is_active:
        return False

    # Get the most recent update timestamp from sections
    latest_section_update = (
        db.query(func.max(ScorecardSection.updated_at))
        .filter(ScorecardSection.is_active == True)
        .scalar()
    )

    # Get the most recent update timestamp from criteria
    latest_criterion_update = (
        db.query(func.max(ScorecardCriterion.updated_at))
        .filter(ScorecardCriterion.is_active == True)
        .scalar()
    )

    # Check if either is newer than published_at
    if latest_section_update and latest_section_update > version.published_at:
        return True
    if latest_criterion_update and latest_criterion_update > version.published_at:
        return True

    return False


def _build_version_detail_response(
    version: ScorecardConfigVersion,
    db: Session = None,
    has_unpublished_changes: bool = False
) -> ScorecardConfigVersionDetailResponse:
    """Build the detailed version response with snapshots."""
    section_snapshots = [
        ScorecardSectionSnapshotResponse(
            snapshot_id=s.snapshot_id,
            code=s.code,
            name=s.name,
            description=s.description,
            sort_order=s.sort_order,
            is_active=s.is_active,
        )
        for s in sorted(version.section_snapshots, key=lambda x: x.sort_order)
    ]

    criterion_snapshots = [
        ScorecardCriterionSnapshotResponse(
            snapshot_id=c.snapshot_id,
            section_code=c.section_code,
            code=c.code,
            name=c.name,
            description_prompt=c.description_prompt,
            comments_prompt=c.comments_prompt,
            include_in_summary=c.include_in_summary,
            allow_zero=c.allow_zero,
            weight=float(c.weight),
            sort_order=c.sort_order,
            is_active=c.is_active,
        )
        for c in sorted(version.criterion_snapshots, key=lambda x: x.sort_order)
    ]

    return ScorecardConfigVersionDetailResponse(
        version_id=version.version_id,
        version_number=version.version_number,
        version_name=version.version_name,
        description=version.description,
        published_by_name=version.published_by.full_name if version.published_by else None,
        published_at=version.published_at,
        is_active=version.is_active,
        sections_count=len(section_snapshots),
        criteria_count=len(criterion_snapshots),
        scorecards_count=len(version.scorecard_results),
        created_at=version.created_at,
        has_unpublished_changes=has_unpublished_changes,
        section_snapshots=section_snapshots,
        criterion_snapshots=criterion_snapshots,
    )
