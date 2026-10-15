#!/bin/zsh
set -eu
# Replace both absolute paths before use. Config must be owned by you, mode 0600.
set -a
source /ABSOLUTE/PRIVATE/PATH/pixora-collector.env
set +a
exec /ABSOLUTE/REPO/.venv/bin/pixora-collect --plugin codex
# If using HTTP over an encrypted private VPN, explicitly append --allow-private-http.
