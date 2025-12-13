"""Batch computation of revalidation status and risk penalty fields.

This module provides efficient batch computation of revalidation-related fields
for the Models list endpoint, avoiding N+1 query patterns.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.validation import ValidationPolicy, ValidationWorkflowSLA
from app.models.taxonomy import Taxonomy, TaxonomyValue


class RevalidationRefCache:
    """Cache for reference data used in batch computation."""

    def __init__(self, db: Session):
        self.policies: Dict[int, ValidationPolicy] = {}  # risk_tier_id -> policy
        self.past_due_buckets: List[Dict] = []  # sorted by min_days
        self.scorecard_order: List[str] = [
            'Green', 'Green-', 'Yellow+', 'Yellow', 'Yellow-', 'Red'
        ]
        self.workflow_sla_days: int = 0  # Total SLA days (assignment + begin_work + approval)
        self._load(db)

    def _load(self, db: Session):
        # Load ValidationPolicies (one per risk tier)
        policies = db.query(ValidationPolicy).all()
        for p in policies:
            self.policies[p.risk_tier_id] = p

        # Load Past Due Level buckets
        taxonomy = db.query(Taxonomy).filter(Taxonomy.name == 'Past Due Level').first()
        if taxonomy:
            buckets = db.query(TaxonomyValue).filter(
                TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
                TaxonomyValue.is_active == True
            ).order_by(TaxonomyValue.sort_order).all()
            for b in buckets:
                self.past_due_buckets.append({
                    'min_days': b.min_days,
                    'max_days': b.max_days,
                    'downgrade_notches': b.downgrade_notches or 0
                })

        # Load Workflow SLA for validation
        workflow_sla = db.query(ValidationWorkflowSLA).filter(
            ValidationWorkflowSLA.workflow_type == "Validation"
        ).first()
        if workflow_sla:
            self.workflow_sla_days = (workflow_sla.assignment_days or 0) + \
                                     (workflow_sla.begin_work_days or 0) + \
                                     (workflow_sla.approval_days or 0)

    def get_policy(self, risk_tier_id: Optional[int]) -> Optional[ValidationPolicy]:
        return self.policies.get(risk_tier_id) if risk_tier_id else None

    def get_penalty_notches(self, days_overdue: int) -> int:
        """Look up penalty notches from Past Due Level buckets."""
        for bucket in self.past_due_buckets:
            min_d = bucket['min_days'] if bucket['min_days'] is not None else float('-inf')
            max_d = bucket['max_days'] if bucket['max_days'] is not None else float('inf')
            if min_d <= days_overdue <= max_d:
                return bucket['downgrade_notches']
        return 0

    def downgrade_scorecard(self, scorecard: Optional[str], notches: int) -> Optional[str]:
        """Downgrade scorecard by N notches, capped at Red."""
        if not scorecard or notches <= 0:
            return scorecard
        try:
            idx = self.scorecard_order.index(scorecard)
            new_idx = min(idx + notches, len(self.scorecard_order) - 1)
            return self.scorecard_order[new_idx]
        except ValueError:
            return scorecard  # Unknown scorecard value


def batch_fetch_latest_validations(
    db: Session,
    model_ids: List[int]
) -> Dict[int, date]:
    """
    Fetch latest APPROVED validation completion_date for each model.
    Returns dict: model_id -> completion_date

    NOTE: ValidationRequest uses many-to-many with models via validation_request_models.
    The status is stored in current_status_id -> taxonomy_values.
    """
    if not model_ids:
        return {}

    # Join through validation_request_models table
    # and use current_status_id (the actual column name)
    sql = text("""
        WITH ranked AS (
            SELECT
                vrm.model_id,
                vr.completion_date,
                ROW_NUMBER() OVER (
                    PARTITION BY vrm.model_id
                    ORDER BY vr.completion_date DESC
                ) as rn
            FROM validation_requests vr
            JOIN validation_request_models vrm ON vr.request_id = vrm.request_id
            JOIN taxonomy_values tv ON vr.current_status_id = tv.value_id
            WHERE tv.code = 'APPROVED'
              AND vrm.model_id = ANY(:model_ids)
              AND vr.completion_date IS NOT NULL
        )
        SELECT model_id, completion_date
        FROM ranked
        WHERE rn = 1
    """)

    result = db.execute(sql, {'model_ids': model_ids})
    output = {}
    for row in result:
        # Handle both datetime and date objects
        completion = row.completion_date
        if hasattr(completion, 'date'):
            completion = completion.date()
        output[row.model_id] = completion
    return output


def compute_batch_revalidation_fields(
    db: Session,
    models: List[Any],  # List of Model ORM objects
    existing_results: List[Dict]  # Mutable list of result dicts
) -> None:
    """
    Compute revalidation fields for all models in batch.
    Mutates existing_results in place to add computed fields.

    Fields added:
    - last_validation_date: ISO date string of most recent APPROVED validation
    - next_validation_due_date: ISO date string of when next validation is due
    - days_until_validation_due: Integer days until due (negative if overdue)
    - validation_status: 'current', 'due_soon', 'overdue', or null
    - days_overdue: Integer days past grace period (0 if not overdue)
    - penalty_notches: Integer 0-3 based on Past Due Level buckets
    - adjusted_scorecard_outcome: Scorecard downgraded by penalty_notches
    """
    if not models:
        return

    # Load reference data (cached for this batch)
    cache = RevalidationRefCache(db)

    # Batch fetch latest validations - single SQL query for all models
    model_ids = [m.model_id for m in models]
    latest_validations = batch_fetch_latest_validations(db, model_ids)

    today = date.today()

    # Compute fields for each model
    for model, result in zip(models, existing_results):
        risk_tier_id = model.risk_tier_id
        policy = cache.get_policy(risk_tier_id)
        last_validation = latest_validations.get(model.model_id)

        # Initialize all fields with defaults
        result['last_validation_date'] = last_validation.isoformat() if last_validation else None
        result['next_validation_due_date'] = None
        result['days_until_validation_due'] = None
        result['validation_status'] = None
        result['days_overdue'] = 0
        result['penalty_notches'] = 0
        result['adjusted_scorecard_outcome'] = result.get('scorecard_outcome')

        if not policy:
            # No policy for this risk tier - can't compute revalidation status
            continue

        # Calculate next due date using relativedelta (matches existing logic)
        if last_validation:
            frequency_months = policy.frequency_months or 12
            grace_period_months = policy.grace_period_months or 0
            completion_lead_time = policy.model_change_lead_time_days or 0

            # Submission due = last_validation + frequency
            submission_due = last_validation + relativedelta(months=frequency_months)

            # Grace period end = submission_due + grace_period
            grace_period_end = submission_due + relativedelta(months=grace_period_months)

            # Validation due = grace_period_end + completion_lead_time + workflow_sla_days
            total_lead_time = completion_lead_time + cache.workflow_sla_days
            validation_due = grace_period_end + timedelta(days=total_lead_time)

            result['next_validation_due_date'] = validation_due.isoformat()

            days_until = (validation_due - today).days
            result['days_until_validation_due'] = days_until

            days_past_grace = (today - grace_period_end).days

            # Determine status based on days until validation due
            if days_until > 90:
                result['validation_status'] = 'current'
            elif days_until > 0:
                result['validation_status'] = 'due_soon'
            else:
                result['validation_status'] = 'overdue'

                # Days overdue is based on grace period end (matches existing logic)
                if days_past_grace > 0:
                    result['days_overdue'] = days_past_grace

                    # Calculate penalty only after grace period expires
                    penalty = cache.get_penalty_notches(days_past_grace)
                    result['penalty_notches'] = penalty

                    # Adjust scorecard outcome
                    original = result.get('scorecard_outcome')
                    result['adjusted_scorecard_outcome'] = cache.downgrade_scorecard(original, penalty)
        else:
            # No validation yet - new model, status is null (not penalized until validated)
            result['validation_status'] = None
