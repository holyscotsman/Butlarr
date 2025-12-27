# Butlarr Setup Guide

Complete step-by-step guide to set up Butlarr with GitHub for easy updates.

---

## Part 1: Create Your GitHub Repository

### Step 1: Create a GitHub Account (if needed)
1. Go to https://github.com/signup
2. Create an account with your email

### Step 2: Create a New Repository
1. Go to https://github.com/new
2. Fill in:
   - **Repository name**: `butlarr`
   - **Description**: `AI-Powered Plex Library Manager`
   - **Visibility**: Private (recommended) or Public
   - ⚠️ **DO NOT** check "Add a README file"
   - ⚠️ **DO NOT** add .gitignore or license
3. Click **Create repository**
4. You'll see a page with setup instructions - keep this open

---

## Part 2: Upload Code to GitHub

### Option A: Using Command Line (Recommended)

**On your computer:**

```bash
# 1. Extract the zip to a folder
unzip butlarr-2512.1.0.zip -d butlarr
cd butlarr

# 2. Initialize git
git init

# 3. Configure git (if first time)
git config user.email "your-email@example.com"
git config user.name "Your Name"

# 4. Add your GitHub repository as remote
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/butlarr.git

# 5. Add all files and commit
git add -A
git commit -m "Initial commit - Butlarr v2512.1.0"

# 6. Push to GitHub
git branch -M main
git push -u origin main
```

When prompted for credentials:
- **Username**: Your GitHub username
- **Password**: Your GitHub Personal Access Token (not your regular password)

**To create a Personal Access Token:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name like "butlarr-push"
4. Select scopes: `repo` (full control)
5. Click Generate and copy the token
6. Use this token as your password

### Option B: Using GitHub Desktop (Easier for beginners)

1. Download GitHub Desktop from https://desktop.github.com
2. Sign in with your GitHub account
3. File → Add Local Repository
4. Navigate to the extracted butlarr folder
5. Click "Publish repository"
6. Uncheck "Keep this code private" if you want it public
7. Click "Publish Repository"

### Option C: Upload via GitHub Web Interface

1. Go to your new repository on GitHub
2. Click "uploading an existing file" link
3. Drag and drop ALL files from the extracted zip
4. Scroll down, add commit message: "Initial commit"
5. Click "Commit changes"

⚠️ Note: This method is slower for many files

---

## Part 3: Deploy on Unraid

### Step 1: Build the Docker Image

SSH into your Unraid server or use the terminal:

```bash
# Go to appdata
cd /mnt/user/appdata

# Clone your repo
git clone https://github.com/YOUR_USERNAME/butlarr.git
cd butlarr

# Build the image
docker build -t butlarr:2512.1.0 .
```

### Step 2: Run the Container

```bash
docker run -d \
  --name butlarr \
  --restart unless-stopped \
  -p 8765:8765 \
  -v /mnt/user/appdata/butlarr/data:/app/data \
  -v /mnt/user:/media:ro \
  -e PUID=99 \
  -e PGID=100 \
  -e TZ=America/New_York \
  -e BUTLARR_REPO=https://github.com/YOUR_USERNAME/butlarr.git \
  -e AUTO_UPDATE=true \
  butlarr:2512.1.0
```

### Step 3: Access the Web UI

Open your browser to: `http://YOUR_UNRAID_IP:8765`

---

## Part 4: Configure Butlarr

1. Open the web UI
2. Go to **Settings**
3. Enter your service URLs and API keys:
   - Plex URL and Token
   - Radarr URL and API Key (optional)
   - Sonarr URL and API Key (optional)
   - Overseerr URL and API Key (optional)
4. Click **Save Settings**

**To get your Plex Token:**
1. Open Plex web app
2. Click on any media item
3. Click the three dots (...) → Get Info → View XML
4. Look for `X-Plex-Token=` in the URL

---

## Part 5: Updating Butlarr

### Method 1: Automatic (On Container Restart)
Simply restart the container - it automatically pulls the latest code:
```bash
docker restart butlarr
```

### Method 2: From Web UI
1. Go to Settings → Updates
2. Click "Check for Updates"
3. Click "Apply Update" if available
4. Restart the container

### Method 3: Push Your Own Changes
When you make changes to the code:
```bash
cd /mnt/user/appdata/butlarr
git add -A
git commit -m "My changes"
git push
docker restart butlarr
```

---

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs butlarr

# Check permissions
ls -la /mnt/user/appdata/butlarr/data
```

### Git authentication fails
- Make sure you're using a Personal Access Token, not your password
- Token needs `repo` scope

### AI model download fails
- The embedded AI model (~1GB) downloads on first start
- Check your internet connection
- You can disable it: `-e EMBEDDED_AI=false`

### WebSocket connection issues
- Make sure port 8765 is not blocked
- Check if another container is using that port

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | 1000 | User ID |
| `PGID` | 1000 | Group ID |
| `TZ` | UTC | Timezone |
| `PORT` | 8765 | Web UI port |
| `BUTLARR_REPO` | - | GitHub repo for updates |
| `AUTO_UPDATE` | true | Auto-update on restart |
| `BRANCH` | main | Git branch |
| `EMBEDDED_AI` | true | Enable local AI |
| `LOG_LEVEL` | info | Logging level |

---

## Support

If you encounter issues:
1. Check the logs: `docker logs butlarr`
2. Check the web UI Settings page for system info
3. Create an issue on your GitHub repository
