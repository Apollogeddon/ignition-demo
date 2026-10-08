#!/usr/bin/env bash
# The gateway image's entrypoint: install the image's assets into the data
# volume, then hand over to the official Ignition entrypoint with the same
# arguments.
set -euo pipefail
/usr/local/bin/ignition/assets/install-assets.sh
exec docker-entrypoint.sh "$@"
