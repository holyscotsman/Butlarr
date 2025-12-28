#!/bin/bash
# =============================================================================
# Butlarr Update Script
# Quick update without full reinstall
# =============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                  BUTLARR UPDATER                             ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"

# Method 1: Container restart (if auto-update enabled)
if docker inspect butlarr &>/dev/null; then
    # Check if auto-update is enabled
    AUTO_UPDATE=$(docker inspect butlarr --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E "^AUTO_UPDATE=" | cut -d'=' -f2)

    if [ "$AUTO_UPDATE" = "true" ]; then
        echo -e "${YELLOW}Auto-update is enabled. Restarting container to pull latest code...${NC}"
        docker restart butlarr
        echo -e "${GREEN}✓ Container restarted. Updates will be applied automatically.${NC}"
        echo ""
        echo -e "${YELLOW}View logs:${NC} docker logs -f butlarr"
        exit 0
    fi
fi

# Method 2: Manual rebuild
INSTALL_DIR="${BUTLARR_INSTALL_DIR:-/mnt/user/appdata/butlarr}"

if [ ! -d "$INSTALL_DIR/.git" ]; then
    echo -e "${YELLOW}No installation found. Running full install...${NC}"
    curl -fsSL https://raw.githubusercontent.com/holyscotsman/Butlarr/claude/setup-butlarr-plex-manager-pFtxL/install.sh | bash
    exit 0
fi

echo -e "${CYAN}► Pulling latest changes...${NC}"
cd "$INSTALL_DIR"
BEFORE=$(git rev-parse --short HEAD)
git fetch origin
git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)
AFTER=$(git rev-parse --short HEAD)

if [ "$BEFORE" = "$AFTER" ]; then
    echo -e "${GREEN}✓ Already up to date ($AFTER)${NC}"
else
    echo -e "${GREEN}✓ Updated $BEFORE → $AFTER${NC}"

    echo -e "${CYAN}► Rebuilding image...${NC}"
    docker build -t butlarr:latest . --quiet

    echo -e "${CYAN}► Restarting container...${NC}"
    docker restart butlarr

    echo -e "${GREEN}✓ Update complete!${NC}"
fi

echo ""
echo -e "${YELLOW}View logs:${NC} docker logs -f butlarr"
