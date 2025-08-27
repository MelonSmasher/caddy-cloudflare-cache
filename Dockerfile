# Build Caddy with Cloudflare DNS and Souin using xcaddy
FROM caddy:builder AS builder

# Build Caddy with required plugins
RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/darkweak/souin/plugins/caddy \
    --with github.com/darkweak/storages/badger/caddy \
    --with github.com/darkweak/storages/redis/caddy \
    --with github.com/darkweak/storages/etcd/caddy \
    --with github.com/darkweak/storages/nuts/caddy \
    --with github.com/darkweak/storages/olric/caddy \
    --with github.com/darkweak/storages/nats/caddy \
    --with github.com/darkweak/storages/otter/caddy \
    --with github.com/darkweak/storages/simplefs/caddy

# Final image
FROM caddy:latest
COPY --from=builder /usr/bin/caddy /usr/bin/caddy

# Default Caddy file locations are the same as the base image
# /etc/caddy/Caddyfile
# /data and /config will be mounted by docker-compose
