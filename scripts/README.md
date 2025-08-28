# Caddy Cloudflare Cache Builder

Custom Caddy image with Cloudflare DNS, Cloudflare IP plugin, and Souin HTTP cache (plus multiple Souin storages). Includes a local watcher to mirror upstream Caddy 2.x tags and automatically build and push multi-arch images to Docker Hub and GHCR using docker buildx.

## Dockerfile

The Dockerfile builds Caddy with:

- Cloudflare DNS: `github.com/caddy-dns/cloudflare`
- Cloudflare IP plugin: `github.com/WeidiDeng/caddy-cloudflare-ip`
- Souin plugin: `github.com/darkweak/souin/plugins/caddy`
- Storages: badger, redis, etcd, nuts, olric, nats, otter, simplefs

Build args allow mirroring upstream tags:

- `CADDY_TAG` (default: `latest`) used for final image base
- `CADDY_BUILDER_TAG` (default: `builder`) used for the build stage

### Local build (manual)

Build a specific upstream tag locally with buildx (multi-arch):

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg CADDY_TAG=2.7.6-alpine \
  --build-arg CADDY_BUILDER_TAG=2.7.6-alpine-builder \
  -t melonsmasher/caddy-cloudflare-cache:2.7.6-alpine \
  .
```

Notes:

- `CADDY_BUILDER_TAG` should point to a builder image that includes `xcaddy` (e.g., `<tag>-builder` or `builder`).
- The final stage uses `FROM caddy:${CADDY_TAG}` and copies the built `/usr/bin/caddy` from the builder stage.

## Local Watcher and Builder

Script: `scripts/watch_build.py`

- Lists upstream tags from Docker Hub for `library/caddy`
- Filters 2.x tags (including `-alpine`) and excludes `-builder`
- Resolves manifest digest via Docker Registry API v2
- Stores tag/digest in SQLite
- Builds and pushes multi-arch images using buildx to Docker Hub and GHCR

### Requirements

- Python 3.9+
- Docker with buildx, QEMU/binfmt for cross-arch
- Logged-in Docker sessions for Docker Hub and GHCR

Install Python deps (recommended: venv inside `scripts/`):

```bash
cd scripts
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Ensure buildx is available.

Login to registries:

```bash
docker login
docker login ghcr.io
```

### Environment variables

- `TARGET_REPO_DOCKERHUB` (default: `melonsmasher/caddy-cloudflare-cache`)
- `TARGET_REPO_GHCR` (default: `ghcr.io/melonsmasher/caddy-cloudflare-cache`)
- `STATE_DB` (default: `scripts/state.db`)
- `PLATFORMS` (default: `linux/amd64,linux/arm64`)
- `POLL_INTERVAL` seconds (default: `600`)

### Run one cycle

```bash
cd scripts
source venv/bin/activate
python watch_build.py --once
```

### Run continuously

```bash
cd scripts
source venv/bin/activate
python watch_build.py
```

Optional systemd unit (example):

```ini
[Unit]
Description=Caddy Mirror Watcher
After=docker.service

[Service]
WorkingDirectory=%h/caddy-cloudflare-cache
Environment=TARGET_REPO_DOCKERHUB=melonsmasher/caddy-cloudflare-cache
Environment=TARGET_REPO_GHCR=ghcr.io/melonsmasher/caddy-cloudflare-cache
ExecStart=/usr/bin/python3 scripts/watch_build.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Notes

- The watcher automatically picks a matching `<tag>-builder` if available; otherwise it falls back to the generic `builder` image for the build stage.
- Ensure your Docker daemon is running before invoking builds.
