"""LOB (Line of Business) utility functions."""
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.lob import LOBUnit
    from app.models.user import User

# LOB4 level in the hierarchy (1=SBU, 2=LOB1, 3=LOB2, 4=LOB3, 5=LOB4)
LOB4_LEVEL = 5


def get_lob_rollup_name(lob: Optional["LOBUnit"], target_level: int = LOB4_LEVEL) -> Optional[str]:
    """
    Get LOB name rolled up to the target hierarchy level.

    If user's LOB level > target_level, traverse up to find ancestor at target_level.
    If user's LOB level <= target_level, return the user's actual LOB name.

    Args:
        lob: The LOBUnit to roll up
        target_level: The hierarchy level to roll up to (default: 5 = LOB4)

    Returns:
        The LOB name at the rolled-up level, or None if no LOB assigned
    """
    if lob is None:
        return None

    # If already at or above target level, return current LOB name
    if lob.level <= target_level:
        return lob.name

    # Traverse up to find ancestor at target level
    current = lob
    while current is not None:
        if current.level == target_level:
            return current.name
        current = current.parent

    # Fallback: return the original LOB name (shouldn't happen with proper data)
    return lob.name


def get_user_lob_rollup_name(user: Optional["User"], target_level: int = LOB4_LEVEL) -> Optional[str]:
    """
    Convenience function to get LOB rollup name directly from a User.

    Args:
        user: The User whose LOB should be rolled up
        target_level: The hierarchy level to roll up to (default: 5 = LOB4)

    Returns:
        The LOB name at the rolled-up level, or None if user is None or has no LOB
    """
    if user is None:
        return None
    return get_lob_rollup_name(user.lob, target_level)
