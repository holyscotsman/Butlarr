#!/bin/bash
set -e

# =============================================================================
# Butlarr Entrypoint Script
# Handles: PUID/PGID, auto-updates from GitHub, model downloads, app start
# =============================================================================

PUID=${PUID:-1000}
PGID=${PGID:-1000}
APP_DIR="/app"
DATA_DIR="/app/data"
MODELS_DIR="/app/data/models"
REPO_URL=${BUTLARR_REPO:-""}
AUTO_UPDATE=${AUTO_UPDATE:-"true"}
BRANCH=${BRANCH:-"main"}

echo "
╔══════════════════════════════════════════════════════════════╗
║                    BUTLARR v2512.1.0                         ║
║            AI-Powered Plex Library Manager                   ║
╚══════════════════════════════════════════════════════════════╝
"

# -----------------------------------------------------------------------------
# Step 1: Setup user/group permissions (Unraid compatibility)
# -----------------------------------------------------------------------------
echo "► Setting up permissions (PUID=$PUID, PGID=$PGID)..."

# Get the group name for the specified GID (might already exist, e.g., 'users' on Unraid)
EXISTING_GROUP=$(getent group "$PGID" | cut -d: -f1)

if [ -n "$EXISTING_GROUP" ]; then
    # GID already exists - use that group
    GROUP_NAME="$EXISTING_GROUP"
    echo "  Using existing group: $GROUP_NAME (GID $PGID)"
else
    # Create new group with specified GID
    GROUP_NAME="butlarr"
    groupadd -g "$PGID" "$GROUP_NAME" 2>/dev/null || true
    echo "  Created group: $GROUP_NAME (GID $PGID)"
fi

# Create user if it doesn't exist
if ! getent passwd butlarr > /dev/null 2>&1; then
    useradd -u "$PUID" -g "$PGID" -d "$APP_DIR" -s /bin/bash butlarr 2>/dev/null || true
else
    # Update existing user's UID/GID
    usermod -u "$PUID" -g "$PGID" butlarr 2>/dev/null || true
fi

# Ensure directories exist
mkdir -p "$DATA_DIR" "$MODELS_DIR" "$DATA_DIR/logs" "$DATA_DIR/reports"

# Set ownership using the correct group name (might be 'users' on Unraid, not 'butlarr')
chown -R butlarr:"$GROUP_NAME" "$DATA_DIR"
chown -R butlarr:"$GROUP_NAME" "$APP_DIR/backend" 2>/dev/null || true
chown -R butlarr:"$GROUP_NAME" "$APP_DIR/frontend" 2>/dev/null || true

echo "  ✓ Permissions configured"

# -----------------------------------------------------------------------------
# Step 2: Auto-update from GitHub (if configured)
# -----------------------------------------------------------------------------
if [ -n "$REPO_URL" ] && [ "$AUTO_UPDATE" = "true" ]; then
    echo "► Checking for updates from GitHub..."
    
    cd "$APP_DIR"
    
    if [ -d ".git" ]; then
        # Existing repo - pull updates
        echo "  Pulling latest changes from $BRANCH..."
        
        # Stash any local changes (like config edits)
        git stash --quiet 2>/dev/null || true
        
        # Fetch and show what's new
        git fetch origin "$BRANCH" --quiet
        
        LOCAL=$(git rev-parse HEAD)
        REMOTE=$(git rev-parse "origin/$BRANCH")
        
        if [ "$LOCAL" != "$REMOTE" ]; then
            echo "  ✓ New updates found! Updating..."
            git reset --hard "origin/$BRANCH"
            
            # Reinstall Python dependencies if requirements changed
            if git diff --name-only "$LOCAL" "$REMOTE" | grep -q "requirements.txt"; then
                echo "  ✓ Requirements changed, updating dependencies..."
                pip install -r requirements.txt --quiet --break-system-packages
            fi
            
            # Rebuild frontend if changed
            if git diff --name-only "$LOCAL" "$REMOTE" | grep -q "frontend/"; then
                echo "  ✓ Frontend changed, rebuilding..."
                cd frontend && npm install --silent && npm run build --silent && cd ..
            fi
            
            echo "  ✓ Updated to $(git rev-parse --short HEAD)"
        else
            echo "  ✓ Already up to date ($(git rev-parse --short HEAD))"
        fi
    else
        # Fresh clone
        echo "  Cloning repository..."
        git clone --branch "$BRANCH" --single-branch "$REPO_URL" /tmp/butlarr-clone
        cp -r /tmp/butlarr-clone/* "$APP_DIR/"
        cp -r /tmp/butlarr-clone/.git "$APP_DIR/"
        rm -rf /tmp/butlarr-clone
        
        # Install dependencies
        echo "  Installing Python dependencies..."
        pip install -r requirements.txt --quiet --break-system-packages
        
        # Build frontend
        echo "  Building frontend..."
        cd frontend && npm install --silent && npm run build --silent && cd ..
        
        echo "  ✓ Repository cloned and built"
    fi
fi

# -----------------------------------------------------------------------------
# Step 3: Download AI model if needed (and enabled)
# -----------------------------------------------------------------------------
EMBEDDED_AI=${EMBEDDED_AI:-"true"}
MODEL_NAME=${MODEL_NAME:-"qwen2.5-1.5b-instruct"}
MODEL_FILE="$MODELS_DIR/$MODEL_NAME.Q4_K_M.gguf"

if [ "$EMBEDDED_AI" = "true" ] && [ ! -f "$MODEL_FILE" ]; then
    echo "► Downloading embedded AI model ($MODEL_NAME)..."
    echo "  This is a one-time download (~1GB). Please wait..."
    
    # Qwen2.5-1.5B quantized model from HuggingFace
    MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    
    if command -v wget &> /dev/null; then
        wget -q --show-progress -O "$MODEL_FILE" "$MODEL_URL" || {
            echo "  ⚠ Model download failed. Embedded AI will be unavailable."
            echo "  You can still use Anthropic/OpenAI APIs."
            rm -f "$MODEL_FILE"
        }
    elif command -v curl &> /dev/null; then
        curl -L --progress-bar -o "$MODEL_FILE" "$MODEL_URL" || {
            echo "  ⚠ Model download failed. Embedded AI will be unavailable."
            rm -f "$MODEL_FILE"
        }
    fi
    
    if [ -f "$MODEL_FILE" ]; then
        chown butlarr:"$GROUP_NAME" "$MODEL_FILE"
        echo "  ✓ Model downloaded successfully"
    fi
elif [ "$EMBEDDED_AI" = "true" ] && [ -f "$MODEL_FILE" ]; then
    echo "► Embedded AI model found: $MODEL_NAME"
fi

# -----------------------------------------------------------------------------
# Step 4: Run database migrations
# -----------------------------------------------------------------------------
echo "► Checking database..."

# Run migrations if alembic is configured (alembic.ini is in backend/)
if [ -f "$APP_DIR/backend/alembic.ini" ]; then
    echo "  Running database migrations..."
    cd "$APP_DIR/backend"

    # Check if this is a fresh database (no alembic_version table)
    # If so, stamp it as current since tables were created by SQLAlchemy
    if ! gosu butlarr python -c "
from backend.db.database import get_db_path
import sqlite3
db_path = get_db_path()
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'\")
    has_alembic = cursor.fetchone() is not None
    conn.close()
    exit(0 if has_alembic else 1)
else:
    exit(1)
" 2>/dev/null; then
        # Database exists but no alembic_version table - stamp current version
        if [ -f "$DATA_DIR/butlarr.db" ]; then
            echo "  Stamping existing database with current migration..."
            gosu butlarr alembic stamp head 2>/dev/null || true
        fi
    fi

    # Run any pending migrations
    gosu butlarr alembic upgrade head 2>/dev/null && echo "  ✓ Database migrations complete" || echo "  ✓ Database ready"
    cd "$APP_DIR"
else
    echo "  ✓ Database will be initialized on first run"
fi

# -----------------------------------------------------------------------------
# Step 5: Start the application
# -----------------------------------------------------------------------------
echo "► Starting Butlarr..."
echo ""
echo "  Web UI:     http://localhost:${PORT:-8765}"
echo "  API Docs:   http://localhost:${PORT:-8765}/docs"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Run as butlarr user
cd "$APP_DIR"
exec gosu butlarr python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8765} \
    --log-level ${LOG_LEVEL:-info}
