# Caddy Cloudflare Cache

[![GitHub](https://img.shields.io/badge/GitHub-gray?logo=github)](https://github.com/melonsmasher/caddy-cloudflare-cache) [![DockerHub](https://img.shields.io/badge/DockerHub-white?logo=docker)](https://hub.docker.com/r/melonsmasher/caddy-cloudflare-cache) [![License](https://img.shields.io/github/license/melonsmasher/papercut-mf-site)](https://raw.githubusercontent.com/melonsmasher/caddy-cloudflare-cache/master/LICENSE)

## Overview

Prebuilt Caddy image with:

- Cloudflare DNS provider for DNS-01 certificates
- Cloudflare IP plugin for real client IP behind Cloudflare
- Souin HTTP cache (multiple storage backends available)

Images are published to:

- Docker Hub: `melonsmasher/caddy-cloudflare-cache`
- GHCR: `ghcr.io/melonsmasher/caddy-cloudflare-cache`

## Supported tags

- Tracks upstream Caddy 2.x tags, including `-alpine` variants, e.g.:
  - `:2`, `:2-alpine`
  - Specific versions when available, e.g. `:2.7.6`, `:2.7.6-alpine`

## Included plugins

- `github.com/caddy-dns/cloudflare`
- `github.com/WeidiDeng/caddy-cloudflare-ip`
- `github.com/darkweak/souin/plugins/caddy`
- Storages for Souin: badger, redis, etcd, nuts, olric, nats, otter, simplefs

## Pulling the image

- Docker Hub:
  - `docker pull melonsmasher/caddy-cloudflare-cache:2`
  - `docker pull melonsmasher/caddy-cloudflare-cache:2-alpine`
- GHCR:
  - `docker pull ghcr.io/melonsmasher/caddy-cloudflare-cache:2`
  - `docker pull ghcr.io/melonsmasher/caddy-cloudflare-cache:2-alpine`

## Quick start (docker run)

1) Create a `Caddyfile` in your working directory.
2) Run:

```bash
docker run -d --name caddy \
  -p 80:80 -p 443:443 \
  -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" \
  -v caddy_data:/data \
  -v caddy_config:/config \
  melonsmasher/caddy-cloudflare-cache:2
```

## Quick start (docker compose)

```yaml
services:
  caddy:
    image: melonsmasher/caddy-cloudflare-cache:2
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    environment:
      # Cloudflare API token for DNS-01 challenge
      CLOUDFLARE_API_TOKEN: "your_token"
      # Only needed if using static trusted proxies
      # CADDY_TRUSTED_PROXIES: "1.2.3.4/32 5.6.7.8/32"

volumes:
  caddy_data:
  caddy_config:
```

## Minimal Caddyfile example

```caddyfile
# Global options
{
  servers {
    # Set client IP headers
    client_ip_headers CF-Connecting-IP X-Real-IP X-Forwarded-For Client-IP X-Client-IP
    # Set trusted proxies to Cloudflare addresses
    trusted_proxies cloudflare {
      # Pull the Cloudflare IP addresses from the Cloudflare API every x hours
      interval 12h
      # Set timeout for the Cloudflare API request
      timeout 15s
    }
    # Add static trusted proxies if needed
    #trusted_proxies static {$CADDY_TRUSTED_PROXIES}
  }
}

example.com {
  root * /srv/www
  file_server

  # Souin plugin basic enablement with Redis storage
  # See https://github.com/darkweak/souin for more details
  cache {
    redis {
      url redis:6379
    }
  }

  # DNS-01 via Cloudflare
  tls {
    dns cloudflare {$CLOUDFLARE_API_TOKEN}
    # Set custom resolvers if needed
    #resolvers 1.1.1.1 8.8.8.8
    # Set custom propagation timeout if needed
    #propagation_timeout 15m
  }
}
```

## Cloudflare DNS-01 notes

- Set `CLOUDFLARE_API_TOKEN` with suitable permissions for DNS-01.
- Enable the Cloudflare DNS provider in a `tls` block in your `Caddyfile`.
- Refer to `github.com/caddy-dns/cloudflare` for all supported variables and token scopes.

## Cloudflare IP plugin notes

- Included: `github.com/WeidiDeng/caddy-cloudflare-ip`
- Refer to the plugin repository for configuration and usage details.

## Souin cache notes

- Enable the Souin Caddy plugin with a `souin { ... }` block inside your site.
- You can configure default cache TTLs, keys, and select storage backends.
- Refer to `github.com/darkweak/souin` docs for full configuration.

## Build system

See `scripts/README.md` for details on how images are built and mirrored from upstream tags.

## Persistence

- `/data`: ACME certs and state
- `/config`: Caddy config storage

Use volumes or host mounts so certs persist across container restarts.

## Troubleshooting

- TLS issuance with DNS-01 failing: verify Cloudflare token, DNS propagation, and Caddyfile `tls` block.
- Souin not caching: ensure the `souin` block is present and that your routes/methods/headers match the cache rules.
