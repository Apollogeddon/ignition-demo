#!/usr/bin/env bash
# check() evals each condition later, so the single quotes are deliberate
# shellcheck disable=SC2016
# Start a gateway image and check what the image is responsible for: the
# projects load from assets/projects, the icon library and web files are
# served, and the asset installer ran. On 8.3 it also starts two gateways with
# an API key, and checks the key is refused over plain HTTP, taken behind a
# TLS proxy (X-Forwarded-Proto: https), and taken over plain HTTP with
# GATEWAY_API_TOKEN_REQUIRE_TLS=false. Works with docker or podman.
#
#   gateway/tests/smoke.sh <image> [timeout seconds]
set -euo pipefail
image=$1
timeout=${2:-600}
engine=${CONTAINER_ENGINE:-$(command -v docker >/dev/null && echo docker || echo podman)}
name="smoke-$$"
export MSYS_NO_PATHCONV=1

cleanup() { "${engine}" rm -f "${name}" "${name}-tls" "${name}-http" >/dev/null 2>&1 || true; }
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
# projects start, and their startup event runs, shortly after the gateway
# reports RUNNING (the same log lines on 8.1 and 8.3)
for _ in $(seq 24); do
  logs=$("${engine}" logs "${name}" 2>&1)
  grep -q "UDT definitions imported" <<< "${logs}" && break
  sleep 5
done

check "asset installer ran" 'grep -q "assets   | .* installed" <<< "${logs}"'
check "library project loaded from the image" 'grep -q "Project started.*project-name=library" <<< "${logs}"'
check "project project loaded from the image" 'grep -q "Project started.*project-name=project" <<< "${logs}"'
code() { "${engine}" exec "${name}" curl -s -o /dev/null -w "%{http_code}" -m 5 "http://localhost:8088$1"; }
check "Perspective serves the project" '[ "$(code /data/perspective/client/project)" = 200 ]'
check "Perspective rejects an unknown project" '[ "$(code /data/perspective/client/no-such-project)" = 404 ]'
# the startup event (8.3 startup/onStartup.py, 8.1 the generated data.bin)
check "startup event imported the UDTs exactly once" '[ "$(grep -c "UDT definitions imported" <<< "${logs}")" = 1 ]'
check "icon library served" 'get http://localhost:8088/data/perspective/icons/equipment | grep -q "id=\"pump\""'
check "web file served from the web root" 'get http://localhost:8088/operator-guide.html | grep -q "Operator guide"'

if [[ ${version} == 8.3.* ]]; then
  key="smoke:$(head -c 32 /dev/urandom | base64 -w0 | tr '+/' '-_' | tr -d '=')"
  # start_keyed <container> <GATEWAY_API_TOKEN_REQUIRE_TLS>: a gateway with the key, trusting
  # forwarded headers as the cluster's does
  start_keyed() {
    "${engine}" run -d --name "$1" \
      -e ACCEPT_IGNITION_EULA=Y -e DISABLE_QUICKSTART=true -e IGNITION_EDITION=standard \
      -e GATEWAY_ADMIN_USERNAME=admin -e GATEWAY_ADMIN_PASSWORD=smoke-test \
      -e GATEWAY_API_TOKEN="${key}" -e GATEWAY_API_TOKEN_REQUIRE_TLS="$2" \
      "${image}" -n "$1" -m 768 -- gateway.useProxyForwardedHeader=true >/dev/null
  }
  # api <container> [curl args]: the status of a keyed API read over plain HTTP
  api() {
    local c=$1
    shift
    "${engine}" exec "${c}" curl -s -o /dev/null -w "%{http_code}" -m 5 -H "X-Ignition-API-Token: ${key}" "$@" \
      http://localhost:8088/data/api/v1/resources/singleton/ignition/gateway-network-settings 2>/dev/null
  }
  # accepted <container> [curl args]: wait, through commissioning and the restart that
  # grants the key, until the read succeeds
  accepted() {
    local end=$(( $(date +%s) + timeout ))
    until [ "$(api "$@")" = 200 ]; do
      [ "$(date +%s)" -lt "${end}" ] || return 1
      sleep 5
    done
  }
  start_keyed "${name}-tls" true
  start_keyed "${name}-http" false
  check "the API key is taken behind a TLS proxy (X-Forwarded-Proto: https)" 'accepted "${name}-tls" -H "X-Forwarded-Proto: https"'
  check "the API key is refused over plain HTTP by default" '[ "$(api "${name}-tls")" != 200 ]'
  check "GATEWAY_API_TOKEN_REQUIRE_TLS=false takes the key over plain HTTP" 'accepted "${name}-http"'
fi

if [ "${failures}" -ne 0 ]; then
  [[ ${version} != 8.3.* ]] || "${engine}" logs --tail 40 "${name}-tls" >&2
  grep -iE "project|icon|assets" <<< "${logs}" | tail -20 >&2
  echo "${failures} failed" >&2
  exit 1
fi
echo "all passed"
