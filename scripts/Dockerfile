# Build Caddy with Cloudflare DNS and Souin using xcaddy
# Accept upstream tags at build time
ARG CADDY_TAG=latest
FROM caddy:builder AS builder
ARG CADDY_TAG

# Build Caddy with required plugins
RUN set -eux; \
    # Derive caddy version from CADDY_TAG (strip -alpine, prefix with v); "2" becomes "v2"
    VER="${CADDY_TAG:-}"; \
    VER="${VER%-alpine}"; \
    case "$VER" in v*) : ;; "") : ;; *) VER="v${VER}" ;; esac; \
    # Build caddy with required plugins (xcaddy is present in caddy:builder)
    xcaddy build ${VER:+"$VER"} --output /usr/bin/caddy \
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