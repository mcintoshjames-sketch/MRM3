#!/bin/bash
#
# deploy.sh - Push development changes to production
#
# Usage:
#   ./scripts/deploy.sh                    # Interactive mode - prompts for commit message
#   ./scripts/deploy.sh "commit message"   # Auto mode - uses provided message
#   ./scripts/deploy.sh --status           # Just show status, don't deploy
#   ./scripts/deploy.sh --prod-only        # Skip git, just deploy to production server
#
# This script saves LLM tokens by combining multiple operations into one command.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REMOTE="origin"
BRANCH="main"
PROD_HOST="mrm-admin@ssh.mrmqmistest.org"
PROD_PATH="/opt/mrm"

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Show current status
show_status() {
    print_header "Repository Status"

    echo ""
    echo "Branch: $(git branch --show-current)"
    echo "Remote: $REMOTE/$BRANCH"
    echo ""

    # Check for uncommitted changes
    if [[ -n $(git status --porcelain) ]]; then
        echo -e "${YELLOW}Uncommitted changes:${NC}"
        git status --short
        echo ""

        # Count changes
        STAGED=$(git diff --cached --numstat | wc -l | tr -d ' ')
        UNSTAGED=$(git diff --numstat | wc -l | tr -d ' ')
        UNTRACKED=$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')

        echo "  Staged:    $STAGED files"
        echo "  Modified:  $UNSTAGED files"
        echo "  Untracked: $UNTRACKED files"
    else
        print_success "Working tree is clean"
    fi

    echo ""

    # Check ahead/behind
    git fetch $REMOTE $BRANCH --quiet 2>/dev/null || true
    LOCAL=$(git rev-parse HEAD)
    REMOTE_HEAD=$(git rev-parse $REMOTE/$BRANCH 2>/dev/null || echo "unknown")

    if [[ "$LOCAL" == "$REMOTE_HEAD" ]]; then
        print_success "Up to date with $REMOTE/$BRANCH"
    else
        AHEAD=$(git rev-list --count $REMOTE/$BRANCH..HEAD 2>/dev/null || echo "0")
        BEHIND=$(git rev-list --count HEAD..$REMOTE/$BRANCH 2>/dev/null || echo "0")

        [[ "$AHEAD" != "0" ]] && print_info "Ahead of $REMOTE/$BRANCH by $AHEAD commits"
        [[ "$BEHIND" != "0" ]] && print_warning "Behind $REMOTE/$BRANCH by $BEHIND commits"
    fi

    echo ""
    echo "Recent commits:"
    git log --oneline -5
}

# Generate smart commit message based on changes
generate_commit_message() {
    local changes=""
    local files_changed=$(git diff --cached --name-only 2>/dev/null || git diff --name-only)

    # Analyze changes
    local has_api=false
    local has_web=false
    local has_docs=false
    local has_tests=false
    local has_config=false

    while IFS= read -r file; do
        [[ "$file" == api/* ]] && has_api=true
        [[ "$file" == web/* ]] && has_web=true
        [[ "$file" == docs/* ]] && has_docs=true
        [[ "$file" == *.md ]] && has_docs=true
        [[ "$file" == *test* ]] && has_tests=true
        [[ "$file" == *.yml ]] && has_config=true
        [[ "$file" == *.json ]] && has_config=true
    done <<< "$files_changed"

    # Build prefix
    if $has_api && $has_web; then
        changes="feat: Update API and frontend"
    elif $has_api; then
        changes="feat: Update backend"
    elif $has_web; then
        changes="feat: Update frontend"
    elif $has_docs; then
        changes="docs: Update documentation"
    elif $has_tests; then
        changes="test: Update tests"
    elif $has_config; then
        changes="chore: Update configuration"
    else
        changes="chore: Update files"
    fi

    # Add file count
    local count=$(echo "$files_changed" | grep -c . || echo "0")
    changes="$changes ($count files)"

    echo "$changes"
}

# Git operations: add, commit, push
git_push() {
    local commit_msg="$1"

    print_header "Git Operations"

    # Check if there are changes
    if [[ -z $(git status --porcelain) ]]; then
        print_success "No changes to commit"
        return 0
    fi

    # Stage all changes
    echo "Staging all changes..."
    git add -A
    print_success "Staged all changes"

    # Show what will be committed
    echo ""
    echo "Changes to be committed:"
    git diff --cached --stat
    echo ""

    # Generate commit message if not provided
    if [[ -z "$commit_msg" ]]; then
        commit_msg=$(generate_commit_message)
        echo "Generated commit message: $commit_msg"
        echo ""
        read -p "Use this message? (y/n/custom): " choice
        case $choice in
            n|N)
                echo "Aborting..."
                git reset HEAD --quiet
                exit 1
                ;;
            y|Y|"")
                ;;
            *)
                commit_msg="$choice"
                ;;
        esac
    fi

    # Commit
    echo ""
    echo "Committing..."
    git commit -m "$commit_msg

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
    print_success "Committed: $commit_msg"

    # Push
    echo ""
    echo "Pushing to $REMOTE/$BRANCH..."
    git push $REMOTE $BRANCH
    print_success "Pushed to $REMOTE/$BRANCH"

    # Show result
    echo ""
    echo "Latest commit:"
    git log --oneline -1
}

# Deploy to production server
deploy_to_prod() {
    print_header "Production Deployment"

    # Check SSH connectivity
    echo "Checking SSH connectivity..."
    if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $PROD_HOST "echo 'connected'" &>/dev/null; then
        print_error "Cannot connect to $PROD_HOST"
        print_info "Make sure you have SSH access configured"
        return 1
    fi
    print_success "SSH connection OK"

    echo ""
    echo "Deploying to production server..."

    # Run deployment commands
    ssh -o ConnectTimeout=30 $PROD_HOST << 'DEPLOY_SCRIPT'
        set -e
        cd /opt/mrm

        # Verify production env file exists (never committed)
        if [ ! -f .env.prod ]; then
            echo "ERROR: /opt/mrm/.env.prod not found!"
            echo "Create it on the server before deploying."
            exit 1
        fi

        # If docker-compose.prod.yml exists but is untracked, git pull will fail.
        # Back it up and remove it so git can manage it.
        if [ -f docker-compose.prod.yml ]; then
            if ! git ls-files --error-unmatch docker-compose.prod.yml >/dev/null 2>&1; then
                if git status --porcelain | grep -q '^?? docker-compose\.prod\.yml$'; then
                    echo "Backing up untracked docker-compose.prod.yml -> docker-compose.prod.yml.backup"
                    sudo cp docker-compose.prod.yml docker-compose.prod.yml.backup
                    sudo rm -f docker-compose.prod.yml
                fi
            fi
        fi

        echo "Pulling latest changes..."
        git pull origin main

        echo "Rebuilding and restarting services..."
        sudo docker compose -f docker-compose.prod.yml up -d --build

        echo "Checking service health..."
        sleep 5
        sudo docker compose -f docker-compose.prod.yml ps

        echo ""
        echo "Testing endpoints..."
        curl -s -o /dev/null -w "Frontend: HTTP %{http_code}\n" http://127.0.0.1:3000/ || echo "Frontend: FAILED"
        curl -s -o /dev/null -w "API:      HTTP %{http_code}\n" http://127.0.0.1:8001/docs || echo "API: FAILED"
DEPLOY_SCRIPT

    if [[ $? -eq 0 ]]; then
        print_success "Production deployment complete!"
        echo ""
        print_info "Production URL: https://mrmqmistest.org"
    else
        print_error "Deployment encountered errors"
        return 1
    fi
}

# Main script
main() {
    cd "$(dirname "$0")/.." || exit 1

    case "${1:-}" in
        --status|-s)
            show_status
            ;;
        --prod-only|-p)
            deploy_to_prod
            ;;
        --help|-h)
            echo "Usage: ./scripts/deploy.sh [options] [commit-message]"
            echo ""
            echo "Options:"
            echo "  --status, -s     Show repository status only"
            echo "  --prod-only, -p  Deploy to production without git operations"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./scripts/deploy.sh                           # Interactive mode"
            echo "  ./scripts/deploy.sh \"fix: resolve bug\"        # With commit message"
            echo "  ./scripts/deploy.sh --status                  # Check status"
            echo "  ./scripts/deploy.sh --prod-only               # Just deploy to prod"
            ;;
        *)
            # Full deployment flow
            show_status

            echo ""
            read -p "Continue with deployment? (y/n): " confirm
            if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
                echo "Aborted."
                exit 0
            fi

            git_push "$1"

            echo ""
            read -p "Deploy to production server? (y/n): " deploy_confirm
            if [[ "$deploy_confirm" == "y" || "$deploy_confirm" == "Y" ]]; then
                deploy_to_prod
            else
                print_info "Skipping production deployment"
            fi

            print_header "Deployment Summary"
            print_success "All operations completed successfully"
            echo ""
            echo "Local:  $(git log --oneline -1)"
            echo "Remote: $REMOTE/$BRANCH"
            ;;
    esac
}

main "$@"
