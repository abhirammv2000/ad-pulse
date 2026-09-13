#!/bin/sh
# Runs from nginx's /docker-entrypoint.d before the server starts.
#
# Writes the runtime service URLs into the built bundle's config.js, so one
# image can be promoted from stage to prod without rebuilding. It must not exec
# anything — the image's own entrypoint starts nginx once these scripts finish.
set -eu

cat > /usr/share/nginx/html/config.js <<EOF
window.__ADPULSE_CONFIG__ = {
  API_BASE_URL: "${REACT_APP_API_BASE_URL:-}",
  AD_SERVER_URL: "${REACT_APP_API_AD_SERVER_URL:-}",
};
EOF
