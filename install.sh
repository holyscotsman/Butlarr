#!/bin/bash
# =============================================================================
# Butlarr Installer Script
# One-command installation for Unraid and other Docker hosts
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              BUTLARR INSTALLER v2512.1.0                     ║"
echo "║            AI-Powered Plex Library Manager                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Configuration
INSTALL_DIR="${BUTLARR_INSTALL_DIR:-/mnt/user/appdata/butlarr}"
DATA_DIR="${BUTLARR_DATA_DIR:-/mnt/user/appdata/butlarr/data}"
REPO_URL="${BUTLARR_REPO:-https://github.com/holyscotsman/Butlarr.git}"
BRANCH="${BUTLARR_BRANCH:-claude/setup-butlarr-plex-manager-pFtxL}"
PORT="${BUTLARR_PORT:-8765}"
PUID="${PUID:-1000}"
PGID="${PGID:-100}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Install Directory: $INSTALL_DIR"
echo "  Data Directory:    $DATA_DIR"
echo "  Repository:        $REPO_URL"
echo "  Branch:            $BRANCH"
echo "  Port:              $PORT"
echo "  PUID/PGID:         $PUID/$PGID"
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

# Check for git
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: Git is not installed or not in PATH${NC}"
    exit 1
fi

# Step 1: Create directories
echo -e "${CYAN}► Creating directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$DATA_DIR/models"
mkdir -p "$DATA_DIR/logs"

# Fix git ownership issues (common on Unraid/NAS systems)
git config --global --add safe.directory "$INSTALL_DIR" 2>/dev/null || true

# Step 2: Clone or update repository
echo -e "${CYAN}► Getting latest code...${NC}"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  Updating existing installation..."
    cd "$INSTALL_DIR"
    git fetch origin "$BRANCH" --quiet
    git checkout "$BRANCH" --quiet 2>/dev/null || git checkout -b "$BRANCH" "origin/$BRANCH" --quiet
    git reset --hard "origin/$BRANCH" --quiet
    echo -e "${GREEN}  ✓ Updated to $(git rev-parse --short HEAD)${NC}"
else
    echo "  Cloning fresh installation..."
    rm -rf "$INSTALL_DIR"/* "$INSTALL_DIR"/.[!.]* 2>/dev/null || true
    git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    echo -e "${GREEN}  ✓ Cloned $(git rev-parse --short HEAD)${NC}"
fi

# Step 3: Stop existing container if running
echo -e "${CYAN}► Stopping existing container...${NC}"
docker stop butlarr 2>/dev/null && echo "  Stopped butlarr" || echo "  No running container"
docker rm butlarr 2>/dev/null && echo "  Removed butlarr" || echo "  No container to remove"

# Step 4: Build Docker image
echo -e "${CYAN}► Building Docker image (this may take a few minutes)...${NC}"
docker build -t butlarr:latest "$INSTALL_DIR" --quiet
echo -e "${GREEN}  ✓ Image built successfully${NC}"

# Step 5: Start container
echo -e "${CYAN}► Starting Butlarr...${NC}"
docker run -d \
    --name butlarr \
    --restart unless-stopped \
    -p "$PORT:8765" \
    -e PUID="$PUID" \
    -e PGID="$PGID" \
    -e TZ="${TZ:-America/New_York}" \
    -e BUTLARR_REPO="$REPO_URL" \
    -e BRANCH="$BRANCH" \
    -e AUTO_UPDATE=true \
    -v "$DATA_DIR:/app/data" \
    butlarr:latest

# Step 6: Wait for container to be healthy
echo -e "${CYAN}► Waiting for Butlarr to start...${NC}"
for i in {1..30}; do
    if curl -s "http://localhost:$PORT/api/health" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Butlarr is running!${NC}"
        break
    fi
    sleep 2
    echo -n "."
done
echo ""

# Done!
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 INSTALLATION COMPLETE!                       ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                              ║"
echo "║  Web UI:      http://$(hostname -I | awk '{print $1}'):$PORT                       ║"
echo "║  Local:       http://localhost:$PORT                         ║"
echo "║                                                              ║"
echo "║  Data stored: $DATA_DIR                     ║"
echo "║                                                              ║"
echo "║  Auto-updates are ENABLED. Restart container to update.     ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Show logs
echo -e "${YELLOW}Showing startup logs (Ctrl+C to exit):${NC}"
docker logs -f butlarr
