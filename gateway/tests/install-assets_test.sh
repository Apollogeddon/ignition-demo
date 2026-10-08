#!/usr/bin/env bash
# Tests for install-assets.sh against fake Ignition homes for 8.1 and 8.3.
set -euo pipefail
script="$(cd "$(dirname "$0")/.." && pwd)/install-assets.sh"
work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT
failures=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; failures=$((failures + 1)); fi; }

home() { # home <dir> <version>: a fake install with a seeded data volume and two assets
  mkdir -p "$1/lib" "$1/data/db" "$1/assets/icons" "$1/assets/certs"
  echo "gateway.version=$2" > "$1/lib/install-info.txt"
  echo '<svg id="a"/>' > "$1/assets/icons/equipment.svg"
  echo cert > "$1/assets/certs/site-ca.crt"
}
run() { IGNITION_HOME="$1" bash "${script}" > "$1/out.txt"; }

# 8.1: icon file in the Perspective module folder, certificate in supplemental
h="${work}/81"; home "$h" 8.1.55; run "$h"
icons81="$h/data/modules/com.inductiveautomation.perspective/icons"
check "8.1 icon library installed" '[ -f "${icons81}/equipment.svg" ]'
check "8.1 certificate installed" '[ -f "$h/data/certificates/supplemental/site-ca.crt" ]'
check "8.1 nothing in the 8.3 location" '[ ! -e "$h/data/config/resources/external" ]'

# an asset dropped from the image is removed; a file someone else put there is not
rm "$h/assets/icons/equipment.svg"; echo other > "${icons81}/hand-made.svg"; run "$h"
check "8.1 dropped icon library removed" '[ ! -e "${icons81}/equipment.svg" ]'
check "8.1 unmanaged icon library kept" '[ -f "${icons81}/hand-made.svg" ]'
check "8.1 removal reported" 'grep -q "removed 1" "$h/out.txt"'

# 8.3: an icon library resource in the external collection
h="${work}/83"; home "$h" 8.3.10; run "$h"
lib="$h/data/config/resources/external/com.inductiveautomation.perspective/icons/equipment"
check "8.3 library svg installed" '[ -f "${lib}/library.svg" ]'
check "8.3 library config names the svg" 'grep -q "\"svgFileName\": \"library.svg\"" "${lib}/config.json"'
check "8.3 resource lists both files" 'grep -q "config.json" "${lib}/resource.json" && grep -q "library.svg" "${lib}/resource.json"'
check "8.3 certificate installed" '[ -f "$h/data/certificates/supplemental/site-ca.crt" ]'
check "8.3 nothing in the 8.1 location" '[ ! -e "$h/data/modules" ]'

# running again changes nothing and removes nothing
before=$(find "$h/data" -type f -exec md5sum {} + | sort); run "$h"; after=$(find "$h/data" -type f -exec md5sum {} + | sort)
check "8.3 second run is idempotent" '[ "${before}" = "${after}" ]'
check "8.3 second run removes nothing" 'grep -q "installed 2 assets, removed 0" "$h/out.txt"'

rm "$h/assets/icons/equipment.svg"; run "$h"
check "8.3 dropped icon library removed" '[ ! -e "${lib}" ]'

# a manifest entry outside the managed folders is never removed
echo "$h/data/db/config.idb" >> "$h/data/.image-assets"; touch "$h/data/db/config.idb"; run "$h"
check "paths outside managed folders are never removed" '[ -f "$h/data/db/config.idb" ]'

# safety: an unseeded volume or an unknown version installs nothing
h="${work}/empty"; home "$h" 8.3.10; rm -rf "$h/data"/*; run "$h"
check "empty data volume skipped" 'grep -q "data volume is empty" "$h/out.txt" && [ -z "$(ls -A "$h/data")" ]'
h="${work}/unknown"; home "$h" 7.9.21; run "$h"
check "unknown version skipped" 'grep -q "unknown Ignition version" "$h/out.txt" && [ ! -e "$h/data/certificates" ]'

[ "${failures}" -eq 0 ] && echo "all passed" || { echo "${failures} failed"; exit 1; }
