"""Generate an authoritative schema appendix from SQLAlchemy ORM metadata.

Writes `DATA_DICTIONARY_SCHEMA.md` at the repo root.

Usage:
  python scripts/generate_data_dictionary_schema.py
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "api"


def _col_type_str(col) -> str:
    try:
        return str(col.type)
    except Exception:
        return col.type.__class__.__name__


def _default_str(col) -> str:
    if col.server_default is not None:
        try:
            return str(col.server_default.arg)
        except Exception:
            return str(col.server_default)

    if col.default is not None:
        try:
            return str(col.default.arg)
        except Exception:
            return str(col.default)

    return ""


def _fk_targets(col) -> str:
    try:
        return ", ".join(sorted({fk.target_fullname for fk in col.foreign_keys}))
    except Exception:
        return ""


def generate_schema_md() -> str:
    sys.path.insert(0, str(API_ROOT))

    # Import all models so they register with Base.metadata
    from app.models.base import Base  # noqa
    import app.models  # noqa: F401

    # `sorted_tables` can warn (or fail in future versions) when there are
    # cyclical FK dependencies. Alphabetical ordering is stable and avoids
    # dependency-resolution requirements for documentation output.
    tables = sorted(Base.metadata.tables.values(), key=lambda t: t.name)

    lines: list[str] = []
    lines.append("# Data Dictionary Schema Appendix (Authoritative)\n")
    lines.append(
        "This file is generated from the SQLAlchemy ORM models under `api/app/models`.\n"
    )
    lines.append(
        "It is intended to be the **authoritative** listing of tables/columns "
        "(types, nullability, PK/FK, defaults, comments).\n"
    )

    lines.append("## Table Index\n")
    for t in tables:
        lines.append(f"- `{t.name}`")
    lines.append("")

    lines.append("## Tables\n")
    for t in tables:
        lines.append(f"### `{t.name}`\n")

        pk_cols = [
            c.name for c in t.primary_key.columns] if t.primary_key is not None else []
        if pk_cols:
            lines.append(f"- **Primary Key:** {', '.join(pk_cols)}")

        fk_summaries: list[str] = []
        for c in t.c:
            for fk in c.foreign_keys:
                fk_summaries.append(f"{c.name} → {fk.target_fullname}")
        fk_summaries = sorted(set(fk_summaries))
        if fk_summaries:
            lines.append(f"- **Foreign Keys:** {', '.join(fk_summaries)}")

        lines.append(
            "\n| Column | Type | Nullable | PK | FK | Default | Comment |\n"
            "|---|---|---:|---:|---|---|---|"
        )
        for c in t.c:
            lines.append(
                "| {col} | {typ} | {nul} | {pk} | {fk} | {dflt} | {cmt} |".format(
                    col=c.name,
                    typ=_col_type_str(c),
                    nul="Yes" if c.nullable else "No",
                    pk="Yes" if c.primary_key else "",
                    fk=_fk_targets(c),
                    dflt=_default_str(c),
                    cmt=(c.comment or "").replace("\n", " ").strip(),
                )
            )
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    output_path = REPO_ROOT / "DATA_DICTIONARY_SCHEMA.md"
    schema_md = generate_schema_md()
    output_path.write_text(schema_md, encoding="utf-8")
    print(f"Wrote {output_path} ({len(schema_md.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
