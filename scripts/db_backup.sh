#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-"$ROOT_DIR/backups"}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
DEFAULT_FILE="$BACKUP_DIR/mrm_db_${TIMESTAMP}.dump"
OUTPUT_FILE="${1:-$DEFAULT_FILE}"

mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$OUTPUT_FILE")"

echo "Creating backup at: $OUTPUT_FILE"
docker compose exec -T db pg_dump -U mrm_user -d mrm_db -Fc --no-owner --no-privileges > "$OUTPUT_FILE"
echo "Backup complete."
