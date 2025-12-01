"""API endpoints for Validation Scorecard."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.time import utc_now
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
)
from app.models.validation import ValidationRequest
from app.schemas.scorecard import (
    ScorecardSectionResponse,
    ScorecardSectionWithCriteria,
    ScorecardCriterionResponse,
    ScorecardConfigResponse,
    ScorecardRatingsCreate,
    CriterionRatingInput,
    CriterionRatingUpdate,
    CriterionRatingResponse,
    ScorecardFullResponse,
    CriterionDetailResponse,
    SectionSummaryResponse,
    OverallAssessmentResponse,
    ScorecardResultResponse,
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
    if current_user.role not in ("Admin", "Validator"):
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

    # Get computed_at from result if exists
    computed_at = validation_request.scorecard_result.computed_at if validation_request.scorecard_result else utc_now()

    return ScorecardFullResponse(
        request_id=validation_request.request_id,
        criteria_details=criteria_details,
        section_summaries=section_summaries,
        overall_assessment=overall,
        computed_at=computed_at,
    )
