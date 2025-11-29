#!/usr/bin/env python3
"""Script to replace datetime.utcnow() with utc_now() across the codebase."""
import os
import re
import sys
from pathlib import Path

# Define the import line to add
UTC_NOW_IMPORT = "from app.core.time import utc_now"

def process_file(filepath: Path, add_import: bool = True) -> tuple[bool, list[str]]:
    """Process a single file to replace datetime.utcnow patterns.

    Args:
        filepath: Path to the file to process
        add_import: If True, adds the import statement. Set to False for test/seed files
                   that might use a different import approach.

    Returns:
        Tuple of (was_modified, list_of_changes)
    """
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    changes = []

    # Check if file contains datetime.utcnow
    if 'datetime.utcnow' not in content:
        return False, []

    # Pattern 1: default=datetime.utcnow (callable reference)
    # Pattern 2: onupdate=datetime.utcnow (callable reference)
    # Pattern 3: datetime.utcnow() (direct call)

    # Replace default=datetime.utcnow with default=utc_now
    if 'default=datetime.utcnow' in content:
        content = re.sub(r'default=datetime\.utcnow\b', 'default=utc_now', content)
        changes.append("Replaced default=datetime.utcnow with default=utc_now")

    # Replace onupdate=datetime.utcnow with onupdate=utc_now
    if 'onupdate=datetime.utcnow' in content:
        content = re.sub(r'onupdate=datetime\.utcnow\b', 'onupdate=utc_now', content)
        changes.append("Replaced onupdate=datetime.utcnow with onupdate=utc_now")

    # Replace datetime.utcnow() direct calls with utc_now()
    if 'datetime.utcnow()' in content:
        content = re.sub(r'datetime\.utcnow\(\)', 'utc_now()', content)
        changes.append("Replaced datetime.utcnow() with utc_now()")

    # Add import if not already present and changes were made
    if add_import and changes and UTC_NOW_IMPORT not in content:
        # Find the best place to insert the import
        # After "from app.models.base import Base" or at the end of imports

        if 'from app.models.base import Base' in content:
            content = content.replace(
                'from app.models.base import Base',
                f'from app.models.base import Base\n{UTC_NOW_IMPORT}'
            )
            changes.append("Added import: from app.core.time import utc_now")
        elif 'from app.models' in content:
            # Find last app.models import
            lines = content.split('\n')
            inserted = False
            for i, line in enumerate(lines):
                if line.startswith('from app.models') or line.startswith('from app.'):
                    pass  # Keep looking for the last one
            # Find first app import and insert after
            for i, line in enumerate(lines):
                if line.startswith('from app.'):
                    lines.insert(i + 1, UTC_NOW_IMPORT)
                    content = '\n'.join(lines)
                    inserted = True
                    break
            if inserted:
                changes.append("Added import: from app.core.time import utc_now")
        elif 'from app.' in content:
            # Add after first app import
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('from app.'):
                    lines.insert(i + 1, UTC_NOW_IMPORT)
                    content = '\n'.join(lines)
                    changes.append("Added import: from app.core.time import utc_now")
                    break
        else:
            # Add after other imports
            lines = content.split('\n')
            import_end = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_end = i + 1
            lines.insert(import_end, UTC_NOW_IMPORT)
            content = '\n'.join(lines)
            changes.append("Added import: from app.core.time import utc_now")

    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True, changes

    return False, []


def process_directory(directory: Path, pattern: str = '*.py', add_import: bool = True) -> int:
    """Process all Python files in a directory.

    Returns: Number of modified files
    """
    total_modified = 0

    for filepath in sorted(directory.glob(pattern)):
        if filepath.name.startswith('__'):
            continue

        modified, changes = process_file(filepath, add_import=add_import)
        if modified:
            total_modified += 1
            print(f"\n{filepath.relative_to(filepath.parent.parent)}:")
            for change in changes:
                print(f"  - {change}")

    return total_modified


def main():
    """Main function to process all files."""
    base_path = Path(__file__).parent

    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'

    total_modified = 0

    if mode in ('all', 'models'):
        models_path = base_path / 'app' / 'models'
        print("=" * 60)
        print("Processing model files...")
        print("=" * 60)
        total_modified += process_directory(models_path)

    if mode in ('all', 'api'):
        api_path = base_path / 'app' / 'api'
        print("\n" + "=" * 60)
        print("Processing API files...")
        print("=" * 60)
        total_modified += process_directory(api_path)

    if mode in ('all', 'core'):
        core_path = base_path / 'app' / 'core'
        print("\n" + "=" * 60)
        print("Processing core files...")
        print("=" * 60)
        total_modified += process_directory(core_path)

    if mode in ('all', 'seeds'):
        # Process seed files in api root
        print("\n" + "=" * 60)
        print("Processing seed files...")
        print("=" * 60)
        for filepath in sorted(base_path.glob('seed*.py')):
            modified, changes = process_file(filepath)
            if modified:
                total_modified += 1
                print(f"\n{filepath.name}:")
                for change in changes:
                    print(f"  - {change}")

        # Also process app/seed.py
        seed_file = base_path / 'app' / 'seed.py'
        if seed_file.exists():
            modified, changes = process_file(seed_file)
            if modified:
                total_modified += 1
                print(f"\napp/seed.py:")
                for change in changes:
                    print(f"  - {change}")

    if mode in ('all', 'tests'):
        tests_path = base_path / 'tests'
        print("\n" + "=" * 60)
        print("Processing test files...")
        print("=" * 60)
        total_modified += process_directory(tests_path)

    print("\n" + "=" * 60)
    print(f"Total modified: {total_modified} files")
    print("=" * 60)


if __name__ == '__main__':
    main()
