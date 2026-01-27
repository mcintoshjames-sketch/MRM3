# Audit Report: scripts/deploy.sh

**Date:** December 22, 2025
**Subject:** Security and Conceptual Audit of Deployment Script
**Status:** Issues Identified

## Executive Summary

The `scripts/deploy.sh` script is a utility for automating the git commit, push, and server deployment workflow. While functional, it contains significant conceptual flaws regarding git hygiene and one critical operational risk regarding file permissions on the production server.

## Critical Findings (Operational & Security)

### 1. Incorrect Use of `sudo` with Git (High Risk)
**Location:** `deploy_to_prod` function
```bash
sudo git pull origin main
```
**Issue:** Running `git pull` with `sudo` is a major anti-pattern.
*   **Permission Corruption:** If the repository in `/opt/mrm` was cloned by the `mrm-admin` user, running `git` as root will change the ownership of internal `.git` files (like `FETCH_HEAD`) to root. Subsequent git operations by the `mrm-admin` user (without sudo) will fail with "Permission denied".
*   **Security Principle:** Git operations should run with the least privilege necessary (the repo owner), not root.

### 2. Aggressive "Commit All" Workflow (Medium Risk)
**Location:** `git_push` function
```bash
git add -A
```
**Issue:** The script blindly stages *every* file in the workspace (untracked, modified, deleted) before committing.
*   **Accidental Commits:** This dramatically increases the risk of committing temporary files, secrets, or unfinished work that wasn't intended for the repository.
*   **Lack of Granularity:** It bypasses the staging area's purpose, treating the entire workspace as a single atomic unit.

## Conceptual & Logic Findings

### 1. Inefficient Build Strategy
**Location:** `deploy_to_prod` function
```bash
sudo docker compose ... build --no-cache
```
**Issue:** Using `--no-cache` forces a complete rebuild of all Docker layers (installing dependencies, etc.) on *every* deployment, even if only a single line of code changed.
*   **Impact:** significantly slower deployment times and unnecessary CPU usage on the production server.
*   **Recommendation:** Remove `--no-cache`. Docker is smart enough to rebuild only changed layers.

### 2. Commit Message Logic Flaw
**Location:** `generate_commit_message` vs `git_push`
**Issue:**
1. `generate_commit_message` prioritizes staged files (`diff --cached`) if they exist.
2. `git_push` then runs `git add -A` (staging everything).
3. **Result:** If you had some files staged and some unstaged, the generated message will *only* describe the originally staged files, but the commit will contain *everything*. The message will be inaccurate.

### 3. Hardcoded Attribution
**Location:** `git_push` function
```bash
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```
**Issue:** The script hardcodes a specific AI model signature into every commit. This is inaccurate metadata if the code was written by a human or a different AI (like the current session).

## Recommendations

### Immediate Fixes
1.  **Remove `sudo` from `git pull`**: Run git as the SSH user. Only use `sudo` for docker commands.
2.  **Remove `--no-cache`**: Allow Docker to use layer caching for faster deploys.
3.  **Fix Git Workflow**:
    *   Ideally, remove `git add -A` and only commit what the user has staged.
    *   Alternatively, prompt the user for confirmation before staging untracked files.

### Proposed Code Fixes

```bash
# 1. Fix Permissions (Run as user, not root)
echo "Pulling latest changes..."
git pull origin main  # Removed sudo

# 2. Optimize Build
echo "Rebuilding containers..."
sudo docker compose -f docker-compose.prod.yml up -d --build # Combined build & up, removed --no-cache
```

## Conclusion
The script is a "convenience" wrapper that sacrifices safety and correctness for speed. The `sudo git pull` command is the most dangerous element and should be patched immediately to prevent repository corruption on the server.
