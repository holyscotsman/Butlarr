# Butlarr Setup Guide

## Prerequisites

- Docker installed
- Access to your Plex server
- (Optional) Radarr, Sonarr, Overseerr

## Quick Start

```bash
docker run -d \
  --name butlarr \
  -p 8765:8765 \
  -v /path/to/data:/app/data \
  -v /path/to/media:/media:ro \
  ghcr.io/holyscotsman/butlarr:latest
```

Then open `http://your-server:8765` in your browser.

## Unraid Users

### Command Line

```bash
# Clone and build
cd /mnt/user/appdata
git clone https://github.com/holyscotsman/butlarr.git
cd butlarr
docker build -t butlarr:latest .

# Run
docker run -d \
  --name butlarr \
  --restart unless-stopped \
  -p 8765:8765 \
  -v /mnt/user/appdata/butlarr/data:/app/data \
  -v /mnt/user:/media:ro \
  -e PUID=99 \
  -e PGID=100 \
  -e TZ=America/New_York \
  butlarr:latest
```

## Configuration

### Plex Token

1. Open any media item in Plex Web
2. Click (...) → Get Info → View XML
3. Find `X-Plex-Token=` in the URL

### Service Connections

In the Settings page, add:
- **Plex**: URL (http://ip:32400) and token
- **Radarr**: URL and API key from Settings → General
- **Sonarr**: URL and API key from Settings → General
- **Overseerr**: URL and API key from Settings → General

## Path Mapping

If Plex sees paths differently than the container, configure mappings:

| Plex Path | Container Path |
|-----------|---------------|
| /movies | /media/Movies |
| /tv | /media/TV |

Add these in Settings → Path Mappings.

## Updating

Just restart the container:

```bash
docker restart butlarr
```

Or use the "Check for Updates" button in Settings.

## Troubleshooting

### Check Logs
```bash
docker logs butlarr
```

### Container Won't Start
- Verify port 8765 isn't in use
- Check volume mount permissions
- Verify paths exist

### Plex Connection Fails
- Confirm Plex URL is reachable from the container
- Verify token is correct (no extra spaces)
- Try the URL in your browser first

### Scan Gets Stuck
- Check Plex is still accessible
- Look at logs for specific errors
- Restart the container and try again
