#!/bin/bash
# Mirror dev database to production, preserving production passwords
# Usage: ./scripts/mirror_to_prod.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== MRM Database Mirror: Dev -> Production ===${NC}"
echo ""
echo -e "${RED}WARNING: This will overwrite ALL production data except user passwords!${NC}"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Step 1: Create dev database dump
echo ""
echo -e "${GREEN}Step 1: Creating dev database dump...${NC}"
DUMP_FILE="/tmp/mrm_dev_dump_$(date +%Y%m%d_%H%M%S).sql"

docker exec mrm3_db pg_dump -U mrm_user -d mrm_db --clean --if-exists > "$DUMP_FILE"

if [ ! -s "$DUMP_FILE" ]; then
    echo -e "${RED}Error: Dump file is empty${NC}"
    exit 1
fi

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo -e "Dump created: $DUMP_FILE (${DUMP_SIZE})"

# Step 2: Test SSH connection
echo ""
echo -e "${GREEN}Step 2: Testing SSH connection to production...${NC}"
if ! ssh -o ConnectTimeout=15 mrm-admin@ssh.mrmqmistest.org "echo 'SSH connection successful'"; then
    echo -e "${RED}Error: Cannot connect to production server${NC}"
    exit 1
fi

# Step 3: Backup production passwords
echo ""
echo -e "${GREEN}Step 3: Backing up production user passwords...${NC}"
ssh mrm-admin@ssh.mrmqmistest.org "
    sudo docker compose -f /opt/mrm/docker-compose.prod.yml exec -T db \
        psql -U mrm -d mrm -c \"COPY (SELECT user_id, email, password_hash FROM users) TO STDOUT WITH CSV HEADER\" \
        > /tmp/prod_passwords_backup.csv
    echo 'Password backup created:'
    head -5 /tmp/prod_passwords_backup.csv
    echo '...'
    echo \"Total users: \$(wc -l < /tmp/prod_passwords_backup.csv)\"
"

# Step 4: Transfer dump to production
echo ""
echo -e "${GREEN}Step 4: Transferring database dump to production...${NC}"
scp "$DUMP_FILE" mrm-admin@ssh.mrmqmistest.org:/tmp/mrm_dev_dump.sql
echo "Dump transferred successfully"

# Step 5: Stop API to prevent writes during restore
echo ""
echo -e "${GREEN}Step 5: Stopping API service during restore...${NC}"
ssh mrm-admin@ssh.mrmqmistest.org "
    cd /opt/mrm
    sudo docker compose -f docker-compose.prod.yml stop api
"

# Step 6: Restore the dump
echo ""
echo -e "${GREEN}Step 6: Restoring database dump on production...${NC}"
ssh mrm-admin@ssh.mrmqmistest.org "
    DB_CONTAINER=\$(sudo docker compose -f /opt/mrm/docker-compose.prod.yml ps -q db)
    if [ -z \"\$DB_CONTAINER\" ]; then
        echo 'Error: Could not determine production db container ID'
        exit 1
    fi

    # Copy dump into container
    sudo docker cp /tmp/mrm_dev_dump.sql \"\$DB_CONTAINER\":/tmp/mrm_dev_dump.sql

    # Restore the dump
    sudo docker compose -f /opt/mrm/docker-compose.prod.yml exec -T db \
        psql -U mrm -d mrm -f /tmp/mrm_dev_dump.sql 2>&1 | tail -20

    echo ''
    echo 'Dump restored successfully'
"

# Step 7: Restore production passwords
echo ""
echo -e "${GREEN}Step 7: Restoring production user passwords...${NC}"
ssh mrm-admin@ssh.mrmqmistest.org "
    DB_CONTAINER=\$(sudo docker compose -f /opt/mrm/docker-compose.prod.yml ps -q db)
    if [ -z \"\$DB_CONTAINER\" ]; then
        echo 'Error: Could not determine production db container ID'
        exit 1
    fi

    # Copy password backup file into the container (required for \copy command)
    sudo docker cp /tmp/prod_passwords_backup.csv \"\$DB_CONTAINER\":/tmp/prod_passwords_backup.csv

    # Create temp table and restore passwords
    sudo docker compose -f /opt/mrm/docker-compose.prod.yml exec -T db psql -U mrm -d mrm << 'EOSQL'
-- Create temporary table for password restoration
CREATE TEMP TABLE password_backup (
    user_id INTEGER,
    email VARCHAR(255),
    password_hash VARCHAR(255)
);

-- Import the backed up passwords
\copy password_backup FROM '/tmp/prod_passwords_backup.csv' WITH CSV HEADER;

-- Update users with production passwords (for existing users)
UPDATE users u
SET password_hash = pb.password_hash
FROM password_backup pb
WHERE u.email = pb.email;

-- Show results
SELECT u.user_id, u.email,
       CASE WHEN pb.email IS NOT NULL THEN 'Password Restored' ELSE 'New User (dev password)' END as status
FROM users u
LEFT JOIN password_backup pb ON u.email = pb.email
ORDER BY u.user_id;

DROP TABLE password_backup;
EOSQL
"

# Step 8: Start API service
echo ""
echo -e "${GREEN}Step 8: Starting API service...${NC}"
ssh mrm-admin@ssh.mrmqmistest.org "
    cd /opt/mrm
    sudo docker compose -f docker-compose.prod.yml start api
    sleep 5
"

# Step 9: Verify services
echo ""
echo -e "${GREEN}Step 9: Verifying services...${NC}"
ssh mrm-admin@ssh.mrmqmistest.org "
    echo '=== Service Status ==='
    sudo docker compose -f /opt/mrm/docker-compose.prod.yml ps
    echo ''
    echo '=== Health Checks ==='
    curl -s -o /dev/null -w 'Frontend: %{http_code}\n' http://127.0.0.1:3000/
    curl -s -o /dev/null -w 'API: %{http_code}\n' http://127.0.0.1:8001/docs
    echo ''
    echo '=== User Count ==='
    sudo docker compose -f /opt/mrm/docker-compose.prod.yml exec -T db \
        psql -U mrm -d mrm -c 'SELECT COUNT(*) as user_count FROM users;'
    echo ''
    echo '=== Model Count ==='
    sudo docker compose -f /opt/mrm/docker-compose.prod.yml exec -T db \
        psql -U mrm -d mrm -c 'SELECT COUNT(*) as model_count FROM models;'
"

# Cleanup
echo ""
echo -e "${GREEN}Step 10: Cleaning up temporary files...${NC}"
rm -f "$DUMP_FILE"
ssh mrm-admin@ssh.mrmqmistest.org "rm -f /tmp/mrm_dev_dump.sql"

echo ""
echo -e "${GREEN}=== Database mirror completed successfully! ===${NC}"
echo ""
echo "Notes:"
echo "  - Production user passwords have been preserved"
echo "  - New users from dev will have dev passwords (may need reset)"
echo "  - Test login at https://app.mrmqmistest.org"
