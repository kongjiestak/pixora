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

${CC:-cc} -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g -O1 \
  -I"$root/main" "$root/host-tests/test_setup_address.c" -o "$tmp/setup-address-test"
"$tmp/setup-address-test"

${CC:-cc} -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g -O1 \
  -I"$root/main" "$root/host-tests/test_setup_request.c" -o "$tmp/setup-request-test"
"$tmp/setup-request-test"

${CC:-cc} -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g -O1 \
  -I"$root/main" "$root/host-tests/test_wifi_credentials.c" -o "$tmp/wifi-credentials-test"
"$tmp/wifi-credentials-test"

mbed="$IDF_PATH/components/mbedtls/mbedtls"
${CC:-cc} -std=c11 -D_POSIX_C_SOURCE=200809L -DMBEDTLS_CONFIG_FILE='"usb_mbedtls_config.h"' \
  -Wall -Wextra -Werror -fsanitize=address,undefined -g -O1 \
  -I"$root/main" -I"$root/host-tests" -I"$mbed/include" -I"$mbed/library" -I"$IDF_PATH/components/json/cJSON" \
  "$root/host-tests/test_usb_protocol.c" "$root/main/usb_protocol.c" "$root/main/quota.c" \
  "$IDF_PATH/components/json/cJSON/cJSON.c" "$mbed/library/sha256.c" "$mbed/library/platform_util.c" -lm -o "$tmp/usb-protocol-test"
"$tmp/usb-protocol-test"

${CC:-cc} -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror -fsanitize=address,undefined -g -O1 \
  -I"$root/main" -I"$IDF_PATH/components/json/cJSON" \
  "$root/host-tests/test_weather.c" "$root/main/quota.c" "$IDF_PATH/components/json/cJSON/cJSON.c" -lm -o "$tmp/weather-test"
"$tmp/weather-test"
