"""Team utility functions for LOB-to-team resolution."""
from typing import Dict, Optional, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.lob import LOBUnit
from app.models.team import Team
from app.models.model import Model
from app.models.user import User


def _build_lob_team_map_python(db: Session) -> Dict[int, Optional[int]]:
    """Python fallback for LOB→Team resolution (used for non-Postgres dialects)."""
    lobs = db.query(LOBUnit.lob_id, LOBUnit.parent_id, LOBUnit.team_id).all()
    lob_map = {lob_id: (parent_id, team_id) for lob_id, parent_id, team_id in lobs}
    resolved: Dict[int, Optional[int]] = {}

    def resolve(lob_id: int, path: Optional[set] = None) -> Optional[int]:
        if lob_id in resolved:
            return resolved[lob_id]
        if lob_id not in lob_map:
            resolved[lob_id] = None
            return None
        if path is None:
            path = set()
        if lob_id in path:
            resolved[lob_id] = None
            return None

        parent_id, team_id = lob_map[lob_id]
        if team_id is not None:
            resolved[lob_id] = team_id
            return team_id

        path.add(lob_id)
        resolved_team = resolve(parent_id, path) if parent_id else None
        resolved[lob_id] = resolved_team
        path.remove(lob_id)
        return resolved_team

    for lob_id in lob_map.keys():
        resolve(lob_id)

    return resolved


def build_lob_team_map(db: Session) -> Dict[int, Optional[int]]:
    """
    Build mapping of LOB ID → effective Team ID using "closest ancestor wins".

    Uses a recursive CTE for Postgres, with a Python fallback for other dialects.
    """
    if db.bind and db.bind.dialect.name != "postgresql":
        return _build_lob_team_map_python(db)

    sql = text(
        """
        WITH RECURSIVE lob_chain AS (
            SELECT lob_id, parent_id, team_id, ARRAY[lob_id] AS path
            FROM lob_units
            UNION ALL
            SELECT c.lob_id, p.parent_id,
                   COALESCE(c.team_id, p.team_id) AS team_id,
                   c.path || p.lob_id AS path
            FROM lob_chain c
            JOIN lob_units p ON c.parent_id = p.lob_id
            WHERE NOT p.lob_id = ANY(c.path)
        )
        SELECT DISTINCT ON (lob_id) lob_id, team_id
        FROM lob_chain
        ORDER BY lob_id, array_length(path, 1) DESC;
        """
    )

    results = db.execute(sql).all()
    return {row.lob_id: row.team_id for row in results}


def get_effective_team_for_lob(lob_team_map: Dict[int, Optional[int]], lob_id: int) -> Optional[int]:
    """Lookup effective team from pre-built map."""
    return lob_team_map.get(lob_id)


def get_models_team_map(db: Session, model_ids: List[int]) -> Dict[int, Optional[dict]]:
    """
    Bulk resolve teams for a list of models.
    Returns mapping of model_id → team dict (or None).
    """
    if not model_ids:
        return {}

    lob_team_map = build_lob_team_map(db)

    owner_lobs = db.query(Model.model_id, User.lob_id).join(
        User, Model.owner_id == User.user_id
    ).filter(Model.model_id.in_(model_ids)).all()

    team_ids = set()
    model_team_ids: Dict[int, Optional[int]] = {}
    for model_id, lob_id in owner_lobs:
        team_id = lob_team_map.get(lob_id)
        model_team_ids[model_id] = team_id
        if team_id:
            team_ids.add(team_id)

    teams = db.query(Team).filter(Team.team_id.in_(team_ids)).all() if team_ids else []
    team_map = {team.team_id: {"team_id": team.team_id, "name": team.name} for team in teams}

    return {
        model_id: team_map.get(team_id) if team_id else None
        for model_id, team_id in model_team_ids.items()
    }


def get_all_lob_ids_for_team(db: Session, team_id: int) -> List[int]:
    """
    Get all LOB IDs belonging to a team (direct + inherited), excluding branches
    with direct assignments to other teams.
    """
    if db.bind and db.bind.dialect.name != "postgresql":
        lobs = db.query(LOBUnit.lob_id, LOBUnit.parent_id, LOBUnit.team_id).all()
        children_map: Dict[Optional[int], List[int]] = {}
        team_lookup: Dict[int, Optional[int]] = {}
        for lob_id, parent_id, direct_team_id in lobs:
            team_lookup[lob_id] = direct_team_id
            children_map.setdefault(parent_id, []).append(lob_id)

        direct_lobs = [lob_id for lob_id, direct_team_id in team_lookup.items() if direct_team_id == team_id]
        results: set = set()

        def walk(current_id: int) -> None:
            results.add(current_id)
            for child_id in children_map.get(current_id, []):
                child_team = team_lookup.get(child_id)
                if child_team is not None and child_team != team_id:
                    continue
                walk(child_id)

        for root_id in direct_lobs:
            walk(root_id)

        return sorted(results)

    sql = text(
        """
        WITH RECURSIVE team_lobs AS (
            SELECT lob_id, parent_id, team_id, ARRAY[lob_id] AS path
            FROM lob_units
            WHERE team_id = :team_id
            UNION ALL
            SELECT child.lob_id, child.parent_id, child.team_id,
                   team_lobs.path || child.lob_id AS path
            FROM lob_units child
            JOIN team_lobs ON child.parent_id = team_lobs.lob_id
            WHERE (child.team_id IS NULL OR child.team_id = :team_id)
              AND NOT child.lob_id = ANY(team_lobs.path)
        )
        SELECT DISTINCT lob_id FROM team_lobs;
        """
    )
    results = db.execute(sql, {"team_id": team_id}).all()
    return [row.lob_id for row in results]
