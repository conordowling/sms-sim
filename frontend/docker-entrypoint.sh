#!/bin/sh
set -e

REFRESH_INTERVAL_SECONDS="${REFRESH_INTERVAL_SECONDS:-5}"

cat > /usr/share/nginx/html/config.js <<CONFIG
window.APP_CONFIG = {
  refreshIntervalSeconds: ${REFRESH_INTERVAL_SECONDS},
};
CONFIG

exec "$@"
