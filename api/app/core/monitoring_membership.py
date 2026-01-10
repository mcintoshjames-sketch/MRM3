"""Monitoring plan membership ledger writer."""
from __future__ import annotations

from typing import Iterable, List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.monitoring import (
    MonitoringPlan,
    MonitoringPlanMembership,
    MonitoringCycle,
    MonitoringCycleStatus,
    monitoring_plan_models,
)


TRANSFER_BLOCKING_STATUSES = {
    MonitoringCycleStatus.DATA_COLLECTION.value,
    MonitoringCycleStatus.UNDER_REVIEW.value,
    MonitoringCycleStatus.PENDING_APPROVAL.value,
    MonitoringCycleStatus.ON_HOLD.value,
}


class MonitoringMembershipService:
    """Single-writer service for monitoring plan memberships."""

    def __init__(self, db: Session):
        self.db = db

    def _lock_plans(self, plan_ids: Iterable[int]) -> None:
        plan_id_list = sorted({pid for pid in plan_ids if pid is not None})
        if not plan_id_list:
            return
        self.db.query(MonitoringPlan).filter(
            MonitoringPlan.plan_id.in_(plan_id_list)
        ).order_by(MonitoringPlan.plan_id.asc()).with_for_update().all()

    def _lock_active_memberships(self, model_ids: Iterable[int]) -> List[MonitoringPlanMembership]:
        model_id_list = sorted({mid for mid in model_ids})
        if not model_id_list:
            return []
        return self.db.query(MonitoringPlanMembership).filter(
            MonitoringPlanMembership.model_id.in_(model_id_list),
            MonitoringPlanMembership.effective_to.is_(None),
        ).order_by(MonitoringPlanMembership.model_id.asc()).with_for_update().all()

    def _assert_transfer_allowed(self, plan_id: int) -> None:
        blocking = self.db.query(MonitoringCycle.cycle_id).filter(
            MonitoringCycle.plan_id == plan_id,
            MonitoringCycle.status.in_(list(TRANSFER_BLOCKING_STATUSES)),
        ).first()
        if blocking:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer not allowed: plan has an active cycle",
            )

    def _add_projection(self, plan_id: int, model_id: int) -> None:
        self.db.execute(
            monitoring_plan_models.delete().where(
                monitoring_plan_models.c.plan_id == plan_id,
                monitoring_plan_models.c.model_id == model_id,
            )
        )
        self.db.execute(
            monitoring_plan_models.insert().values(
                plan_id=plan_id,
                model_id=model_id,
            )
        )

    def _remove_projection(self, plan_id: int, model_id: int) -> None:
        self.db.execute(
            monitoring_plan_models.delete().where(
                monitoring_plan_models.c.plan_id == plan_id,
                monitoring_plan_models.c.model_id == model_id,
            )
        )

    def _mark_plans_dirty(self, plan_ids: Set[int]) -> None:
        if not plan_ids:
            return
        self.db.query(MonitoringPlan).filter(
            MonitoringPlan.plan_id.in_(sorted(plan_ids))
        ).update({"is_dirty": True}, synchronize_session=False)

    def replace_plan_models(
        self,
        plan_id: int,
        model_ids: List[int],
        changed_by_user_id: Optional[int],
        reason: Optional[str] = None,
    ) -> None:
        desired_model_ids = {mid for mid in model_ids}

        current_memberships = self.db.query(MonitoringPlanMembership).filter(
            MonitoringPlanMembership.plan_id == plan_id,
            MonitoringPlanMembership.effective_to.is_(None),
        ).all()
        current_model_ids = {membership.model_id for membership in current_memberships}

        to_add = desired_model_ids - current_model_ids
        to_remove = current_model_ids - desired_model_ids

        if not to_add and not to_remove:
            return

        # Identify source plans for models we need to add (for locking order).
        existing_add_memberships = self.db.query(MonitoringPlanMembership).filter(
            MonitoringPlanMembership.model_id.in_(sorted(to_add)),
            MonitoringPlanMembership.effective_to.is_(None),
        ).all() if to_add else []

        plan_ids_to_lock = {plan_id}
        plan_ids_to_lock.update(
            membership.plan_id
            for membership in existing_add_memberships
            if membership.plan_id != plan_id
        )
        self._lock_plans(plan_ids_to_lock)

        # Lock affected memberships after plans are locked.
        locked_memberships = self._lock_active_memberships(to_add | to_remove)
        membership_by_model = {membership.model_id: membership for membership in locked_memberships}

        # Sanity check: ensure all membership plans are in lock set.
        unlocked_plan_ids = {
            membership.plan_id
            for membership in membership_by_model.values()
            if membership.plan_id not in plan_ids_to_lock
        }
        if unlocked_plan_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Membership changed during update; please retry",
            )

        now = utc_now()
        dirty_plan_ids: Set[int] = set()

        for model_id in sorted(to_remove):
            membership = membership_by_model.get(model_id)
            if not membership or membership.plan_id != plan_id:
                continue
            membership.effective_to = now
            membership.updated_at = now
            self._remove_projection(plan_id, model_id)
            dirty_plan_ids.add(plan_id)

        for model_id in sorted(to_add):
            membership = membership_by_model.get(model_id)
            if membership and membership.plan_id != plan_id:
                self._assert_transfer_allowed(membership.plan_id)
                membership.effective_to = now
                membership.updated_at = now
                self._remove_projection(membership.plan_id, model_id)
                dirty_plan_ids.add(membership.plan_id)

            if membership and membership.plan_id == plan_id:
                continue

            self.db.add(MonitoringPlanMembership(
                model_id=model_id,
                plan_id=plan_id,
                effective_from=now,
                effective_to=None,
                reason=reason,
                changed_by_user_id=changed_by_user_id,
                created_at=now,
                updated_at=now,
            ))
            self._add_projection(plan_id, model_id)
            dirty_plan_ids.add(plan_id)

        self._mark_plans_dirty(dirty_plan_ids)

    def transfer_model(
        self,
        model_id: int,
        to_plan_id: int,
        changed_by_user_id: Optional[int],
        reason: Optional[str] = None,
    ) -> MonitoringPlanMembership:
        active_membership = self.db.query(MonitoringPlanMembership).filter(
            MonitoringPlanMembership.model_id == model_id,
            MonitoringPlanMembership.effective_to.is_(None),
        ).first()

        source_plan_id = active_membership.plan_id if active_membership else None
        plan_ids_to_lock = {to_plan_id}
        if source_plan_id is not None:
            plan_ids_to_lock.add(source_plan_id)

        self._lock_plans(plan_ids_to_lock)
        locked_memberships = self._lock_active_memberships([model_id])
        membership = locked_memberships[0] if locked_memberships else None

        if membership and membership.plan_id not in plan_ids_to_lock:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Membership changed during transfer; please retry",
            )

        if membership and membership.plan_id == to_plan_id:
            return membership

        now = utc_now()
        dirty_plan_ids: Set[int] = {to_plan_id}

        if membership:
            self._assert_transfer_allowed(membership.plan_id)
            membership.effective_to = now
            membership.updated_at = now
            self._remove_projection(membership.plan_id, model_id)
            dirty_plan_ids.add(membership.plan_id)

        new_membership = MonitoringPlanMembership(
            model_id=model_id,
            plan_id=to_plan_id,
            effective_from=now,
            effective_to=None,
            reason=reason,
            changed_by_user_id=changed_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(new_membership)
        self._add_projection(to_plan_id, model_id)
        self._mark_plans_dirty(dirty_plan_ids)

        return new_membership
