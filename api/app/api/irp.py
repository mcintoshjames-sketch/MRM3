"""IRP (Independent Review Process) routes."""
from typing import List, Optional
from datetime import date
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rls import apply_model_rls, can_see_all_data
from app.models.user import User
from app.models.model import Model
from app.models.irp import IRP, IRPReview, IRPCertification
from app.models.mrsa_review_policy import MRSAReviewPolicy, MRSAReviewException
from app.models.taxonomy import TaxonomyValue
from app.models.audit_log import AuditLog
from app.schemas.irp import (
    IRPCreate, IRPUpdate, IRPResponse, IRPDetailResponse,
    IRPReviewCreate, IRPReviewResponse,
    IRPCertificationCreate, IRPCertificationResponse,
    MRSASummary, IRPCoverageStatus
)
from app.schemas.mrsa_review_policy import (
    MRSAReviewStatus, MRSAReviewStatusEnum
)

router = APIRouter()

def _get_accessible_mrsa_ids(db: Session, current_user: User) -> set[int]:
    query = db.query(Model.model_id).filter(Model.is_mrsa == True)
    query = apply_model_rls(query, current_user, db)
    return {row[0] for row in query.all()}


def _require_irp_access(irp: IRP, accessible_mrsa_ids: set[int] | None) -> None:
    if accessible_mrsa_ids is None:
        return
    if not irp.covered_mrsas:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    if not any(mrsa.model_id in accessible_mrsa_ids for mrsa in irp.covered_mrsas):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for IRP operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)
    db.flush()


def _build_irp_response(irp: IRP) -> dict:
    """Build IRP response with computed fields."""
    response = {
        "irp_id": irp.irp_id,
        "process_name": irp.process_name,
        "description": irp.description,
        "is_active": irp.is_active,
        "contact_user_id": irp.contact_user_id,
        "contact_user": irp.contact_user,
        "created_at": irp.created_at,
        "updated_at": irp.updated_at,
        "covered_mrsa_count": irp.covered_mrsa_count,
        "latest_review_date": None,
        "latest_review_outcome": None,
        "latest_certification_date": None,
    }

    # Add latest review info
    if irp.latest_review:
        response["latest_review_date"] = irp.latest_review.review_date
        if irp.latest_review.outcome:
            response["latest_review_outcome"] = irp.latest_review.outcome.label

    # Add latest certification date
    if irp.latest_certification:
        response["latest_certification_date"] = irp.latest_certification.certification_date

    return response


def _build_irp_detail_response(irp: IRP, covered_mrsas: Optional[List[Model]] = None) -> dict:
    """Build detailed IRP response with nested relationships."""
    response = _build_irp_response(irp)

    # Add covered MRSAs
    mrsas = covered_mrsas if covered_mrsas is not None else irp.covered_mrsas
    response["covered_mrsas"] = [
        MRSASummary(
            model_id=mrsa.model_id,
            model_name=mrsa.model_name,
            description=mrsa.description,
            mrsa_risk_level_id=mrsa.mrsa_risk_level_id,
            mrsa_risk_level_label=mrsa.mrsa_risk_level.label if mrsa.mrsa_risk_level else None,
            mrsa_risk_rationale=mrsa.mrsa_risk_rationale,
            is_mrsa=mrsa.is_mrsa,
            owner_id=mrsa.owner_id,
            owner_name=mrsa.owner.full_name if mrsa.owner else None,
        )
        for mrsa in mrsas
    ]
    if covered_mrsas is not None:
        response["covered_mrsa_count"] = len(mrsas)

    # Add reviews
    response["reviews"] = irp.reviews
    response["latest_review"] = irp.latest_review

    # Add certifications
    response["certifications"] = irp.certifications
    response["latest_certification"] = irp.latest_certification

    return response


# ============================================================================
# IRP CRUD Endpoints
# ============================================================================

@router.get("/", response_model=List[IRPResponse])
def list_irps(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all IRPs with optional filtering by active status."""
    query = db.query(IRP).options(
        joinedload(IRP.contact_user),
        joinedload(IRP.reviews).joinedload(IRPReview.outcome),
        joinedload(IRP.certifications),
        joinedload(IRP.covered_mrsas),
    )

    if not can_see_all_data(current_user):
        accessible_mrsa_ids = _get_accessible_mrsa_ids(db, current_user)
        if not accessible_mrsa_ids:
            return []
        query = query.join(IRP.covered_mrsas).filter(
            Model.model_id.in_(accessible_mrsa_ids)
        ).distinct()

    if is_active is not None:
        query = query.filter(IRP.is_active == is_active)

    irps = query.order_by(IRP.process_name).all()
    return [_build_irp_response(irp) for irp in irps]


@router.post("/", response_model=IRPDetailResponse, status_code=status.HTTP_201_CREATED)
def create_irp(
    irp_data: IRPCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new IRP. Admin only."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Validate contact user exists
    contact_user = db.query(User).filter(User.user_id == irp_data.contact_user_id).first()
    if not contact_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact user not found"
        )

    # Check for duplicate name
    existing = db.query(IRP).filter(IRP.process_name == irp_data.process_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IRP with this name already exists"
        )

    # Create IRP
    irp = IRP(
        process_name=irp_data.process_name,
        description=irp_data.description,
        is_active=irp_data.is_active,
        contact_user_id=irp_data.contact_user_id,
    )
    db.add(irp)
    db.flush()  # Get the irp_id

    # Link MRSAs if provided
    if irp_data.mrsa_ids:
        mrsas = db.query(Model).filter(
            Model.model_id.in_(irp_data.mrsa_ids),
            Model.is_mrsa == True
        ).all()

        if len(mrsas) != len(irp_data.mrsa_ids):
            found_ids = {m.model_id for m in mrsas}
            missing_ids = set(irp_data.mrsa_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Some MRSA IDs not found or not MRSAs: {missing_ids}"
            )

        irp.covered_mrsas = mrsas

    db.flush()

    # Create audit log for IRP creation
    create_audit_log(
        db=db,
        entity_type="IRP",
        entity_id=irp.irp_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "process_name": irp.process_name,
            "description": irp.description,
            "contact_user_id": irp.contact_user_id,
            "mrsa_ids": irp_data.mrsa_ids if irp_data.mrsa_ids else []
        }
    )

    # Create audit logs for each linked MRSA
    if irp_data.mrsa_ids:
        for mrsa_id in irp_data.mrsa_ids:
            create_audit_log(
                db=db,
                entity_type="Model",
                entity_id=mrsa_id,
                action="IRP_LINKED",
                user_id=current_user.user_id,
                changes={
                    "irp_id": irp.irp_id,
                    "irp_name": irp.process_name
                }
            )

    db.commit()

    # Reload with relationships
    irp = db.query(IRP).options(
        joinedload(IRP.contact_user),
        joinedload(IRP.covered_mrsas).joinedload(Model.owner),
        joinedload(IRP.covered_mrsas).joinedload(Model.mrsa_risk_level),
        joinedload(IRP.reviews).joinedload(IRPReview.outcome),
        joinedload(IRP.reviews).joinedload(IRPReview.reviewed_by),
        joinedload(IRP.certifications).joinedload(IRPCertification.certified_by),
    ).filter(IRP.irp_id == irp.irp_id).first()

    return _build_irp_detail_response(irp)




@router.get("/{irp_id:int}", response_model=IRPDetailResponse)
def get_irp(
    irp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed IRP with MRSAs, reviews, and certifications."""
    irp = db.query(IRP).options(
        joinedload(IRP.contact_user),
        joinedload(IRP.covered_mrsas).joinedload(Model.owner),
        joinedload(IRP.covered_mrsas).joinedload(Model.mrsa_risk_level),
        joinedload(IRP.reviews).joinedload(IRPReview.outcome),
        joinedload(IRP.reviews).joinedload(IRPReview.reviewed_by),
        joinedload(IRP.certifications).joinedload(IRPCertification.certified_by),
    ).filter(IRP.irp_id == irp_id).first()

    if not irp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IRP not found"
        )

    if not can_see_all_data(current_user):
        accessible_mrsa_ids = _get_accessible_mrsa_ids(db, current_user)
        _require_irp_access(irp, accessible_mrsa_ids)
        accessible_mrsas = [
            mrsa for mrsa in irp.covered_mrsas if mrsa.model_id in accessible_mrsa_ids
        ]
        return _build_irp_detail_response(irp, accessible_mrsas)

    return _build_irp_detail_response(irp)


@router.patch("/{irp_id:int}", response_model=IRPDetailResponse)
def update_irp(
    irp_id: int,
    irp_data: IRPUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an IRP. Admin only."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    irp = db.query(IRP).options(
        joinedload(IRP.covered_mrsas)
    ).filter(IRP.irp_id == irp_id).first()
    if not irp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IRP not found"
        )

    # Track current MRSA IDs before changes
    old_mrsa_ids = set(m.model_id for m in irp.covered_mrsas)

    update_data = irp_data.model_dump(exclude_unset=True)

    # Validate contact user if updating
    if "contact_user_id" in update_data:
        contact_user = db.query(User).filter(User.user_id == update_data["contact_user_id"]).first()
        if not contact_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contact user not found"
            )

    # Check for duplicate name if updating name
    if "process_name" in update_data and update_data["process_name"] != irp.process_name:
        existing = db.query(IRP).filter(IRP.process_name == update_data["process_name"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IRP with this name already exists"
            )

    # Handle MRSA linkages separately
    mrsa_ids = update_data.pop("mrsa_ids", None)

    # Track changes for audit log
    changes = {}
    for field, value in update_data.items():
        old_value = getattr(irp, field)
        if old_value != value:
            changes[field] = {"old": old_value, "new": value}
        setattr(irp, field, value)

    # Update MRSA linkages if provided
    added_mrsa_ids = []
    removed_mrsa_ids = []
    if mrsa_ids is not None:
        new_mrsa_ids = set(mrsa_ids)
        added_mrsa_ids = list(new_mrsa_ids - old_mrsa_ids)
        removed_mrsa_ids = list(old_mrsa_ids - new_mrsa_ids)

        if mrsa_ids:
            mrsas = db.query(Model).filter(
                Model.model_id.in_(mrsa_ids),
                Model.is_mrsa == True
            ).all()

            if len(mrsas) != len(mrsa_ids):
                found_ids = {m.model_id for m in mrsas}
                missing_ids = set(mrsa_ids) - found_ids
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Some MRSA IDs not found or not MRSAs: {missing_ids}"
                )

            irp.covered_mrsas = mrsas
        else:
            irp.covered_mrsas = []

        if added_mrsa_ids or removed_mrsa_ids:
            changes["mrsa_ids"] = {
                "added": added_mrsa_ids,
                "removed": removed_mrsa_ids
            }

    db.flush()

    # Create audit log for IRP update (if any changes)
    if changes:
        create_audit_log(
            db=db,
            entity_type="IRP",
            entity_id=irp.irp_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    # Create audit logs for linked MRSAs
    for mrsa_id in added_mrsa_ids:
        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=mrsa_id,
            action="IRP_LINKED",
            user_id=current_user.user_id,
            changes={
                "irp_id": irp.irp_id,
                "irp_name": irp.process_name
            }
        )

    # Create audit logs for unlinked MRSAs
    for mrsa_id in removed_mrsa_ids:
        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=mrsa_id,
            action="IRP_UNLINKED",
            user_id=current_user.user_id,
            changes={
                "irp_id": irp.irp_id,
                "irp_name": irp.process_name
            }
        )

    db.commit()

    # Reload with relationships
    irp = db.query(IRP).options(
        joinedload(IRP.contact_user),
        joinedload(IRP.covered_mrsas).joinedload(Model.owner),
        joinedload(IRP.covered_mrsas).joinedload(Model.mrsa_risk_level),
        joinedload(IRP.reviews).joinedload(IRPReview.outcome),
        joinedload(IRP.reviews).joinedload(IRPReview.reviewed_by),
        joinedload(IRP.certifications).joinedload(IRPCertification.certified_by),
    ).filter(IRP.irp_id == irp.irp_id).first()

    return _build_irp_detail_response(irp)


@router.delete("/{irp_id:int}", status_code=status.HTTP_204_NO_CONTENT)
def delete_irp(
    irp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an IRP. Admin only."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    irp = db.query(IRP).options(
        joinedload(IRP.covered_mrsas)
    ).filter(IRP.irp_id == irp_id).first()
    if not irp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IRP not found"
        )

    # Store IRP info for audit log before deletion
    irp_name = irp.process_name
    covered_mrsa_ids = [m.model_id for m in irp.covered_mrsas]

    # Create audit log for IRP deletion
    create_audit_log(
        db=db,
        entity_type="IRP",
        entity_id=irp_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "process_name": irp_name,
            "covered_mrsa_ids": covered_mrsa_ids
        }
    )

    # Create audit logs for unlinked MRSAs
    for mrsa_id in covered_mrsa_ids:
        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=mrsa_id,
            action="IRP_UNLINKED",
            user_id=current_user.user_id,
            changes={
                "irp_id": irp_id,
                "irp_name": irp_name,
                "reason": "IRP deleted"
            }
        )

    db.delete(irp)
    db.commit()
    return None


# ============================================================================
# IRP Review Endpoints
# ============================================================================

@router.get("/{irp_id:int}/reviews", response_model=List[IRPReviewResponse])
def list_irp_reviews(
    irp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all reviews for an IRP."""
    irp = db.query(IRP).options(
        joinedload(IRP.covered_mrsas)
    ).filter(IRP.irp_id == irp_id).first()
    if not irp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IRP not found"
        )

    if not can_see_all_data(current_user):
        accessible_mrsa_ids = _get_accessible_mrsa_ids(db, current_user)
        _require_irp_access(irp, accessible_mrsa_ids)

    reviews = db.query(IRPReview).options(
        joinedload(IRPReview.outcome),
        joinedload(IRPReview.reviewed_by),
    ).filter(IRPReview.irp_id == irp_id).order_by(IRPReview.review_date.desc()).all()

    return reviews


@router.post("/{irp_id:int}/reviews", response_model=IRPReviewResponse, status_code=status.HTTP_201_CREATED)
def create_irp_review(
    irp_id: int,
    review_data: IRPReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new review for an IRP."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    irp = db.query(IRP).filter(IRP.irp_id == irp_id).first()
    if not irp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IRP not found"
        )

    # Validate outcome taxonomy value
    outcome = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == review_data.outcome_id).first()
    if not outcome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid outcome taxonomy value"
        )

    review = IRPReview(
        irp_id=irp_id,
        review_date=review_data.review_date,
        outcome_id=review_data.outcome_id,
        notes=review_data.notes,
        reviewed_by_user_id=current_user.user_id,
    )
    db.add(review)
    db.flush()

    # Create audit log for IRP review
    create_audit_log(
        db=db,
        entity_type="IRP",
        entity_id=irp_id,
        action="REVIEW_ADDED",
        user_id=current_user.user_id,
        changes={
            "review_id": review.review_id,
            "review_date": str(review_data.review_date),
            "outcome_id": review_data.outcome_id,
            "outcome_label": outcome.label,
            "notes": review_data.notes
        }
    )

    db.commit()

    # Reload with relationships
    review = db.query(IRPReview).options(
        joinedload(IRPReview.outcome),
        joinedload(IRPReview.reviewed_by),
    ).filter(IRPReview.review_id == review.review_id).first()

    return review


# ============================================================================
# IRP Certification Endpoints
# ============================================================================

@router.get("/{irp_id:int}/certifications", response_model=List[IRPCertificationResponse])
def list_irp_certifications(
    irp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all certifications for an IRP."""
    irp = db.query(IRP).options(
        joinedload(IRP.covered_mrsas)
    ).filter(IRP.irp_id == irp_id).first()
    if not irp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IRP not found"
        )

    if not can_see_all_data(current_user):
        accessible_mrsa_ids = _get_accessible_mrsa_ids(db, current_user)
        _require_irp_access(irp, accessible_mrsa_ids)

    certifications = db.query(IRPCertification).options(
        joinedload(IRPCertification.certified_by),
    ).filter(IRPCertification.irp_id == irp_id).order_by(IRPCertification.certification_date.desc()).all()

    return certifications


@router.post("/{irp_id:int}/certifications", response_model=IRPCertificationResponse, status_code=status.HTTP_201_CREATED)
def create_irp_certification(
    irp_id: int,
    certification_data: IRPCertificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new certification for an IRP. Admin only."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    irp = db.query(IRP).filter(IRP.irp_id == irp_id).first()
    if not irp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IRP not found"
        )

    certification = IRPCertification(
        irp_id=irp_id,
        certification_date=certification_data.certification_date,
        conclusion_summary=certification_data.conclusion_summary,
        certified_by_user_id=current_user.user_id,
    )
    db.add(certification)
    db.flush()

    # Create audit log for IRP certification
    create_audit_log(
        db=db,
        entity_type="IRP",
        entity_id=irp_id,
        action="CERTIFICATION_ADDED",
        user_id=current_user.user_id,
        changes={
            "certification_id": certification.certification_id,
            "certification_date": str(certification_data.certification_date),
            "conclusion_summary": certification_data.conclusion_summary
        }
    )

    db.commit()

    # Reload with relationships
    certification = db.query(IRPCertification).options(
        joinedload(IRPCertification.certified_by),
    ).filter(IRPCertification.certification_id == certification.certification_id).first()

    return certification


# ============================================================================
# IRP Coverage Check Endpoint
# ============================================================================

@router.get("/coverage/check", response_model=List[IRPCoverageStatus])
def check_irp_coverage(
    mrsa_ids: Optional[List[int]] = Query(None, description="Filter by MRSA IDs"),
    require_irp_only: bool = Query(False, description="Only return MRSAs that require IRP"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check IRP coverage status for MRSAs.

    Returns compliance status for each MRSA based on their risk level
    and whether they have IRP coverage.
    """
    query = db.query(Model).options(
        joinedload(Model.mrsa_risk_level),
        joinedload(Model.irps),
    ).filter(Model.is_mrsa == True)

    query = apply_model_rls(query, current_user, db)

    if mrsa_ids:
        query = query.filter(Model.model_id.in_(mrsa_ids))

    mrsas = query.all()

    results = []
    for mrsa in mrsas:
        # Determine if IRP is required based on risk level
        requires_irp = False
        if mrsa.mrsa_risk_level and mrsa.mrsa_risk_level.requires_irp:
            requires_irp = True

        # Skip if filtering for only those that require IRP
        if require_irp_only and not requires_irp:
            continue

        has_coverage = len(mrsa.irps) > 0
        is_compliant = (not requires_irp) or has_coverage

        results.append(IRPCoverageStatus(
            model_id=mrsa.model_id,
            model_name=mrsa.model_name,
            is_mrsa=mrsa.is_mrsa,
            mrsa_risk_level_id=mrsa.mrsa_risk_level_id,
            mrsa_risk_level_label=mrsa.mrsa_risk_level.label if mrsa.mrsa_risk_level else None,
            requires_irp=requires_irp,
            has_irp_coverage=has_coverage,
            is_compliant=is_compliant,
            irp_ids=[irp.irp_id for irp in mrsa.irps],
            irp_names=[irp.process_name for irp in mrsa.irps],
        ))

    return results


# ============================================================================
# MRSA Review Status Calculation
# ============================================================================

def calculate_mrsa_review_status(
    mrsa: Model,
    policy: Optional[MRSAReviewPolicy],
    exception: Optional[MRSAReviewException],
    latest_review_date: Optional[date]
) -> tuple[MRSAReviewStatusEnum, Optional[date], Optional[int]]:
    """Calculate review status for a single MRSA.

    Args:
        mrsa: Model instance (must be MRSA)
        policy: Active review policy for the MRSA's risk level
        exception: Active exception for this MRSA (if any)
        latest_review_date: Date of most recent review across all covering IRPs

    Returns:
        tuple of (status, next_due_date, days_until_due)
    """
    today = date.today()

    # NO_IRP: High-Risk MRSA with no IRP coverage
    if mrsa.mrsa_risk_level and mrsa.mrsa_risk_level.requires_irp and len(mrsa.irps) == 0:
        return (MRSAReviewStatusEnum.NO_IRP, None, None)

    # NO_REQUIREMENT: No active policy (typically Low-Risk MRSAs)
    if not policy or not policy.is_active:
        return (MRSAReviewStatusEnum.NO_REQUIREMENT, None, None)

    # Calculate next due date
    if latest_review_date:
        # Use latest review date + frequency
        next_due_date = latest_review_date + relativedelta(months=policy.frequency_months)
    else:
        # NEVER_REVIEWED: Use creation date + initial review period
        next_due_date = mrsa.created_at.date() + relativedelta(months=policy.initial_review_months)

    # Apply exception override if exists
    if exception and exception.is_active:
        next_due_date = exception.override_due_date

    # Calculate days until due
    days_until_due = (next_due_date - today).days

    # NEVER_REVIEWED: Has IRP but no review ever performed
    if not latest_review_date:
        if days_until_due < 0:
            return (MRSAReviewStatusEnum.OVERDUE, next_due_date, days_until_due)
        return (MRSAReviewStatusEnum.NEVER_REVIEWED, next_due_date, days_until_due)

    # Determine status based on days until due
    if days_until_due < 0:
        return (MRSAReviewStatusEnum.OVERDUE, next_due_date, days_until_due)
    elif days_until_due <= policy.warning_days:
        return (MRSAReviewStatusEnum.UPCOMING, next_due_date, days_until_due)
    else:
        return (MRSAReviewStatusEnum.CURRENT, next_due_date, days_until_due)


@router.get("/mrsa-review-status", response_model=List[MRSAReviewStatus])
def get_mrsa_review_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get review status for all MRSAs.

    Returns review compliance status for all MRSAs based on:
    - Review policy for their risk level
    - Latest review date across all covering IRPs
    - Active exceptions
    """
    # Query all MRSAs with eager loading
    query = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.mrsa_risk_level),
        joinedload(Model.irps).joinedload(IRP.reviews)
    ).filter(Model.is_mrsa == True)

    # Apply row-level security for non-privileged users
    query = apply_model_rls(query, current_user, db)
    mrsas = query.all()

    # Batch load all policies and exceptions
    policies_dict = {}
    policies = db.query(MRSAReviewPolicy).filter(
        MRSAReviewPolicy.is_active == True
    ).all()
    for policy in policies:
        policies_dict[policy.mrsa_risk_level_id] = policy

    exceptions_dict = {}
    exceptions = db.query(MRSAReviewException).filter(
        MRSAReviewException.is_active == True
    ).all()
    for exception in exceptions:
        exceptions_dict[exception.mrsa_id] = exception

    # Calculate status for each MRSA
    results = []
    for mrsa in mrsas:
        # Get policy for this MRSA's risk level
        policy = policies_dict.get(mrsa.mrsa_risk_level_id) if mrsa.mrsa_risk_level_id else None

        # Get exception for this MRSA
        exception = exceptions_dict.get(mrsa.model_id)

        # Find latest review across ALL covering IRPs
        latest_review_date = None
        for irp in mrsa.irps:
            if irp.reviews:
                irp_latest = irp.reviews[0].review_date  # Reviews are ordered DESC by review_date
                if latest_review_date is None or irp_latest > latest_review_date:
                    latest_review_date = irp_latest

        # Calculate status
        status, next_due_date, days_until_due = calculate_mrsa_review_status(
            mrsa=mrsa,
            policy=policy,
            exception=exception,
            latest_review_date=latest_review_date
        )

        results.append(MRSAReviewStatus(
            mrsa_id=mrsa.model_id,
            mrsa_name=mrsa.model_name,
            risk_level=mrsa.mrsa_risk_level.label if mrsa.mrsa_risk_level else None,
            last_review_date=latest_review_date,
            next_due_date=next_due_date,
            status=status,
            days_until_due=days_until_due,
            owner={
                "user_id": mrsa.owner.user_id,
                "full_name": mrsa.owner.full_name,
                "email": mrsa.owner.email
            } if mrsa.owner else None,
            has_exception=exception is not None,
            exception_due_date=exception.override_due_date if exception else None
        ))

    return results
