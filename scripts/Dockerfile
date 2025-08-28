# Build Caddy with Cloudflare DNS and Souin using xcaddy
# Accept upstream tags at build time
ARG CADDY_TAG=latest
ARG CADDY_BUILDER_TAG=builder

FROM caddy:${CADDY_BUILDER_TAG} AS builder

# Build Caddy with required plugins
RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/WeidiDeng/caddy-cloudflare-ip \
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
FROM caddy:${CADDY_TAG}
COPY --from=builder /usr/bin/caddy /usr/bin/caddy