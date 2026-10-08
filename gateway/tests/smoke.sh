#!/usr/bin/env bash
# Start a gateway image and check what the image is responsible for: the
# projects load from assets/projects, the icon library and web files are
# served, and the asset installer ran. Works with docker or podman.
#
#   gateway/tests/smoke.sh <image> [timeout seconds]
set -euo pipefail
image=$1
timeout=${2:-600}
engine=${CONTAINER_ENGINE:-$(command -v docker >/dev/null && echo docker || echo podman)}
name="smoke-$$"
export MSYS_NO_PATHCONV=1

cleanup() { "${engine}" rm -f "${name}" >/dev/null 2>&1 || true; }
trap cleanup EXIT

"${engine}" run -d --name "${name}" \
  -e ACCEPT_IGNITION_EULA=Y -e DISABLE_QUICKSTART=true -e IGNITION_EDITION=standard \
  -e GATEWAY_ADMIN_USERNAME=admin -e GATEWAY_ADMIN_PASSWORD=smoke-test \
  "${image}" -n smoke -m 768 -- \
  -Dignition.projects.dir=/usr/local/bin/ignition/assets/projects >/dev/null

get() { "${engine}" exec "${name}" curl -s -m 5 "$@"; }
deadline=$(( $(date +%s) + timeout ))
until get http://localhost:8088/StatusPing 2>/dev/null | grep -q RUNNING; do
  if [ "$(date +%s)" -ge "${deadline}" ]; then
    "${engine}" logs --tail 40 "${name}" >&2
    echo "FAIL gateway not RUNNING within ${timeout}s" >&2
    exit 1
  fi
  sleep 5
done
version=$(get http://localhost:8088/system/gwinfo | tr ';' '\n' | sed -n 's/^Version=//p')
echo "gateway ${version} running"

failures=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; failures=$((failures + 1)); fi; }
# projects start shortly after the gateway reports RUNNING (same line on 8.1 and 8.3)
for _ in $(seq 24); do
  logs=$("${engine}" logs "${name}" 2>&1)
  grep -q "Project started.*project-name=project" <<< "${logs}" && break
  sleep 5
done

check "asset installer ran" 'grep -q "assets   | .* installed" <<< "${logs}"'
check "library project loaded from the image" 'grep -q "Project started.*project-name=library" <<< "${logs}"'
check "project project loaded from the image" 'grep -q "Project started.*project-name=project" <<< "${logs}"'
code() { "${engine}" exec "${name}" curl -s -o /dev/null -w "%{http_code}" -m 5 "http://localhost:8088$1"; }
check "Perspective serves the project" '[ "$(code /data/perspective/client/project)" = 200 ]'
check "Perspective rejects an unknown project" '[ "$(code /data/perspective/client/no-such-project)" = 404 ]'
check "icon library served" 'get http://localhost:8088/data/perspective/icons/equipment | grep -q "id=\"pump\""'
check "web file served from the web root" 'get http://localhost:8088/operator-guide.html | grep -q "Operator guide"'

if [ "${failures}" -ne 0 ]; then
  grep -iE "project|icon|assets" <<< "${logs}" | tail -20 >&2
  echo "${failures} failed" >&2
  exit 1
fi
echo "all passed"
