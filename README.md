# Butlarr

A media library manager for Plex that helps identify and remove low-quality content, find duplicates, detect issues, and keep your library organized.

## What It Does

Butlarr scans your Plex library and integrates with your existing *arr stack to:

- Identify movies worth removing based on ratings and watch history
- Detect duplicate files and suggest which to keep
- Find quality issues (corrupt files, outdated codecs, wrong resolutions)
- Check file integrity without playing every file manually
- Analyze collections for missing entries
- Generate recommendations for what to add next

## Installation

### Docker (Recommended)

```bash
docker run -d \
  --name butlarr \
  -p 8765:8765 \
  -v /path/to/data:/app/data \
  -v /path/to/media:/media:ro \
  ghcr.io/holyscotsman/butlarr:latest
```

### Docker Compose

```yaml
services:
  butlarr:
    image: ghcr.io/holyscotsman/butlarr:latest
    container_name: butlarr
    ports:
      - "8765:8765"
    volumes:
      - ./data:/app/data
      - /path/to/media:/media:ro
    environment:
      - TZ=America/New_York
    restart: unless-stopped
```

## Setup

1. Open `http://your-server:8765` in your browser
2. Add your Plex server URL and token
3. Optionally connect Radarr, Sonarr, Overseerr
4. Run your first scan

### Getting Your Plex Token

The easiest way:
1. Open any item in Plex Web
2. Click the three dots menu → "Get Info"
3. Click "View XML"
4. Look for `X-Plex-Token=` in the URL

## AI Features

Butlarr can use AI to analyze your library and make smarter decisions about what to keep or remove.

### Built-in (No API Key Required)

Runs a local Qwen model. Downloads ~1GB on first use. Slower but completely free and private.

### Cloud Options

For faster analysis, add your API key in Settings:
- Anthropic (Claude)
- OpenAI (GPT-4)
- Ollama (self-hosted)

## Scan Phases

| Phase | What It Does |
|-------|--------------|
| 1 | Sync library from Plex |
| 2 | AI analysis (if enabled) |
| 3-4 | Cross-reference with Radarr/Sonarr/Overseerr |
| 5 | Find incomplete collections |
| 6-7 | Check file organization |
| 8-10 | Deep scan for duplicates and naming issues |
| 11-12 | Verify file integrity |
| 13-15 | Check audio languages, HDR, subtitles |
| 16-17 | Storage and codec analysis |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | UTC | Timezone |
| `PORT` | 8765 | Web interface port |
| `LOG_LEVEL` | info | Logging verbosity |
| `AUTO_UPDATE` | true | Pull latest on restart |
| `EMBEDDED_AI` | true | Enable local AI model |

## Path Mapping

If Plex sees files at `/movies` but your container sees them at `/media/Movies`, configure path mappings in Settings → Path Mappings.

## FAQ

**Why is the first scan slow?**

The initial library sync fetches metadata for every item. Subsequent scans are faster as they only check for changes.

**Will this delete my files?**

No. Butlarr only identifies issues and makes recommendations. You decide what to do with them.

**Does it work with Jellyfin/Emby?**

Not currently. Plex only for now.

## Development

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

API docs available at `/docs` when running.

## License

MIT
