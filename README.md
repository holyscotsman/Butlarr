# Butlarr 🎬🤖

**AI-Powered Plex Library Manager**

Butlarr is a comprehensive media library management tool that uses AI to analyze, curate, and maintain your Plex library. It integrates with Radarr, Sonarr, Overseerr, and more.

![Version](https://img.shields.io/badge/version-2512.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **17-Phase Deep Scanning** - Comprehensive library analysis
- **AI-Powered Curation** - Smart recommendations and bad movie detection
- **Embedded AI** - Works offline with local Qwen2.5 model (no API keys needed)
- **Cloud AI Support** - Anthropic Claude, OpenAI GPT-4, Ollama
- **Auto-Updates** - Pull latest code on container restart
- **Duplicate Detection** - Find and manage duplicate files
- **Quality Analysis** - HDR, codec, bitrate, resolution checks
- **Integrity Verification** - Detect corrupt media files
- **Collection Management** - Find incomplete collections
- **Real-time Progress** - WebSocket-based live updates

## Quick Start (Unraid)

### Option 1: Docker Run

```bash
docker run -d \
  --name butlarr \
  --restart unless-stopped \
  -p 8765:8765 \
  -v /mnt/user/appdata/butlarr:/app/data \
  -v /mnt/user:/media:ro \
  -e PUID=99 \
  -e PGID=100 \
  -e TZ=America/New_York \
  -e BUTLARR_REPO=https://github.com/YOUR_USERNAME/butlarr.git \
  -e AUTO_UPDATE=true \
  ghcr.io/YOUR_USERNAME/butlarr:latest
```

### Option 2: Build Locally

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/butlarr.git
cd butlarr

# Build and run
docker build -t butlarr:latest .
docker run -d \
  --name butlarr \
  -p 8765:8765 \
  -v /mnt/user/appdata/butlarr:/app/data \
  -v /mnt/user:/media:ro \
  butlarr:latest
```

## Configuration

Access the web UI at `http://YOUR_IP:8765` and configure:

1. **Plex** - URL and token
2. **Radarr** - URL and API key (optional)
3. **Sonarr** - URL and API key (optional)
4. **Overseerr** - URL and API key (optional)
5. **AI** - Anthropic/OpenAI keys (optional - embedded AI works without)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | 1000 | User ID for file permissions |
| `PGID` | 1000 | Group ID for file permissions |
| `TZ` | UTC | Timezone |
| `PORT` | 8765 | Web UI port |
| `BUTLARR_REPO` | - | GitHub repo URL for auto-updates |
| `AUTO_UPDATE` | true | Enable auto-updates on restart |
| `BRANCH` | main | Git branch to track |
| `EMBEDDED_AI` | true | Download embedded AI model |
| `LOG_LEVEL` | info | Logging verbosity |

## Updating

### Automatic (Recommended)
Simply restart the container - it pulls the latest code automatically.

### Manual
1. Go to Settings in the web UI
2. Click "Check for Updates"
3. Click "Apply Update" if available
4. Restart the container

### From Command Line
```bash
docker restart butlarr
```

## AI Providers

### Embedded AI (Default)
- **Model**: Qwen2.5-1.5B-Instruct (Q4 quantized)
- **Size**: ~1GB download on first run
- **Speed**: ~10-30 tokens/sec on CPU
- **Cost**: Free!
- **Quality**: Good for basic analysis

### Cloud APIs (Optional, Faster)
- **Anthropic Claude** - Best quality, recommended
- **OpenAI GPT-4** - Great alternative
- **Ollama** - Self-hosted option

## Development

```bash
# Backend
cd backend
pip install -r ../requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## API Documentation

Once running, visit `http://YOUR_IP:8765/docs` for interactive API docs.

## License

MIT License - See LICENSE file

## Credits

Created with assistance from Claude (Anthropic)
