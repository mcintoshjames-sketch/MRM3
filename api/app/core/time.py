"""Central time utilities for the application.

This module provides timezone-aware datetime utilities that maintain
backward compatibility with naive DateTime columns in the database
(TIMESTAMP WITHOUT TIME ZONE).
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Return current UTC time as a naive datetime object.

    This replaces datetime.utcnow() while maintaining backward compatibility
    with naive DateTime columns in the database (TIMESTAMP WITHOUT TIME ZONE).

    The function:
    1. Gets the current time in UTC (timezone-aware)
    2. Strips the timezone info to return a naive datetime

    This approach:
    - Avoids the DeprecationWarning from datetime.utcnow()
    - Maintains compatibility with existing naive datetime database columns
    - Prevents "can't compare offset-naive and offset-aware datetimes" errors

    Returns:
        datetime: Current UTC time as a naive datetime object
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
