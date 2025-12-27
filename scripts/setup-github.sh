#!/bin/bash
# =============================================================================
# Butlarr GitHub Setup Script
# Run this script to initialize your GitHub repository
# =============================================================================

set -e

echo "
╔══════════════════════════════════════════════════════════════╗
║           Butlarr GitHub Repository Setup                    ║
╚══════════════════════════════════════════════════════════════╝
"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed. Please install git first."
    exit 1
fi

# Get GitHub username
read -p "Enter your GitHub username: " GITHUB_USER

if [ -z "$GITHUB_USER" ]; then
    echo "Error: GitHub username is required"
    exit 1
fi

REPO_NAME="butlarr"
REPO_URL="https://github.com/$GITHUB_USER/$REPO_NAME.git"

echo ""
echo "This script will:"
echo "  1. Initialize a git repository"
echo "  2. Configure it to push to: $REPO_URL"
echo "  3. Create the initial commit"
echo ""
echo "Before running this script, you need to:"
echo "  1. Create a new repository on GitHub named '$REPO_NAME'"
echo "  2. Do NOT initialize it with README, .gitignore, or license"
echo ""
read -p "Have you created the empty repository on GitHub? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo ""
    echo "Please create the repository first:"
    echo "  1. Go to https://github.com/new"
    echo "  2. Name it: $REPO_NAME"
    echo "  3. Keep it empty (don't add README)"
    echo "  4. Run this script again"
    exit 0
fi

# Initialize git repo
echo ""
echo "► Initializing git repository..."
git init

# Configure git (if not already configured)
if [ -z "$(git config user.email)" ]; then
    read -p "Enter your email for git commits: " GIT_EMAIL
    git config user.email "$GIT_EMAIL"
fi

if [ -z "$(git config user.name)" ]; then
    read -p "Enter your name for git commits: " GIT_NAME
    git config user.name "$GIT_NAME"
fi

# Add remote
echo "► Adding remote origin..."
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

# Add all files
echo "► Staging files..."
git add -A

# Create initial commit
echo "► Creating initial commit..."
git commit -m "Initial commit - Butlarr v2512.1.0"

# Push to GitHub
echo "► Pushing to GitHub..."
echo ""
echo "You may be prompted for your GitHub credentials."
echo "If using 2FA, use a Personal Access Token as your password."
echo ""

git branch -M main
git push -u origin main

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✓ Success! Your repository is now at:"
echo "  https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
echo "Next steps:"
echo "  1. Update your docker-compose.yml or Unraid template with:"
echo "     BUTLARR_REPO=$REPO_URL"
echo ""
echo "  2. To update Butlarr in the future:"
echo "     - Make changes to files"
echo "     - Run: git add -A && git commit -m 'Your message' && git push"
echo "     - Restart your container"
echo "═══════════════════════════════════════════════════════════════"
