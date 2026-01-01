#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_FILE="${1:-}"

if [[ -z "$BACKUP_FILE" ]]; then
    echo "Usage: $(basename "$0") /path/to/backup.dump [--yes]"
    echo "Example: $(basename "$0") $ROOT_DIR/backups/mrm_db_YYYYMMDD_HHMMSS.dump"
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

if [[ "${2:-}" != "--yes" ]]; then
    echo "This will overwrite the current dev database in docker-compose."
    read -r -p "Type 'yes' to continue: " confirm
    if [[ "$confirm" != "yes" ]]; then
        echo "Restore cancelled."
        exit 1
    fi
fi

echo "Restoring from: $BACKUP_FILE"
docker compose exec -T db pg_restore -U mrm_user -d mrm_db --clean --if-exists --no-owner --no-privileges "$BACKUP_FILE"
echo "Restore complete."
