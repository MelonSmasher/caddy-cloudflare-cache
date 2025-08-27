# Build Caddy with Cloudflare DNS and cache-handler (with Redis/Valkey storage) using xcaddy
FROM caddy:builder AS builder

# Build Caddy with required plugins
RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/caddyserver/cache-handler \
    --with github.com/darkweak/storages/redis/caddy

# Final image
FROM caddy:latest
COPY --from=builder /usr/bin/caddy /usr/bin/caddy

# Default Caddy file locations are the same as the base image
# /etc/caddy/Caddyfile
# /data and /config will be mounted by docker-compose
