#!/usr/bin/env python3
"""Generate API_ENDPOINTS.md from FastAPI router definitions."""
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path


def _attr_to_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute):
        base = _attr_to_str(node.value)
        return f"{base}.{node.attr}" if base else None
    if isinstance(node, ast.Name):
        return node.id
    return None


def _load_include_prefixes(main_path: Path) -> dict[str, str]:
    tree = ast.parse(main_path.read_text())
    prefixes: dict[str, str] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "app" or node.func.attr != "include_router":
            continue
        if not node.args:
            continue
        target = _attr_to_str(node.args[0])
        if not target:
            continue
        prefix = ""
        for kw in node.keywords:
            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                prefix = kw.value.value
        prefixes[target] = prefix

    return prefixes


def _collect_routes(api_dir: Path, include_prefixes: dict[str, str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    func_nodes = (ast.FunctionDef, ast.AsyncFunctionDef)

    for path in sorted(api_dir.glob("*.py")):
        tree = ast.parse(path.read_text())
        router_prefix: dict[str, str] = {}

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            if not isinstance(node.value.func, ast.Name):
                continue
            if node.value.func.id != "APIRouter":
                continue
            prefix = ""
            for kw in node.value.keywords:
                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                    prefix = kw.value.value
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    router_prefix[tgt.id] = prefix

        for node in ast.walk(tree):
            if not isinstance(node, func_nodes):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call):
                    continue
                if not isinstance(deco.func, ast.Attribute):
                    continue
                if not isinstance(deco.func.value, ast.Name):
                    continue
                router_var = deco.func.value.id
                method = deco.func.attr
                path_val = None
                if deco.args and isinstance(deco.args[0], ast.Constant):
                    path_val = deco.args[0].value
                if path_val is None:
                    for kw in deco.keywords:
                        if kw.arg == "path" and isinstance(kw.value, ast.Constant):
                            path_val = kw.value.value
                if path_val is None:
                    continue

                module = path.stem
                include_prefix = include_prefixes.get(f"{module}.{router_var}", "")
                base_prefix = f"{include_prefix}{router_prefix.get(router_var, '')}"
                full_path = f"{base_prefix}{path_val}"

                entries.append(
                    {
                        "module": module,
                        "base_prefix": base_prefix,
                        "full_path": full_path,
                        "method": method,
                    }
                )

    return entries


def _build_markdown(entries: list[dict[str, str]]) -> str:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for entry in entries:
        grouped[entry["module"]].append(entry)

    lines: list[str] = []
    lines.append("## API Endpoint Appendix (Generated from code)")
    lines.append("")
    lines.append(
        "- Generated from FastAPI router definitions in `api/app/api/*` and `api/app/main.py` include_router prefixes."
    )
    lines.append("")

    for module in sorted(grouped):
        module_entries = grouped[module]
        prefixes = sorted({e["base_prefix"] for e in module_entries})
        prefix_label = ", ".join([p if p else "(none)" for p in prefixes])
        lines.append(f"### {module} (prefixes: {prefix_label})")
        for entry in sorted(module_entries, key=lambda e: (e["full_path"], e["method"])):
            lines.append(f"- {entry['method'].upper()} {entry['full_path']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    main_path = root / "api" / "app" / "main.py"
    api_dir = root / "api" / "app" / "api"
    output_path = root / "API_ENDPOINTS.md"

    include_prefixes = _load_include_prefixes(main_path)
    entries = _collect_routes(api_dir, include_prefixes)
    output_path.write_text(_build_markdown(entries))
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
