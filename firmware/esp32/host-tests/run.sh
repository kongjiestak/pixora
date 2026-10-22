#!/bin/sh
set -eu
: "${IDF_PATH:?Set IDF_PATH to ESP-IDF v5.5.5}"
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
${CC:-cc} -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror -fsanitize=address,undefined -g -O1 \
  -I"$root/main" -I"$IDF_PATH/components/json/cJSON" \
  "$root/host-tests/test_quota.c" "$root/main/quota.c" "$IDF_PATH/components/json/cJSON/cJSON.c" -lm -o "$tmp/quota-test"
"$tmp/quota-test"
