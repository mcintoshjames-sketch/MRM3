"""API endpoints for Residual Risk Map Configuration.

This module provides endpoints for viewing and configuring the residual
risk map, which maps (Inherent Risk Tier, Scorecard Outcome) to Residual Risk.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.time import utc_now
from app.models.user import User
from app.core.roles import is_admin
from app.models.audit_log import AuditLog
from app.models.residual_risk_map import ResidualRiskMapConfig
from app.schemas.residual_risk_map import (
    ResidualRiskMapCreate,
    ResidualRiskMapUpdate,
    ResidualRiskMapResponse,
    ResidualRiskMapListResponse,
    ResidualRiskMatrixConfig,
    ResidualRiskCalculateRequest,
    ResidualRiskCalculateResponse,
)

router = APIRouter(prefix="/residual-risk-map")


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be an Admin."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


def create_audit_log(
    db: Session, entity_type: str, entity_id: int,
    action: str, user_id: int, changes: dict = None
):
    """Create an audit log entry."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def get_active_config(db: Session) -> Optional[ResidualRiskMapConfig]:
    """Get the currently active residual risk map configuration."""
    return (
        db.query(ResidualRiskMapConfig)
        .filter(ResidualRiskMapConfig.is_active == True)
        .first()
    )


@router.get("/", response_model=Optional[ResidualRiskMapResponse])
def get_residual_risk_map(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current active residual risk map configuration.

    Returns the matrix configuration that maps (Inherent Risk Tier, Scorecard Outcome)
    to Residual Risk.
    """
    config = get_active_config(db)

    if not config:
        return None

    return ResidualRiskMapResponse(
        config_id=config.config_id,
        version_number=config.version_number,
        version_name=config.version_name,
        description=config.description,
        matrix_config=ResidualRiskMatrixConfig(**config.matrix_config),
        is_active=config.is_active,
        created_by_name=config.created_by.full_name if config.created_by else None,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get("/versions", response_model=List[ResidualRiskMapListResponse])
def list_residual_risk_map_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all residual risk map configuration versions.

    Returns versions ordered by version_number descending (newest first).
    """
    configs = (
        db.query(ResidualRiskMapConfig)
        .order_by(ResidualRiskMapConfig.version_number.desc())
        .all()
    )

    return [
        ResidualRiskMapListResponse(
            config_id=c.config_id,
            version_number=c.version_number,
            version_name=c.version_name,
            description=c.description,
            is_active=c.is_active,
            created_by_name=c.created_by.full_name if c.created_by else None,
            created_at=c.created_at,
        )
        for c in configs
    ]


@router.get("/versions/{version_id}", response_model=ResidualRiskMapResponse)
def get_residual_risk_map_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific residual risk map configuration version.
    """
    config = (
        db.query(ResidualRiskMapConfig)
        .filter(ResidualRiskMapConfig.config_id == version_id)
        .first()
    )

    if not config:
        raise HTTPException(status_code=404, detail="Configuration version not found")

    return ResidualRiskMapResponse(
        config_id=config.config_id,
        version_number=config.version_number,
        version_name=config.version_name,
        description=config.description,
        matrix_config=ResidualRiskMatrixConfig(**config.matrix_config),
        is_active=config.is_active,
        created_by_name=config.created_by.full_name if config.created_by else None,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("/", response_model=ResidualRiskMapResponse, status_code=status.HTTP_201_CREATED)
def create_residual_risk_map(
    data: ResidualRiskMapCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new residual risk map configuration.

    This will deactivate any existing active configuration and set the new one as active.
    Admin only.
    """
    # Get next version number
    max_version = db.query(func.max(ResidualRiskMapConfig.version_number)).scalar() or 0
    new_version_number = max_version + 1

    # Deactivate existing active config
    db.query(ResidualRiskMapConfig).filter(
        ResidualRiskMapConfig.is_active == True
    ).update({"is_active": False, "updated_at": utc_now()})

    # Create new config
    config = ResidualRiskMapConfig(
        version_number=new_version_number,
        version_name=data.version_name or f"Version {new_version_number}",
        description=data.description,
        matrix_config=data.matrix_config.model_dump(),
        is_active=True,
        created_by_user_id=current_user.user_id,
    )
    db.add(config)
    db.flush()

    # Audit log
    create_audit_log(
        db=db,
        entity_type="ResidualRiskMapConfig",
        entity_id=config.config_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "version_number": new_version_number,
            "version_name": config.version_name,
        }
    )

    db.commit()
    db.refresh(config)

    return ResidualRiskMapResponse(
        config_id=config.config_id,
        version_number=config.version_number,
        version_name=config.version_name,
        description=config.description,
        matrix_config=ResidualRiskMatrixConfig(**config.matrix_config),
        is_active=config.is_active,
        created_by_name=current_user.full_name,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.patch("/", response_model=ResidualRiskMapResponse)
def update_residual_risk_map(
    data: ResidualRiskMapUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update the residual risk map configuration.

    This creates a new version (current becomes inactive).
    Admin only.
    """
    # This is implemented as creating a new version
    return create_residual_risk_map(
        ResidualRiskMapCreate(
            version_name=data.version_name,
            description=data.description,
            matrix_config=data.matrix_config,
        ),
        db=db,
        current_user=current_user
    )


@router.post("/calculate", response_model=ResidualRiskCalculateResponse)
def calculate_residual_risk(
    data: ResidualRiskCalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate the residual risk given an inherent risk tier and scorecard outcome.

    Uses the currently active residual risk map configuration.
    """
    config = get_active_config(db)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active residual risk map configuration found"
        )

    matrix = config.matrix_config.get("matrix", {})

    # Look up the residual risk in the matrix
    row = matrix.get(data.inherent_risk_tier)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid inherent risk tier: {data.inherent_risk_tier}. "
                   f"Valid values: {list(matrix.keys())}"
        )

    residual_risk = row.get(data.scorecard_outcome)
    if not residual_risk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scorecard outcome: {data.scorecard_outcome}. "
                   f"Valid values: {list(row.keys())}"
        )

    return ResidualRiskCalculateResponse(
        inherent_risk_tier=data.inherent_risk_tier,
        scorecard_outcome=data.scorecard_outcome,
        residual_risk=residual_risk,
        config_version=config.version_number,
    )


# Utility function for use by other modules
def get_residual_risk(
    db: Session,
    inherent_risk_tier: str,
    scorecard_outcome: str
) -> Optional[str]:
    """
    Calculate residual risk for use by other modules.

    Returns None if no active config or invalid inputs.
    """
    config = get_active_config(db)
    if not config:
        return None

    matrix = config.matrix_config.get("matrix", {})
    row = matrix.get(inherent_risk_tier)
    if not row:
        return None

    return row.get(scorecard_outcome)
