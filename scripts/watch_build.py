#!/usr/bin/env python3
import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

DOCKER_HUB_TAGS_URL = "https://hub.docker.com/v2/repositories/library/caddy/tags"
DOCKER_REGISTRY = "https://registry-1.docker.io"
DOCKER_AUTH_URL = "https://auth.docker.io/token"
REPO_DOCKERHUB = os.environ.get("TARGET_REPO_DOCKERHUB", "melonsmasher/caddy-cloudflare-cache")
REPO_GHCR = os.environ.get("TARGET_REPO_GHCR", "ghcr.io/melonsmasher/caddy-cloudflare-cache")
DB_PATH = os.environ.get("STATE_DB", os.path.join(os.path.dirname(__file__), "state.db"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "600"))  # seconds
PLATFORMS = os.environ.get("PLATFORMS", "linux/amd64,linux/arm64")
ALWAYS_PULL = os.environ.get("ALWAYS_PULL", "1") == "1"
MAX_BUILDS_PER_RUN = int(os.environ.get("MAX_BUILDS_PER_RUN", "0"))  # 0 => no cap
BUILD_DELAY_SEC = int(os.environ.get("BUILD_DELAY_SEC", "0"))
# Mirror only 2.x tags (optionally -alpine). Examples matched: 2, 2.7, 2.7.6, 2-alpine, 2.7-alpine, 2.7.6-alpine
# Explicitly exclude builder images and any windowsservercore variants.
TAG_INCLUDE_REGEX = re.compile(r"^2(?:\.?\d+(?:\.\d+)?)?(?:-alpine)?$")
TAG_EXCLUDE_REGEX = re.compile(r"(?:.*-builder$)|(?:.*-windowsservercore.*)")

# Minimum Caddy version supported by the plugin set (e.g., cloudflare dns plugin requires >= v2.7.5)
MIN_CADDY_VERSION = (2, 7, 5)
ACCEPT_HEADERS = ", ".join([
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
])


def log(msg: str):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{now}] {msg}", flush=True)


def db_init(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            tag TEXT PRIMARY KEY,
            digest TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_built_at TEXT
        )
        """
    )
    conn.commit()


def get_docker_auth_token(repo: str = "library/caddy") -> str:
    # Request a bearer token to pull from registry-1.docker.io
    r = requests.get(
        DOCKER_AUTH_URL,
        params={
            "service": "registry.docker.io",
            "scope": f"repository:{repo}:pull",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["token"]


def get_manifest_digest(tag: str, repo: str = "library/caddy") -> Optional[str]:
    token = get_docker_auth_token(repo)
    headers = {
        "Accept": ACCEPT_HEADERS,
        "Authorization": f"Bearer {token}",
    }
    # Use HEAD first; fall back to GET if needed
    url = f"{DOCKER_REGISTRY}/v2/{repo}/manifests/{tag}"
    r = requests.head(url, headers=headers, timeout=30)
    if r.status_code == 404:
        return None
    if r.ok:
        digest = r.headers.get("Docker-Content-Digest")
        if digest:
            return digest
    # Fallback: GET
    r = requests.get(url, headers=headers, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    digest = r.headers.get("Docker-Content-Digest")
    if digest:
        return digest
    # Some registries may not echo header; compute a hash would require canonicalization; skip
    return None


def list_hub_tags() -> List[str]:
    tags: List[str] = []
    url = DOCKER_HUB_TAGS_URL
    params = {"page_size": 100}
    while url:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        for item in data.get("results", []):
            name = item.get("name")
            if not name:
                continue
            tags.append(name)
        url = data.get("next")
        params = None  # 'next' already includes the query params
    return tags


def parse_caddy_version(tag: str) -> Optional[Tuple[int, int, int]]:
    """Parse caddy tag like '2', '2.7', '2.7.6', optionally with '-alpine'.
    Returns a (major, minor, patch) tuple or None if not a 2.x tag.
    """
    # Strip variant suffix (e.g., '-alpine')
    base = tag.split("-", 1)[0]
    parts = base.split(".")
    # Must start with major '2'
    try:
        major = int(parts[0])
    except (ValueError, IndexError):
        return None
    if major != 2:
        return None
    # Fill missing minor/patch with zeros
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    return (major, minor, patch)


def filter_tags(all_tags: List[str]) -> List[str]:
    filtered = []
    for t in all_tags:
        if TAG_EXCLUDE_REGEX.match(t):
            continue
        if TAG_INCLUDE_REGEX.match(t):
            v = parse_caddy_version(t)
            if not v:
                continue
            if v < MIN_CADDY_VERSION:
                # below supported baseline for our plugin set
                continue
            filtered.append(t)
    # Unique and sorted for stability
    return sorted(set(filtered))


def decide_builder_tag(base_tag: str) -> str:
    # We standardized on the official builder image which includes xcaddy.
    # Returning a constant avoids extra registry lookups and rate limit consumption.
    return "builder"


def run(cmd: List[str]) -> int:
    log("RUN: " + " ".join(cmd))
    proc = subprocess.Popen(cmd)
    return proc.wait()


def build_and_push(tag: str) -> bool:
    builder_tag = decide_builder_tag(tag)
    log(f"Building for tag={tag}, builder_tag={builder_tag}")

    # Compose docker buildx command
    dockerfile_path = os.path.join(os.path.dirname(__file__), "Dockerfile")
    docker_context = os.path.dirname(dockerfile_path)
    cmd: List[str] = ["docker", "buildx", "build"]
    # Options block; ensure flag/value adjacency is preserved
    opts: List[str] = []
    if ALWAYS_PULL:
        opts += ["--pull"]
    opts += [
        "--platform", PLATFORMS,
        "--provenance=false",
        "-t", f"{REPO_DOCKERHUB}:{tag}",
        "-t", f"{REPO_GHCR}:{tag}",
        "--build-arg", f"CADDY_TAG={tag}",
        "-f", dockerfile_path,
        "--push",
        docker_context,
    ]
    cmd += opts
    code = run(cmd)
    if code != 0:
        log(f"Build failed for {tag} (exit {code})")
        return False
    log(f"Build succeeded for {tag}")
    return True


def sync_once(conn: sqlite3.Connection, only_tag: Optional[str] = None) -> None:
    all_tags = list_hub_tags()
    targets = filter_tags(all_tags)
    if only_tag:
        targets = [t for t in targets if t == only_tag]
    log(f"Found {len(targets)} 2.x tags to mirror (>= {'.'.join(map(str, MIN_CADDY_VERSION))}, incl. alpine)")
    cur = conn.cursor()
    built = 0
    for tag in targets:
        # Defensive guard: never build Windows Server Core variants even if they slip past filters
        if "windowsservercore" in tag:
            log(f"Skip {tag}: windowsservercore explicitly excluded")
            continue
        digest = get_manifest_digest(tag)
        if not digest:
            log(f"Skip {tag}: no digest found")
            continue
        row = cur.execute("SELECT digest FROM tags WHERE tag= ?", (tag,)).fetchone()
        if row and row[0] == digest:
            # No change
            continue
        # Change detected or new tag
        log(f"Change detected for {tag}: {row[0] if row else '∅'} -> {digest}")
        ok = build_and_push(tag)
        now = datetime.now(timezone.utc).isoformat()
        if ok:
            cur.execute(
                "INSERT INTO tags(tag,digest,updated_at,last_built_at) VALUES(?,?,?,?)"
                " ON CONFLICT(tag) DO UPDATE SET digest=excluded.digest, updated_at=excluded.updated_at, last_built_at=excluded.last_built_at",
                (tag, digest, now, now),
            )
            conn.commit()
        else:
            # Record updated_at even if build failed, but don't update digest to avoid suppressing retries
            cur.execute(
                "INSERT INTO tags(tag,digest,updated_at) VALUES(?,?,?)"
                " ON CONFLICT(tag) DO UPDATE SET updated_at=excluded.updated_at",
                (tag, row[0] if row else "", now),
            )
            conn.commit()
        built += 1
        if BUILD_DELAY_SEC > 0:
            time.sleep(BUILD_DELAY_SEC)
        if MAX_BUILDS_PER_RUN and built >= MAX_BUILDS_PER_RUN:
            log(f"Build cap reached for this run (MAX_BUILDS_PER_RUN={MAX_BUILDS_PER_RUN})")
            break


def main():
    parser = argparse.ArgumentParser(description="Mirror upstream caddy 2.x (+alpine) tags with custom build")
    parser.add_argument("--once", action="store_true", help="Run a single scan/build cycle and exit")
    parser.add_argument("--list-only", action="store_true", help="List filtered tags and exit (no builds)")
    parser.add_argument("--tag", help="Build only this specific tag", default=None)
    args = parser.parse_args()

    # Basic env checks
    if not shutil_which("docker"):
        log("ERROR: docker not found in PATH")
        sys.exit(1)
    if not shutil_which("docker buildx") and not shutil_which("buildx"):
        # We cannot detect buildx via which easily; attempt a version check
        try:
            subprocess.run(["docker", "buildx", "version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            log("ERROR: docker buildx not available. Install/enable buildx and create a builder.")
            sys.exit(1)

    # Optional Docker Hub login to raise rate limits
    dockerhub_user = os.environ.get("DOCKERHUB_USERNAME")
    dockerhub_pass = os.environ.get("DOCKERHUB_PASSWORD") or os.environ.get("DOCKERHUB_TOKEN")
    if dockerhub_user and dockerhub_pass:
        try:
            log("Logging into Docker Hub (username from DOCKERHUB_USERNAME)")
            proc = subprocess.run(
                ["docker", "login", "-u", dockerhub_user, "--password-stdin"],
                input=dockerhub_pass.encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if proc.returncode != 0:
                log(f"WARNING: docker login failed: {proc.stderr.decode().strip()}")
            else:
                log("Docker login succeeded")
        except Exception as e:
            log(f"WARNING: docker login exception: {e}")

    conn = sqlite3.connect(DB_PATH)
    db_init(conn)

    if args.list_only:
        all_tags = list_hub_tags()
        targets = filter_tags(all_tags)
        for t in targets:
            if "windowsservercore" in t:
                log(f"(filtered but would skip) {t}")
            else:
                log(f"target: {t}")
        return

    if args.once:
        sync_once(conn, only_tag=args.tag)
        return

    log(f"Starting watcher loop; polling every {POLL_INTERVAL}s")
    while True:
        try:
            sync_once(conn, only_tag=args.tag)
        except Exception as e:
            log(f"ERROR during sync: {e}")
        time.sleep(POLL_INTERVAL)


def shutil_which(cmd: str) -> Optional[str]:
    from shutil import which
    return which(cmd)


if __name__ == "__main__":
    main()
