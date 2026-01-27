#!/usr/bin/env python3
"""
Role Privilege Analyzer

Scans the FastAPI backend codebase to document role-based authorization patterns
and generates a comprehensive, human-readable summary of privileges per role.

Usage:
    python3 analyze_role_privileges.py [--output OUTPUT_FILE] [--format {markdown,json,text}]

Output:
    - Detailed breakdown of endpoints and features accessible by each role
    - Authorization patterns (role checks, RLS filters, ownership checks)
    - Summary matrices and permission tables
"""

import ast
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import argparse


# Canonical roles based on ROLE_NORMAL_PLAN.md
CANONICAL_ROLES = {
    'ADMIN': 'Admin',
    'USER': 'User',
    'VALIDATOR': 'Validator',
    'GLOBAL_APPROVER': 'Global Approver',
    'REGIONAL_APPROVER': 'Regional Approver'
}


@dataclass
class EndpointPrivilege:
    """Represents authorization requirements for an endpoint."""
    path: str
    method: str
    file_path: str
    line_number: int
    allowed_roles: Set[str] = field(default_factory=set)
    requires_auth: bool = True
    ownership_check: bool = False
    rls_applied: bool = False
    conditional_logic: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class FeaturePrivilege:
    """Represents privileges for a feature/module."""
    feature_name: str
    endpoints: List[EndpointPrivilege] = field(default_factory=list)
    role_summary: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class RolePrivilegeReport:
    """Complete privilege analysis report."""
    roles: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    features: List[FeaturePrivilege] = field(default_factory=list)
    authorization_patterns: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class RoleAnalyzer:
    """Analyzes Python source files for role-based authorization patterns."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.api_path = base_path / 'api' / 'app' / 'api'
        self.core_path = base_path / 'api' / 'app' / 'core'
        self.models_path = base_path / 'api' / 'app' / 'models'

        self.endpoints: List[EndpointPrivilege] = []
        self.features: Dict[str, FeaturePrivilege] = defaultdict(
            lambda: FeaturePrivilege(feature_name='')
        )
        self.auth_patterns: Dict[str, int] = defaultdict(int)
        self.warnings: List[str] = []

    def analyze(self) -> RolePrivilegeReport:
        """Run complete analysis."""
        print("🔍 Scanning codebase for authorization patterns...")

        # Analyze API routes
        if self.api_path.exists():
            for py_file in self.api_path.glob('*.py'):
                if py_file.name != '__init__.py':
                    self._analyze_file(py_file, is_api=True)

        # Analyze core authorization modules
        if self.core_path.exists():
            for core_file in ['deps.py', 'rls.py', 'security.py']:
                file_path = self.core_path / core_file
                if file_path.exists():
                    self._analyze_file(file_path, is_api=False)

        # Build feature summaries
        self._build_feature_summaries()

        # Generate role-centric view
        role_capabilities = self._generate_role_capabilities()

        return RolePrivilegeReport(
            roles=role_capabilities,
            features=list(self.features.values()),
            authorization_patterns=dict(self.auth_patterns),
            warnings=self.warnings
        )

    def _analyze_file(self, file_path: Path, is_api: bool = True):
        """Analyze a single Python file for auth patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            if is_api:
                self._extract_endpoints(tree, file_path, content)

            self._extract_auth_patterns(tree, file_path, content)

        except Exception as e:
            self.warnings.append(f"Failed to parse {file_path}: {e}")

    def _extract_endpoints(self, tree: ast.AST, file_path: Path, content: str):
        """Extract FastAPI endpoint definitions and their auth requirements."""
        lines = content.split('\n')

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for FastAPI route decorators
                route_info = self._parse_route_decorator(node)
                if not route_info:
                    continue

                method, path_pattern = route_info

                # Analyze function for auth requirements
                endpoint = EndpointPrivilege(
                    path=path_pattern,
                    method=method,
                    file_path=str(file_path.relative_to(self.base_path)),
                    line_number=node.lineno
                )

                # Check function signature for dependencies
                for arg in node.args.args:
                    if arg.annotation:
                        annotation_str = ast.unparse(
                            arg.annotation) if hasattr(ast, 'unparse') else ''

                        # Check for get_current_user dependency
                        if 'get_current_user' in annotation_str or 'Depends(get_current_user)' in annotation_str:
                            endpoint.requires_auth = True
                            self.auth_patterns['requires_auth'] += 1

                # Analyze function body for role checks
                self._analyze_function_body(node, endpoint, lines)

                # Categorize by feature
                feature_name = self._categorize_endpoint(
                    file_path, path_pattern)
                self.features[feature_name].feature_name = feature_name
                self.features[feature_name].endpoints.append(endpoint)
                self.endpoints.append(endpoint)

    def _parse_route_decorator(self, node: ast.FunctionDef) -> Optional[tuple]:
        """Extract HTTP method and path from route decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    method = decorator.func.attr.upper()
                    if method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                        # Extract path from first argument
                        if decorator.args:
                            if isinstance(decorator.args[0], ast.Constant):
                                return method, decorator.args[0].value
        return None

    def _analyze_function_body(self, func_node: ast.FunctionDef, endpoint: EndpointPrivilege, lines: List[str]):
        """Analyze function body for authorization logic."""
        for node in ast.walk(func_node):
            # Role comparisons (e.g., current_user.role == UserRole.ADMIN)
            if isinstance(node, ast.Compare):
                compare_str = self._extract_comparison_string(node, lines)
                if compare_str:
                    roles = self._extract_roles_from_comparison(compare_str)
                    endpoint.allowed_roles.update(roles)
                    if roles:
                        self.auth_patterns['role_comparison'] += 1

            # Function calls (e.g., check_admin_role, apply_rls_filters)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id

                    # RLS filter applications
                    if 'rls' in func_name.lower() or 'apply_' in func_name.lower():
                        endpoint.rls_applied = True
                        self.auth_patterns['rls_filter'] += 1

                    # Ownership checks
                    if 'owner' in func_name.lower() or 'check_access' in func_name.lower():
                        endpoint.ownership_check = True
                        self.auth_patterns['ownership_check'] += 1

                    # Role helper checks
                    if func_name == 'is_admin':
                        endpoint.allowed_roles.add('ADMIN')
                        self.auth_patterns['admin_check'] += 1
                    elif func_name == 'is_validator':
                        endpoint.allowed_roles.add('VALIDATOR')
                        self.auth_patterns['validator_check'] += 1
                    elif func_name == 'is_global_approver':
                        endpoint.allowed_roles.add('GLOBAL_APPROVER')
                        self.auth_patterns['global_approver_check'] += 1
                    elif func_name == 'is_regional_approver':
                        endpoint.allowed_roles.add('REGIONAL_APPROVER')
                        self.auth_patterns['regional_approver_check'] += 1
                    elif func_name == 'is_approver':
                        endpoint.allowed_roles.add('GLOBAL_APPROVER')
                        endpoint.allowed_roles.add('REGIONAL_APPROVER')
                        self.auth_patterns['approver_check'] += 1
                    elif func_name == 'is_privileged':
                        endpoint.allowed_roles.add('ADMIN')
                        endpoint.allowed_roles.add('VALIDATOR')
                        endpoint.allowed_roles.add('GLOBAL_APPROVER')
                        endpoint.allowed_roles.add('REGIONAL_APPROVER')
                        self.auth_patterns['privileged_check'] += 1
                    # Fallback for other admin checks (legacy)
                    elif 'admin' in func_name.lower() and func_name != 'is_admin':
                        endpoint.allowed_roles.add('ADMIN')
                        self.auth_patterns['admin_check'] += 1

            # HTTPException raises for authorization
            if isinstance(node, ast.Raise):
                if isinstance(node.exc, ast.Call):
                    if isinstance(node.exc.func, ast.Name):
                        if node.exc.func.id == 'HTTPException':
                            # Check if it's a 403 Forbidden
                            for keyword in node.exc.keywords:
                                if keyword.arg == 'status_code':
                                    if isinstance(keyword.value, ast.Constant):
                                        if keyword.value.value == 403:
                                            self.auth_patterns['explicit_403'] += 1

    def _extract_comparison_string(self, node: ast.Compare, lines: List[str]) -> Optional[str]:
        """Extract string representation of comparison for analysis."""
        try:
            if hasattr(ast, 'unparse'):
                return ast.unparse(node)
            else:
                # Fallback: extract from source lines
                if hasattr(node, 'lineno'):
                    return lines[node.lineno - 1].strip()
        except:
            pass
        return None

    def _extract_roles_from_comparison(self, comparison_str: str) -> Set[str]:
        """Extract role references from comparison string."""
        roles = set()

        # Pattern: UserRole.ADMIN, UserRole.VALIDATOR, etc.
        enum_pattern = r'UserRole\.(\w+)'
        for match in re.finditer(enum_pattern, comparison_str):
            roles.add(match.group(1))

        # Pattern: current_user.role == "Admin"
        string_pattern = r'["\'](\w+\s*\w*)["\']'
        for match in re.finditer(string_pattern, comparison_str):
            role_str = match.group(1)
            # Map display names to codes
            for code, display in CANONICAL_ROLES.items():
                if role_str.lower().replace(' ', '_') == code.lower():
                    roles.add(code)
                elif role_str == display:
                    roles.add(code)

        # Pattern: role_code == "ADMIN"
        if 'role_code' in comparison_str:
            for code in CANONICAL_ROLES.keys():
                if code in comparison_str:
                    roles.add(code)

        return roles

    def _extract_auth_patterns(self, tree: ast.AST, file_path: Path, content: str):
        """Extract general authorization patterns from file."""
        # Count specific authorization utilities
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name.lower()

                if 'privileged' in func_name or 'admin' in func_name:
                    self.auth_patterns['admin_helper_functions'] += 1

                if 'check_' in func_name and 'role' in func_name:
                    self.auth_patterns['role_check_functions'] += 1

    def _categorize_endpoint(self, file_path: Path, path_pattern: str) -> str:
        """Categorize endpoint by module/feature."""
        # Use filename as primary categorization
        module_name = file_path.stem

        # Map common modules to feature names
        feature_map = {
            'auth': 'Authentication & User Management',
            'models': 'Model Inventory',
            'validation_workflow': 'Validation Workflow',
            'monitoring': 'Performance Monitoring',
            'recommendations': 'Recommendations',
            'taxonomies': 'Taxonomy Management',
            'decommissioning': 'Model Decommissioning',
            'vendors': 'Vendor Management',
            'regions': 'Regional Management',
            'audit_logs': 'Audit Logging',
            'approver_roles': 'Approver Roles & Conditional Approvals',
            'mrsa_review_policy': 'MRSA Review Policies',
            'map_applications': 'MAP Applications',
            'kpm': 'KPM Library',
        }

        return feature_map.get(module_name, module_name.replace('_', ' ').title())

    def _build_feature_summaries(self):
        """Build role-based summaries for each feature."""
        for feature in self.features.values():
            role_actions = defaultdict(list)

            for endpoint in feature.endpoints:
                action = f"{endpoint.method} {endpoint.path}"

                if not endpoint.allowed_roles:
                    # No explicit role check - could be open or RLS-based
                    if endpoint.requires_auth:
                        if endpoint.rls_applied:
                            role_actions['ALL_AUTHENTICATED'].append(
                                f"{action} (RLS filtered)")
                        else:
                            role_actions['ALL_AUTHENTICATED'].append(action)
                    else:
                        role_actions['PUBLIC'].append(action)
                else:
                    for role in endpoint.allowed_roles:
                        role_actions[role].append(action)

            feature.role_summary = dict(role_actions)

    def _generate_role_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Generate role-centric capability view."""
        capabilities = {role: {
            'display_name': display,
            'features': defaultdict(list),
            'endpoint_count': 0,
            'exclusive_endpoints': [],
            'notes': []
        } for role, display in CANONICAL_ROLES.items()}

        # Add special categories
        capabilities['ALL_AUTHENTICATED'] = {
            'display_name': 'All Authenticated Users',
            'features': defaultdict(list),
            'endpoint_count': 0,
            'notes': ['Applies to any logged-in user, may be filtered by RLS']
        }

        for feature in self.features.values():
            for role, actions in feature.role_summary.items():
                if role in capabilities:
                    capabilities[role]['features'][feature.feature_name].extend(
                        actions)
                    capabilities[role]['endpoint_count'] += len(actions)

        # Identify exclusive capabilities (only one role can access)
        for endpoint in self.endpoints:
            if len(endpoint.allowed_roles) == 1:
                role = list(endpoint.allowed_roles)[0]
                if role in capabilities:
                    action = f"{endpoint.method} {endpoint.path}"
                    capabilities[role]['exclusive_endpoints'].append(action)

        # Convert defaultdicts to regular dicts for JSON serialization
        for role in capabilities:
            capabilities[role]['features'] = dict(
                capabilities[role]['features'])

        return capabilities


class ReportGenerator:
    """Generates human-readable reports from analysis results."""

    def __init__(self, report: RolePrivilegeReport):
        self.report = report

    def generate_markdown(self) -> str:
        """Generate comprehensive markdown report."""
        lines = [
            "# Role-Based Authorization Analysis",
            "",
            f"*Generated on: {self._get_timestamp()}*",
            "",
            "## Executive Summary",
            "",
            self._generate_executive_summary(),
            "",
            "## Canonical Roles",
            "",
            self._generate_roles_table(),
            "",
            "## Role Capabilities Matrix",
            "",
            self._generate_capabilities_matrix(),
            "",
            "## Detailed Role Privileges",
            "",
        ]

        # Detailed breakdown per role
        for role_code in sorted(CANONICAL_ROLES.keys()):
            if role_code in self.report.roles:
                lines.extend(self._generate_role_section(role_code))
                lines.append("")

        # All authenticated users
        if 'ALL_AUTHENTICATED' in self.report.roles:
            lines.extend(self._generate_role_section('ALL_AUTHENTICATED'))
            lines.append("")

        lines.extend([
            "## Feature-Centric View",
            "",
        ])

        for feature in sorted(self.report.features, key=lambda f: f.feature_name):
            lines.extend(self._generate_feature_section(feature))
            lines.append("")

        lines.extend([
            "## Authorization Patterns",
            "",
            self._generate_patterns_summary(),
            "",
        ])

        if self.report.warnings:
            lines.extend([
                "## Warnings & Issues",
                "",
            ])
            for warning in self.report.warnings:
                lines.append(f"- ⚠️ {warning}")
            lines.append("")

        lines.extend([
            "## Analysis Methodology",
            "",
            self._generate_methodology(),
        ])

        return '\n'.join(lines)

    def generate_json(self) -> str:
        """Generate JSON report."""
        # Convert dataclass instances to dicts
        json_data = {
            'timestamp': self._get_timestamp(),
            'roles': self.report.roles,
            'features': [
                {
                    'feature_name': f.feature_name,
                    'role_summary': f.role_summary,
                    'endpoints': [
                        {
                            'path': e.path,
                            'method': e.method,
                            'allowed_roles': list(e.allowed_roles),
                            'requires_auth': e.requires_auth,
                            'rls_applied': e.rls_applied,
                            'ownership_check': e.ownership_check,
                        }
                        for e in f.endpoints
                    ]
                }
                for f in self.report.features
            ],
            'authorization_patterns': self.report.authorization_patterns,
            'warnings': self.report.warnings
        }
        return json.dumps(json_data, indent=2)

    def generate_text(self) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 80,
            "ROLE-BASED AUTHORIZATION ANALYSIS",
            "=" * 80,
            "",
            self._generate_executive_summary(),
            "",
            "-" * 80,
            "ROLE CAPABILITIES",
            "-" * 80,
            "",
        ]

        for role_code in sorted(CANONICAL_ROLES.keys()):
            if role_code in self.report.roles:
                role_data = self.report.roles[role_code]
                lines.append(f"{role_data['display_name']} ({role_code}):")
                lines.append(
                    f"  Total Endpoints: {role_data['endpoint_count']}")
                lines.append(f"  Features: {len(role_data['features'])}")
                lines.append("")

        return '\n'.join(lines)

    def _generate_executive_summary(self) -> str:
        """Generate executive summary section."""
        total_endpoints = sum(
            role_data['endpoint_count']
            for role_data in self.report.roles.values()
        )

        total_features = len(self.report.features)

        lines = [
            f"- **Total API Endpoints Analyzed**: {total_endpoints}",
            f"- **Total Features/Modules**: {total_features}",
            f"- **Canonical Roles**: {len(CANONICAL_ROLES)}",
            f"- **Authorization Patterns Detected**: {len(self.report.authorization_patterns)}",
        ]

        return '\n'.join(lines)

    def _generate_roles_table(self) -> str:
        """Generate canonical roles reference table."""
        lines = [
            "| Role Code | Display Name | Description |",
            "|-----------|--------------|-------------|",
        ]

        role_descriptions = {
            'ADMIN': 'Full system access, configuration management, user administration',
            'VALIDATOR': 'Execute validation workflows, review models, assign tasks',
            'GLOBAL_APPROVER': 'Approve model deployments and validations globally',
            'REGIONAL_APPROVER': 'Approve model deployments within assigned regions',
            'USER': 'Basic model owner/contributor access, view and submit models',
        }

        for code, display in sorted(CANONICAL_ROLES.items()):
            desc = role_descriptions.get(code, 'Standard user')
            lines.append(f"| `{code}` | {display} | {desc} |")

        return '\n'.join(lines)

    def _generate_capabilities_matrix(self) -> str:
        """Generate cross-feature capability matrix."""
        # Build feature x role matrix
        features = sorted(set(f.feature_name for f in self.report.features))
        roles = sorted(CANONICAL_ROLES.keys())

        lines = [
            "| Feature | " + " | ".join(roles) + " |",
            "|---------|" + "|".join(["-----"] * len(roles)) + "|",
        ]

        for feature_name in features:
            feature = next(
                (f for f in self.report.features if f.feature_name == feature_name), None)
            if not feature:
                continue

            row = [feature_name]
            for role in roles:
                if role in feature.role_summary and feature.role_summary[role]:
                    count = len(feature.role_summary[role])
                    row.append(f"✅ ({count})")
                else:
                    row.append("—")

            lines.append("| " + " | ".join(row) + " |")

        return '\n'.join(lines)

    def _generate_role_section(self, role_code: str) -> List[str]:
        """Generate detailed section for a role."""
        role_data = self.report.roles[role_code]
        lines = [
            f"### {role_data['display_name']} (`{role_code}`)",
            "",
            f"**Accessible Endpoints**: {role_data['endpoint_count']}",
            "",
        ]

        if role_data.get('notes'):
            lines.append("**Notes**:")
            for note in role_data['notes']:
                lines.append(f"- {note}")
            lines.append("")

        if role_data.get('exclusive_endpoints'):
            lines.append(
                f"**Exclusive Capabilities** ({len(role_data['exclusive_endpoints'])} endpoints):")
            # Show top 10
            for endpoint in sorted(role_data['exclusive_endpoints'])[:10]:
                lines.append(f"- `{endpoint}`")
            if len(role_data['exclusive_endpoints']) > 10:
                lines.append(
                    f"- *(+{len(role_data['exclusive_endpoints']) - 10} more)*")
            lines.append("")

        lines.append("**Feature Access**:")
        lines.append("")

        for feature_name in sorted(role_data['features'].keys()):
            actions = role_data['features'][feature_name]
            lines.append(f"#### {feature_name}")
            lines.append("")
            for action in sorted(actions)[:5]:  # Show top 5 per feature
                lines.append(f"- `{action}`")
            if len(actions) > 5:
                lines.append(f"- *(+{len(actions) - 5} more endpoints)*")
            lines.append("")

        return lines

    def _generate_feature_section(self, feature: FeaturePrivilege) -> List[str]:
        """Generate section for a feature."""
        lines = [
            f"### {feature.feature_name}",
            "",
            f"**Total Endpoints**: {len(feature.endpoints)}",
            "",
        ]

        if feature.role_summary:
            lines.append("**Role Access Summary**:")
            for role in sorted(feature.role_summary.keys()):
                count = len(feature.role_summary[role])
                lines.append(f"- **{role}**: {count} endpoint(s)")
            lines.append("")

        # Show sample endpoints
        if feature.endpoints:
            lines.append("**Sample Endpoints**:")
            for endpoint in sorted(feature.endpoints, key=lambda e: e.path)[:5]:
                roles_str = ', '.join(sorted(
                    endpoint.allowed_roles)) if endpoint.allowed_roles else 'Any authenticated'
                auth_flags = []
                if endpoint.rls_applied:
                    auth_flags.append('RLS')
                if endpoint.ownership_check:
                    auth_flags.append('Ownership')
                flags_str = f" [{', '.join(auth_flags)}]" if auth_flags else ""
                lines.append(
                    f"- `{endpoint.method} {endpoint.path}` — {roles_str}{flags_str}")
            lines.append("")

        return lines

    def _generate_patterns_summary(self) -> str:
        """Generate authorization patterns summary."""
        lines = [
            "The following authorization mechanisms were detected:",
            "",
        ]

        pattern_descriptions = {
            'requires_auth': 'Endpoints requiring authentication (get_current_user dependency)',
            'role_comparison': 'Explicit role comparisons in code',
            'rls_filter': 'Row-level security filters applied',
            'ownership_check': 'Ownership/access checks',
            'admin_check': 'Admin-only checks',
            'explicit_403': 'Explicit 403 Forbidden exceptions',
            'admin_helper_functions': 'Admin helper functions',
            'role_check_functions': 'Role check helper functions',
        }

        for pattern, count in sorted(self.report.authorization_patterns.items(), key=lambda x: -x[1]):
            desc = pattern_descriptions.get(
                pattern, pattern.replace('_', ' ').title())
            lines.append(f"- **{desc}**: {count} occurrence(s)")

        return '\n'.join(lines)

    def _generate_methodology(self) -> str:
        """Generate methodology section."""
        return """This analysis was performed by:

1. **Static Code Analysis**: Parsing Python source files using the `ast` module
2. **Pattern Matching**: Identifying authorization patterns including:
   - FastAPI route decorators and dependencies
   - `get_current_user` dependency injections
   - Role enum comparisons (`UserRole.ADMIN`, etc.)
   - String-based role checks (`role == "Admin"`)
   - RLS filter applications
   - Ownership verification calls
   - HTTP 403 authorization exceptions
3. **Feature Categorization**: Grouping endpoints by module/feature
4. **Role Aggregation**: Building role-centric capability views

**Limitations**:
- Dynamic authorization logic may not be fully captured
- Conditional permissions based on runtime state are approximated
- Frontend authorization is not included in this backend-focused analysis
"""

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def main():
    """Main entry point."""
    # Default to repo root (parent of scripts/)
    default_base = Path(__file__).parent.parent

    parser = argparse.ArgumentParser(
        description='Analyze role-based authorization in FastAPI backend'
    )
    parser.add_argument(
        '--output',
        '-o',
        default='ROLE_PRIVILEGES_REPORT.md',
        help='Output file path (default: ROLE_PRIVILEGES_REPORT.md)'
    )
    parser.add_argument(
        '--format',
        '-f',
        choices=['markdown', 'json', 'text'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--base-path',
        default=str(default_base),
        help=f'Base path to codebase (default: {default_base})'
    )

    args = parser.parse_args()

    base_path = Path(args.base_path).resolve()

    if not base_path.exists():
        print(f"❌ Error: Base path does not exist: {base_path}")
        return 1

    print(f"📂 Analyzing codebase at: {base_path}")

    # Run analysis
    analyzer = RoleAnalyzer(base_path)
    report = analyzer.analyze()

    print(f"✅ Analysis complete!")
    print(
        f"   - {sum(r['endpoint_count'] for r in report.roles.values())} endpoints analyzed")
    print(f"   - {len(report.features)} features identified")
    print(f"   - {len(report.authorization_patterns)} auth patterns detected")

    if report.warnings:
        print(f"   - ⚠️  {len(report.warnings)} warnings")

    # Generate report
    generator = ReportGenerator(report)

    if args.format == 'markdown':
        content = generator.generate_markdown()
    elif args.format == 'json':
        content = generator.generate_json()
    else:
        content = generator.generate_text()

    # Write output
    output_path = Path(args.output)
    output_path.write_text(content, encoding='utf-8')

    print(f"📄 Report written to: {output_path}")
    print(f"   Format: {args.format}")

    return 0


if __name__ == '__main__':
    exit(main())
