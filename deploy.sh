#!/usr/bin/env bash
#
# Quick deploy — sync code to the Pi and restart services.
# Run from your dev machine (not the Pi).
# Usage: ./deploy.sh [hostname]

set -euo pipefail

HOST="${1:-spotifoni.local}"
REMOTE_DIR="/opt/spotifoni"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

info() { printf '\033[1;33m=> %s\033[0m\n' "$*"; }

info "Syncing gpio-daemon to ${HOST}"
rsync -avz --delete \
    "${REPO_DIR}/gpio-daemon/" \
    "pi@${HOST}:${REMOTE_DIR}/gpio-daemon/" \
    --rsync-path="sudo rsync"

info "Syncing web app to ${HOST}"
rsync -avz --delete \
    "${REPO_DIR}/web/" \
    "pi@${HOST}:${REMOTE_DIR}/web/" \
    --rsync-path="sudo rsync"

info "Syncing config to ${HOST}"
rsync -avz --ignore-existing \
    "${REPO_DIR}/config/" \
    "pi@${HOST}:${REMOTE_DIR}/config/" \
    --rsync-path="sudo rsync"

info "Restarting services"
ssh "pi@${HOST}" "sudo systemctl restart spotifoni-controls spotifoni-web"

info "Deployed to ${HOST}"
