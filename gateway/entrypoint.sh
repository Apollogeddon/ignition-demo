#!/usr/bin/env bash
# The gateway image's entrypoint: install the image's assets into the data
# volume and (8.3, when GATEWAY_API_TOKEN is set) the API key, start the
# trial keepalive when asked for, then hand over
# to the official Ignition entrypoint with the same arguments.
set -euo pipefail
/usr/local/bin/ignition/assets/install-assets.sh
/usr/local/bin/ignition/assets/api-token.sh
# demo and trial environments only (GATEWAY_TRIAL_KEEPALIVE=true)
/usr/local/bin/ignition/assets/trial-keepalive.sh &
exec docker-entrypoint.sh "$@"
