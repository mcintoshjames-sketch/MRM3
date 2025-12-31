"""Exception detection service for Model Exceptions tracking.

Provides detection functions for three exception types:
1. UNMITIGATED_PERFORMANCE - RED monitoring results persisting or without linked recommendations
2. OUTSIDE_INTENDED_PURPOSE - ATT_Q10_USE_RESTRICTIONS attestation answered "No"
3. USE_PRIOR_TO_VALIDATION - Model version deployed before validation approval

Also provides auto-close functions for exception resolution.
"""
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, exists, select

logger = logging.getLogger(__name__)

from app.core.time import utc_now
from app.models.model_exception import ModelException, ModelExceptionStatusHistory
from app.models.monitoring import MonitoringResult, MonitoringCycle, MonitoringPlanMetric
from app.models.attestation import AttestationResponse, AttestationRecord
from app.models.version_deployment_task import VersionDeploymentTask
from app.models.recommendation import Recommendation
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.validation import ValidationRequest


# Exception type constants
EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE = "UNMITIGATED_PERFORMANCE"
EXCEPTION_TYPE_OUTSIDE_INTENDED_PURPOSE = "OUTSIDE_INTENDED_PURPOSE"
EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION = "USE_PRIOR_TO_VALIDATION"

# Status constants
STATUS_OPEN = "OPEN"
STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
STATUS_CLOSED = "CLOSED"

# Closure reason codes
CLOSURE_REASON_NO_LONGER_EXCEPTION = "NO_LONGER_EXCEPTION"
CLOSURE_REASON_EXCEPTION_OVERRIDDEN = "EXCEPTION_OVERRIDDEN"
CLOSURE_REASON_OTHER = "OTHER"

# Attestation question code for use restrictions
ATT_Q10_USE_RESTRICTIONS_CODE = "ATT_Q10_USE_RESTRICTIONS"


def generate_exception_code(db: Session) -> str:
    """Generate a unique exception code in format EXC-YYYY-NNNNN.

    Uses the current year and an auto-incrementing sequence within that year.
    """
    current_year = utc_now().year
    prefix = f"EXC-{current_year}-"

    # Find the highest sequence number for this year
    max_code = db.query(func.max(ModelException.exception_code)).filter(
        ModelException.exception_code.like(f"{prefix}%")
    ).scalar()

    if max_code:
        # Extract sequence number and increment
        try:
            seq = int(max_code.split("-")[-1])
            next_seq = seq + 1
        except (ValueError, IndexError):
            next_seq = 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:05d}"


def get_closure_reason_value_id(db: Session, code: str) -> Optional[int]:
    """Get the taxonomy value ID for a closure reason code."""
    result = db.query(TaxonomyValue.value_id).join(Taxonomy).filter(
        Taxonomy.name == "Exception Closure Reason",
        TaxonomyValue.code == code
    ).scalar()
    return result


def _create_exception(
    db: Session,
    model_id: int,
    exception_type: str,
    description: str,
    monitoring_result_id: Optional[int] = None,
    attestation_response_id: Optional[int] = None,
    deployment_task_id: Optional[int] = None,
) -> ModelException:
    """Create a new exception and add initial status history."""
    exception = ModelException(
        exception_code=generate_exception_code(db),
        model_id=model_id,
        exception_type=exception_type,
        description=description,
        status=STATUS_OPEN,
        detected_at=utc_now(),
        monitoring_result_id=monitoring_result_id,
        attestation_response_id=attestation_response_id,
        deployment_task_id=deployment_task_id,
    )
    db.add(exception)
    db.flush()  # Get the exception_id

    # Add initial status history
    history = ModelExceptionStatusHistory(
        exception_id=exception.exception_id,
        old_status=None,
        new_status=STATUS_OPEN,
        changed_by_id=None,  # System-generated
        changed_at=utc_now(),
        notes="Exception detected automatically by system",
    )
    db.add(history)

    return exception


def _close_exception(
    db: Session,
    exception: ModelException,
    closure_narrative: str,
    closure_reason_code: str,
    user_id: Optional[int] = None,
    auto_closed: bool = True,
) -> bool:
    """Close an exception with narrative and reason.

    Returns True if closed successfully, False if closure reason lookup failed.
    """
    closure_reason_id = get_closure_reason_value_id(db, closure_reason_code)

    # Validate closure reason lookup succeeded
    if closure_reason_id is None:
        logger.warning(
            f"Cannot close exception {exception.exception_code}: "
            f"closure reason '{closure_reason_code}' not found in taxonomy. "
            f"Exception will remain open."
        )
        return False

    old_status = exception.status
    exception.status = STATUS_CLOSED
    exception.closed_at = utc_now()
    exception.closed_by_id = user_id
    exception.closure_narrative = closure_narrative
    exception.closure_reason_id = closure_reason_id
    exception.auto_closed = auto_closed
    exception.updated_at = utc_now()

    # Add status history
    history = ModelExceptionStatusHistory(
        exception_id=exception.exception_id,
        old_status=old_status,
        new_status=STATUS_CLOSED,
        changed_by_id=user_id,
        changed_at=utc_now(),
        notes=f"Auto-closed: {closure_narrative}" if auto_closed else closure_narrative,
    )
    db.add(history)
    return True


# =============================================================================
# Type 1: Unmitigated Performance Problem Detection
# =============================================================================

def detect_type1_unmitigated_performance(
    db: Session,
    model_id: Optional[int] = None,
) -> List[ModelException]:
    """Detect Type 1 exceptions: RED monitoring results without recommendations.

    Triggers when:
    - RED monitoring result exists without a linked recommendation for that model/cycle
    - RED monitoring result persists across consecutive monitoring cycles
    - ONLY considers results from APPROVED monitoring cycles (not cycles still in progress)

    Args:
        db: Database session
        model_id: Optional - limit detection to a specific model

    Returns:
        List of newly created ModelException objects
    """
    created_exceptions = []

    # Query RED monitoring results - ONLY from APPROVED cycles
    # Before cycle is approved, team may still be creating recommendations
    query = db.query(MonitoringResult).join(
        MonitoringCycle, MonitoringResult.cycle_id == MonitoringCycle.cycle_id
    ).filter(
        MonitoringResult.calculated_outcome == "RED",
        MonitoringCycle.status == "APPROVED"
    )

    if model_id:
        query = query.filter(MonitoringResult.model_id == model_id)

    red_results = query.all()

    for result in red_results:
        # Check if exception already exists for this result
        existing = db.query(ModelException).filter(
            ModelException.monitoring_result_id == result.result_id
        ).first()

        if existing:
            continue

        # Determine the model_id - either from result directly or via the plan
        result_model_id = result.model_id
        if not result_model_id:
            # If result doesn't have model_id, get from the monitoring plan
            # For plan-level metrics, we need to check all models in the plan
            continue  # Skip plan-level results without explicit model

        # Check if there's an ACTIVE recommendation for this model from this cycle
        # AND for the same metric (plan_metric_id).
        # A recommendation must be linked to the specific metric to count as addressing the issue.
        active_rec_statuses_subq = db.query(TaxonomyValue.value_id).join(Taxonomy).filter(
            Taxonomy.name == "Recommendation Status",
            TaxonomyValue.code.notin_(['CLOSED', 'CANCELLED', 'COMPLETED'])
        ).subquery()

        has_active_recommendation = db.query(exists().where(
            and_(
                Recommendation.model_id == result_model_id,
                Recommendation.monitoring_cycle_id == result.cycle_id,
                Recommendation.plan_metric_id == result.plan_metric_id,
                Recommendation.current_status_id.in_(select(active_rec_statuses_subq))
            )
        )).scalar()

        if not has_active_recommendation:
            # Create exception for RED without recommendation
            exception = _create_exception(
                db=db,
                model_id=result_model_id,
                exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
                description=(
                    f"RED monitoring result detected for metric without a linked recommendation. "
                    f"Monitoring result ID: {result.result_id}, Cycle ID: {result.cycle_id}"
                ),
                monitoring_result_id=result.result_id,
            )
            created_exceptions.append(exception)

    return created_exceptions


def detect_type1_persistent_red(
    db: Session,
    current_cycle: MonitoringCycle,
    model_id: int,
    metric_id: int,
) -> Optional[ModelException]:
    """Detect Type 1 exception for RED persisting across consecutive cycles.

    Called when a RED result is recorded - checks if previous cycle also had RED
    for the same model/metric combination.

    Args:
        db: Database session
        current_cycle: The current monitoring cycle
        model_id: The model ID to check
        metric_id: The metric ID (plan_metric_id) to check

    Returns:
        Newly created ModelException if persistence detected, None otherwise
    """
    # Get the current RED result
    current_red = db.query(MonitoringResult).filter(
        MonitoringResult.cycle_id == current_cycle.cycle_id,
        MonitoringResult.model_id == model_id,
        MonitoringResult.plan_metric_id == metric_id,
        MonitoringResult.calculated_outcome == "RED"
    ).first()

    if not current_red:
        return None

    # Check if exception already exists
    existing = db.query(ModelException).filter(
        ModelException.monitoring_result_id == current_red.result_id
    ).first()

    if existing:
        return None

    # Find previous APPROVED cycle for this plan
    # Only compare against finalized cycles, not cycles still in progress
    previous_cycle = db.query(MonitoringCycle).filter(
        MonitoringCycle.plan_id == current_cycle.plan_id,
        MonitoringCycle.cycle_id < current_cycle.cycle_id,
        MonitoringCycle.status == "APPROVED"
    ).order_by(MonitoringCycle.cycle_id.desc()).first()

    if not previous_cycle:
        return None

    # Check if previous APPROVED cycle had RED for same model/metric
    previous_red = db.query(MonitoringResult).filter(
        MonitoringResult.cycle_id == previous_cycle.cycle_id,
        MonitoringResult.model_id == model_id,
        MonitoringResult.plan_metric_id == metric_id,
        MonitoringResult.calculated_outcome == "RED"
    ).first()

    if previous_red:
        # RED persists - create exception
        exception = _create_exception(
            db=db,
            model_id=model_id,
            exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
            description=(
                f"RED monitoring result persisting across consecutive cycles. "
                f"Current cycle: {current_cycle.cycle_id}, Previous cycle: {previous_cycle.cycle_id}, "
                f"Metric ID: {metric_id}"
            ),
            monitoring_result_id=current_red.result_id,
        )
        return exception

    return None


def detect_type1_persistent_red_for_model(
    db: Session,
    model_id: int,
) -> List[ModelException]:
    """Batch detection of Type 1 persistent RED for a model (for scan endpoints).

    Finds all current RED results for the model and checks if each has persisted
    from a previous cycle.

    Args:
        db: Database session
        model_id: The model ID to scan

    Returns:
        List of newly created exceptions
    """
    created_exceptions = []

    # Find all current RED results for this model
    # Group by cycle to process each cycle's RED results
    from app.models.monitoring import MonitoringPlan

    # Get the latest cycle for each plan associated with this model
    subq = db.query(
        MonitoringCycle.plan_id,
        func.max(MonitoringCycle.cycle_id).label('latest_cycle_id')
    ).join(
        MonitoringPlan, MonitoringCycle.plan_id == MonitoringPlan.plan_id
    ).filter(
        MonitoringPlan.models.any(model_id=model_id)
    ).group_by(MonitoringCycle.plan_id).subquery()

    # Get RED results in latest cycles for this model
    red_results = db.query(MonitoringResult).join(
        MonitoringCycle, MonitoringResult.cycle_id == MonitoringCycle.cycle_id
    ).join(
        subq, and_(
            MonitoringCycle.plan_id == subq.c.plan_id,
            MonitoringCycle.cycle_id == subq.c.latest_cycle_id
        )
    ).filter(
        MonitoringResult.model_id == model_id,
        MonitoringResult.calculated_outcome == "RED"
    ).all()

    for result in red_results:
        cycle = db.query(MonitoringCycle).filter(
            MonitoringCycle.cycle_id == result.cycle_id
        ).first()

        if cycle:
            exc = detect_type1_persistent_red(
                db=db,
                current_cycle=cycle,
                model_id=model_id,
                metric_id=result.plan_metric_id,
            )
            if exc:
                created_exceptions.append(exc)

    return created_exceptions


def autoclose_type1_on_improved_result(
    db: Session,
    result: MonitoringResult,
) -> List[ModelException]:
    """Auto-close Type 1 exceptions when metric improves from RED to GREEN/YELLOW.

    Called when a new MonitoringResult is recorded. If the result is GREEN or YELLOW,
    check for open Type 1 exceptions on the same model/metric and auto-close them.

    Args:
        db: Database session
        result: The newly recorded MonitoringResult

    Returns:
        List of auto-closed exceptions
    """
    if result.calculated_outcome not in ("GREEN", "YELLOW"):
        return []

    if not result.model_id:
        return []

    closed_exceptions = []

    # Find open Type 1 exceptions for this model
    open_exceptions = db.query(ModelException).filter(
        ModelException.model_id == result.model_id,
        ModelException.exception_type == EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
        ModelException.status.in_([STATUS_OPEN, STATUS_ACKNOWLEDGED])
    ).all()

    for exception in open_exceptions:
        if exception.monitoring_result_id:
            # Check if this exception's result is for the same metric
            orig_result = db.query(MonitoringResult).filter(
                MonitoringResult.result_id == exception.monitoring_result_id
            ).first()

            if orig_result and orig_result.plan_metric_id == result.plan_metric_id:
                # Same metric - auto-close
                closed = _close_exception(
                    db=db,
                    exception=exception,
                    closure_narrative=f"Metric returned to {result.calculated_outcome} in cycle {result.cycle_id}",
                    closure_reason_code=CLOSURE_REASON_NO_LONGER_EXCEPTION,
                    auto_closed=True,
                )
                if closed:
                    closed_exceptions.append(exception)

    return closed_exceptions


def close_type1_exception_for_result(
    db: Session,
    result: MonitoringResult,
    new_outcome: str,
) -> int:
    """Close Type 1 exceptions tied to a specific monitoring result."""
    if not result.result_id:
        return 0

    exceptions = db.query(ModelException).filter(
        ModelException.monitoring_result_id == result.result_id,
        ModelException.exception_type == EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
        ModelException.status.in_([STATUS_OPEN, STATUS_ACKNOWLEDGED])
    ).all()

    closed_count = 0
    for exception in exceptions:
        closed = _close_exception(
            db=db,
            exception=exception,
            closure_narrative=f"Monitoring result updated to {new_outcome} for cycle {result.cycle_id}",
            closure_reason_code=CLOSURE_REASON_NO_LONGER_EXCEPTION,
            auto_closed=True,
        )
        if closed:
            closed_count += 1

    return closed_count


def ensure_type1_exception_for_result(
    db: Session,
    result: MonitoringResult,
) -> Optional[ModelException]:
    """Create a Type 1 exception for a RED monitoring result if none exists."""
    if result.calculated_outcome != "RED":
        return None
    if not result.model_id:
        return None

    cycle = result.cycle
    if not cycle:
        cycle = db.query(MonitoringCycle).filter(
            MonitoringCycle.cycle_id == result.cycle_id
        ).first()
    if not cycle or cycle.status != "APPROVED":
        return None

    existing = db.query(ModelException).filter(
        ModelException.monitoring_result_id == result.result_id
    ).first()
    if existing:
        return None

    active_rec_statuses_subq = db.query(TaxonomyValue.value_id).join(Taxonomy).filter(
        Taxonomy.name == "Recommendation Status",
        TaxonomyValue.code.notin_(['CLOSED', 'CANCELLED', 'COMPLETED'])
    ).subquery()

    has_active_recommendation = db.query(exists().where(
        and_(
            Recommendation.model_id == result.model_id,
            Recommendation.monitoring_cycle_id == result.cycle_id,
            Recommendation.plan_metric_id == result.plan_metric_id,
            Recommendation.current_status_id.in_(select(active_rec_statuses_subq))
        )
    )).scalar()

    if has_active_recommendation:
        return None

    return _create_exception(
        db=db,
        model_id=result.model_id,
        exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
        description=(
            "RED monitoring result detected for metric without a linked recommendation. "
            f"Monitoring result ID: {result.result_id}, Cycle ID: {result.cycle_id}"
        ),
        monitoring_result_id=result.result_id,
    )


# =============================================================================
# Type 2: Outside Intended Purpose Detection
# =============================================================================

def detect_type2_outside_intended_purpose(
    db: Session,
    model_id: Optional[int] = None,
) -> List[ModelException]:
    """Detect Type 2 exceptions: ATT_Q10_USE_RESTRICTIONS answered "No".

    Triggers when an attestation response indicates the model is being used
    outside its intended purpose (answer=False to ATT_Q10_USE_RESTRICTIONS).

    Args:
        db: Database session
        model_id: Optional - limit detection to a specific model

    Returns:
        List of newly created ModelException objects
    """
    created_exceptions = []

    # Find the ATT_Q10_USE_RESTRICTIONS question
    question = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Attestation Question",
        TaxonomyValue.code == ATT_Q10_USE_RESTRICTIONS_CODE
    ).first()

    if not question:
        # Question not yet seeded - return empty
        return created_exceptions

    # Query responses with answer=False
    query = db.query(AttestationResponse).join(AttestationRecord).filter(
        AttestationResponse.question_id == question.value_id,
        AttestationResponse.answer == False  # noqa: E712
    )

    if model_id:
        query = query.filter(AttestationRecord.model_id == model_id)

    no_responses = query.all()

    for response in no_responses:
        # Check if exception already exists for this response
        existing = db.query(ModelException).filter(
            ModelException.attestation_response_id == response.response_id
        ).first()

        if existing:
            continue

        # Get the model_id from the attestation record
        attestation = response.attestation
        response_model_id = attestation.model_id

        # Create exception
        exception = _create_exception(
            db=db,
            model_id=response_model_id,
            exception_type=EXCEPTION_TYPE_OUTSIDE_INTENDED_PURPOSE,
            description=(
                f"Model reported as being used outside its intended purpose. "
                f"Attestation ID: {attestation.attestation_id}, Cycle ID: {attestation.cycle_id}"
            ),
            attestation_response_id=response.response_id,
        )
        created_exceptions.append(exception)

    return created_exceptions


def detect_type2_for_response(
    db: Session,
    response: AttestationResponse,
) -> Optional[ModelException]:
    """Detect Type 2 exception for a specific attestation response.

    Called immediately when an attestation is submitted.

    Args:
        db: Database session
        response: The attestation response to check

    Returns:
        Newly created ModelException if applicable, None otherwise
    """
    # Check if this is the use restrictions question
    question = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == response.question_id
    ).first()

    if not question or question.code != ATT_Q10_USE_RESTRICTIONS_CODE:
        return None

    # Only trigger on "No" answer
    if response.answer:
        return None

    # Check if exception already exists
    existing = db.query(ModelException).filter(
        ModelException.attestation_response_id == response.response_id
    ).first()

    if existing:
        return None

    # Get model_id from attestation
    attestation = response.attestation

    # Create exception
    exception = _create_exception(
        db=db,
        model_id=attestation.model_id,
        exception_type=EXCEPTION_TYPE_OUTSIDE_INTENDED_PURPOSE,
        description=(
            f"Model reported as being used outside its intended purpose. "
            f"Attestation ID: {attestation.attestation_id}, Cycle ID: {attestation.cycle_id}"
        ),
        attestation_response_id=response.response_id,
    )
    return exception


# Type 2 has NO auto-close - must be manually closed by Admin
# This is intentional as per the plan


# =============================================================================
# Type 3: Use Prior to Validation Detection
# =============================================================================

def detect_type3_use_prior_to_validation(
    db: Session,
    model_id: Optional[int] = None,
) -> List[ModelException]:
    """Detect Type 3 exceptions: Deployment confirmed before validation approval.

    Triggers when a VersionDeploymentTask has:
    - deployed_before_validation_approved = True
    - status = "CONFIRMED"

    Args:
        db: Database session
        model_id: Optional - limit detection to a specific model

    Returns:
        List of newly created ModelException objects
    """
    created_exceptions = []

    # Query deployment tasks that deployed before validation
    query = db.query(VersionDeploymentTask).filter(
        VersionDeploymentTask.deployed_before_validation_approved == True,  # noqa: E712
        VersionDeploymentTask.status == "CONFIRMED"
    )

    if model_id:
        query = query.filter(VersionDeploymentTask.model_id == model_id)

    tasks = query.all()

    for task in tasks:
        # Check if exception already exists for this task
        existing = db.query(ModelException).filter(
            ModelException.deployment_task_id == task.task_id
        ).first()

        if existing:
            continue

        # Create exception
        exception = _create_exception(
            db=db,
            model_id=task.model_id,
            exception_type=EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION,
            description=(
                f"Model version deployed before validation was approved. "
                f"Deployment task ID: {task.task_id}, Version ID: {task.version_id}"
                + (f", Reason: {task.validation_override_reason}" if task.validation_override_reason else "")
            ),
            deployment_task_id=task.task_id,
        )
        created_exceptions.append(exception)

    return created_exceptions


def detect_type3_for_deployment_task(
    db: Session,
    task: VersionDeploymentTask,
) -> Optional[ModelException]:
    """Detect Type 3 exception for a specific deployment task.

    Called immediately when a deployment is confirmed.

    Args:
        db: Database session
        task: The deployment task to check

    Returns:
        Newly created ModelException if applicable, None otherwise
    """
    # Only trigger if deployed before validation and status is CONFIRMED
    if not task.deployed_before_validation_approved:
        return None

    if task.status != "CONFIRMED":
        return None

    # Check if exception already exists
    existing = db.query(ModelException).filter(
        ModelException.deployment_task_id == task.task_id
    ).first()

    if existing:
        return None

    # Create exception
    exception = _create_exception(
        db=db,
        model_id=task.model_id,
        exception_type=EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION,
        description=(
            f"Model version deployed before validation was approved. "
            f"Deployment task ID: {task.task_id}, Version ID: {task.version_id}"
            + (f", Reason: {task.validation_override_reason}" if task.validation_override_reason else "")
        ),
        deployment_task_id=task.task_id,
    )
    return exception


# Interim validation type codes that do NOT auto-close Type 3 exceptions
# Uses immutable 'code' field (not 'label') for reliable matching
INTERIM_VALIDATION_TYPES = {"INTERIM"}


def autoclose_type3_on_full_validation_approved(
    db: Session,
    validation_request: ValidationRequest,
) -> List[ModelException]:
    """Auto-close Type 3 exceptions when FULL validation is approved.

    IMPORTANT: Only FULL validations (Initial, Comprehensive, Targeted Review)
    close Type 3 exceptions. Interim validations do NOT close them.

    Called when a ValidationRequest transitions to APPROVED status.

    Args:
        db: Database session
        validation_request: The validation request that was approved

    Returns:
        List of auto-closed exceptions
    """
    # Check if this is an interim validation - if so, do NOT auto-close
    if validation_request.validation_type:
        # Get the validation type code from taxonomy
        if validation_request.validation_type_id:
            type_value = db.query(TaxonomyValue).filter(
                TaxonomyValue.value_id == validation_request.validation_type_id
            ).first()
            if type_value and type_value.code in INTERIM_VALIDATION_TYPES:
                # Interim validation - do not auto-close
                return []

    closed_exceptions = []

    # Get model IDs from the validation request
    # ValidationRequest can cover multiple models via validation_request_models
    model_ids = set()

    # Direct model_id if present
    if hasattr(validation_request, 'model_id') and validation_request.model_id:
        model_ids.add(validation_request.model_id)

    # Models from the many-to-many relationship
    if hasattr(validation_request, 'models'):
        for model in validation_request.models:
            model_ids.add(model.model_id)

    if not model_ids:
        return []

    # Find open Type 3 exceptions for these models
    open_exceptions = db.query(ModelException).filter(
        ModelException.model_id.in_(model_ids),
        ModelException.exception_type == EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION,
        ModelException.status.in_([STATUS_OPEN, STATUS_ACKNOWLEDGED])
    ).all()

    completion_date = validation_request.completion_date or utc_now().date()

    for exception in open_exceptions:
        closed = _close_exception(
            db=db,
            exception=exception,
            closure_narrative=f"Full validation approved on {completion_date}. Validation request ID: {validation_request.request_id}",
            closure_reason_code=CLOSURE_REASON_NO_LONGER_EXCEPTION,
            auto_closed=True,
        )
        if closed:
            closed_exceptions.append(exception)

    return closed_exceptions


# =============================================================================
# Batch Detection Functions
# =============================================================================

def detect_all_exceptions_for_model(
    db: Session,
    model_id: int,
) -> Tuple[List[ModelException], List[ModelException], List[ModelException]]:
    """Run all exception detection for a specific model.

    Args:
        db: Database session
        model_id: The model ID to check

    Returns:
        Tuple of (type1_exceptions, type2_exceptions, type3_exceptions)
    """
    type1 = detect_type1_unmitigated_performance(db, model_id)
    type2 = detect_type2_outside_intended_purpose(db, model_id)
    type3 = detect_type3_use_prior_to_validation(db, model_id)

    return type1, type2, type3


def detect_all_exceptions(
    db: Session,
) -> Tuple[List[ModelException], List[ModelException], List[ModelException]]:
    """Run all exception detection across all models (batch).

    Args:
        db: Database session

    Returns:
        Tuple of (type1_exceptions, type2_exceptions, type3_exceptions)
    """
    type1 = detect_type1_unmitigated_performance(db)
    type2 = detect_type2_outside_intended_purpose(db)
    type3 = detect_type3_use_prior_to_validation(db)

    return type1, type2, type3


# =============================================================================
# Helper Functions for API
# =============================================================================

def acknowledge_exception(
    db: Session,
    exception: ModelException,
    user_id: int,
    notes: Optional[str] = None,
) -> ModelException:
    """Acknowledge an exception (transition from OPEN to ACKNOWLEDGED).

    Args:
        db: Database session
        exception: The exception to acknowledge
        user_id: The admin user acknowledging
        notes: Optional acknowledgment notes

    Returns:
        Updated exception

    Raises:
        ValueError: If exception is not in OPEN status
    """
    if exception.status != STATUS_OPEN:
        raise ValueError(f"Cannot acknowledge exception in status '{exception.status}'. Must be '{STATUS_OPEN}'.")

    old_status = exception.status
    exception.status = STATUS_ACKNOWLEDGED
    exception.acknowledged_by_id = user_id
    exception.acknowledged_at = utc_now()
    exception.acknowledgment_notes = notes
    exception.updated_at = utc_now()

    # Add status history
    history = ModelExceptionStatusHistory(
        exception_id=exception.exception_id,
        old_status=old_status,
        new_status=STATUS_ACKNOWLEDGED,
        changed_by_id=user_id,
        changed_at=utc_now(),
        notes=notes,
    )
    db.add(history)

    return exception


def close_exception_manually(
    db: Session,
    exception: ModelException,
    user_id: int,
    closure_narrative: str,
    closure_reason_id: int,
) -> ModelException:
    """Manually close an exception (Admin action).

    Args:
        db: Database session
        exception: The exception to close
        user_id: The admin user closing
        closure_narrative: Required narrative (min 10 chars)
        closure_reason_id: FK to taxonomy_values for closure reason

    Returns:
        Updated exception

    Raises:
        ValueError: If exception already closed or invalid inputs
    """
    if exception.status == STATUS_CLOSED:
        raise ValueError("Exception is already closed.")

    if not closure_narrative or len(closure_narrative.strip()) < 10:
        raise ValueError("Closure narrative must be at least 10 characters.")

    old_status = exception.status
    exception.status = STATUS_CLOSED
    exception.closed_at = utc_now()
    exception.closed_by_id = user_id
    exception.closure_narrative = closure_narrative.strip()
    exception.closure_reason_id = closure_reason_id
    exception.auto_closed = False
    exception.updated_at = utc_now()

    # Add status history
    history = ModelExceptionStatusHistory(
        exception_id=exception.exception_id,
        old_status=old_status,
        new_status=STATUS_CLOSED,
        changed_by_id=user_id,
        changed_at=utc_now(),
        notes=closure_narrative,
    )
    db.add(history)

    return exception
