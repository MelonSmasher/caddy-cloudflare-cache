# Build Caddy with Cloudflare DNS and Souin using xcaddy
# Accept upstream tags at build time
ARG CADDY_TAG=latest
ARG CADDY_BUILDER_TAG=builder

FROM caddy:${CADDY_BUILDER_TAG} AS builder
ARG CADDY_TAG
ARG SOUIN_VERSION
ARG STORAGES_VERSION
ARG CLOUDFLARE_DNS_VERSION
ARG CFIP_VERSION

# Build Caddy with required plugins
RUN set -eux; \
    # Ensure xcaddy is present (older builder tags may not include it)
    if ! command -v xcaddy >/dev/null 2>&1; then \
      export GOBIN=/usr/bin; \
      # Prefer module-aware install; fallback to GOPATH-mode for very old Go toolchains \
      (GO111MODULE=on go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest \
        || go get -u github.com/caddyserver/xcaddy/cmd/xcaddy); \
    fi; \
    # Derive caddy version from CADDY_TAG (strip -alpine, prefix with v); "2" becomes "v2"
    VER="$CADDY_TAG"; \
    VER="${VER%-alpine}"; \
    [ -n "$VER" ] && VER="v${VER}"; \
    # Build caddy with required plugins
    xcaddy build "$VER" \
      --with github.com/caddy-dns/cloudflare${CLOUDFLARE_DNS_VERSION:+@${CLOUDFLARE_DNS_VERSION}} \
      --with github.com/WeidiDeng/caddy-cloudflare-ip${CFIP_VERSION:+@${CFIP_VERSION}} \
      --with github.com/darkweak/souin/plugins/caddy${SOUIN_VERSION:+@${SOUIN_VERSION}} \
      --with github.com/darkweak/storages/badger/caddy${STORAGES_VERSION:+@${STORAGES_VERSION}} \
      --with github.com/darkweak/storages/redis/caddy${STORAGES_VERSION:+@${STORAGES_VERSION}} \
      --with github.com/darkweak/storages/etcd/caddy${STORAGES_VERSION:+@${STORAGES_VERSION}} \
      --with github.com/darkweak/storages/nuts/caddy${STORAGES_VERSION:+@${STORAGES_VERSION}} \
      --with github.com/darkweak/storages/olric/caddy${STORAGES_VERSION:+@${STORAGES_VERSION}} \
      --with github.com/darkweak/storages/nats/caddy${STORAGES_VERSION:+@${STORAGES_VERSION}} \
      --with github.com/darkweak/storages/otter/caddy${STORAGES_VERSION:+@${STORAGES_VERSION}} \
      --with github.com/darkweak/storages/simplefs/caddy${STORAGES_VERSION:+@${STORAGES_VERSION}}

# Final image
FROM caddy:${CADDY_TAG}
COPY --from=builder /usr/bin/caddy /usr/bin/caddy