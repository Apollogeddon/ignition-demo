#!/usr/bin/env bash
# check() evals each condition later, so the single quotes are deliberate and the
# variables they name are used
# shellcheck disable=SC2016,SC2034
# Tests for api-token.sh: the token hash and the files it writes.
set -euo pipefail
script="$(cd "$(dirname "$0")/.." && pwd)/api-token.sh"
work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT
failures=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; failures=$((failures + 1)); fi; }

# the hash matches a reference implementation, for random secrets
# shellcheck source=/dev/null
source "${script}"
python=$(command -v python3 || command -v python || true)
for _ in 1 2 3; do
  secret=$(head -c 32 /dev/urandom | base64 -w0 | tr '+/' '-_' | tr -d '=')
  if [ -n "${python}" ] && "${python}" -c 1 2>/dev/null; then
    expected=$("${python}" -c 'import base64,hashlib,sys; s=sys.argv[1]; d=base64.urlsafe_b64decode(s+"="*(-len(s)%4)); print(base64.urlsafe_b64encode(hashlib.sha256(d).digest()).decode().rstrip("="))' "${secret}")
  else
    expected=$(uv run --no-project python -c 'import base64,hashlib,sys; s=sys.argv[1]; d=base64.urlsafe_b64decode(s+"="*(-len(s)%4)); print(base64.urlsafe_b64encode(hashlib.sha256(d).digest()).decode().rstrip("="))' "${secret}")
  fi
  check "hash of a random secret matches the reference" '[ "$(hash_token "${secret}")" = "${expected}" ]'
done

home() { # home <dir> <version>: a fake install with external and core collections
  mkdir -p "$1/lib" "$1/data/config/resources/external" "$1/data/config/resources/core"
  echo "gateway.version=$2" > "$1/lib/install-info.txt"
}
run() { # run <home> <token> [VAR=value ...]; the exit status goes to <home>/rc
  local rc=0
  env IGNITION_HOME="$1" GATEWAY_API_TOKEN="$2" "${@:3}" bash "${script}" > "$1/out.txt" 2>&1 || rc=$?
  echo "${rc}" > "$1/rc"
}

h="${work}/83"; home "$h" 8.3.10; run "$h" "iac:${secret}"
tok="$h/data/config/resources/external/ignition/api-token/iac"
check "8.3 key written to the external collection" '[ -f "${tok}/config.json" ] && [ -f "${tok}/resource.json" ]'
check "8.3 key stores the hash, not the secret" 'grep -q "\"tokenHash\": \"$(hash_token "${secret}")\"" "${tok}/config.json" && ! grep -qF -- "${secret}" "${tok}/config.json"'
check "8.3 key carries the Api level and a timestamp" 'grep -q "\"name\": \"Api\"" "${tok}/config.json" && grep -q "\"timestamp\"" "${tok}/config.json"'
check "8.3 Api security level defined" 'grep -q "\"name\": \"Api\"" "$h/data/config/resources/external/ignition/security-levels/config.json"'
check "8.3 key needs a secure channel by default" 'grep -q "\"secureChannelRequired\": true" "${tok}/config.json"'

h="${work}/plain-http"; home "$h" 8.3.10; run "$h" "iac:${secret}" GATEWAY_API_TOKEN_REQUIRE_TLS=false
check "GATEWAY_API_TOKEN_REQUIRE_TLS=false takes the key over plain HTTP" 'grep -q "\"secureChannelRequired\": false" "$h/data/config/resources/external/ignition/api-token/iac/config.json"'
h="${work}/bad-tls"; home "$h" 8.3.10; run "$h" "iac:${secret}" GATEWAY_API_TOKEN_REQUIRE_TLS=yes
check "a GATEWAY_API_TOKEN_REQUIRE_TLS other than true or false installs nothing" 'grep -q "must be true or false" "$h/out.txt" && [ ! -e "$h/data/config/resources/external/ignition" ]'

for bad in "../../core/x" ".." "a b"; do
  h="${work}/name"; rm -rf "$h"; home "$h" 8.3.10; run "$h" "${bad}:${secret}"
  check "key name '${bad}' refused, nothing written" 'grep -q "may only hold" "$h/out.txt" && [ ! -e "$h/data/config/resources/external/ignition" ] && [ ! -e "$h/data/config/resources/core/x" ]'
done
h="${work}/level"; home "$h" 8.3.10; run "$h" "iac:${secret}" 'GATEWAY_API_TOKEN_LEVEL=Api", "x'
check "a level that isn't a plain name is refused" 'grep -q "may only hold" "$h/out.txt" && [ ! -e "$h/data/config/resources/external/ignition" ]'

# the trial keepalive resets an 8.3 trial with the key over plain HTTP, which a key that needs
# TLS is refused on: the start fails with the way out, rather than the trial lapsing later
h="${work}/keepalive"; home "$h" 8.3.10; run "$h" "iac:${secret}" GATEWAY_TRIAL_KEEPALIVE=true
check "keepalive with a key that needs TLS fails the start, naming the fix" '[ "$(cat "$h/rc")" != 0 ] && grep -q "GATEWAY_API_TOKEN_REQUIRE_TLS=false" "$h/out.txt"'
h="${work}/keepalive-http"; home "$h" 8.3.10; run "$h" "iac:${secret}" GATEWAY_TRIAL_KEEPALIVE=true GATEWAY_API_TOKEN_REQUIRE_TLS=false
check "keepalive with the plain-HTTP opt-out starts" '[ "$(cat "$h/rc")" = 0 ] && [ -f "$h/data/config/resources/external/ignition/api-token/iac/config.json" ]'
h="${work}/keepalive-https"; home "$h" 8.3.10; run "$h" "iac:${secret}" GATEWAY_TRIAL_KEEPALIVE=true GATEWAY_TRIAL_URL=https://gateway.example:8043
check "keepalive over an https GATEWAY_TRIAL_URL starts" '[ "$(cat "$h/rc")" = 0 ]'
h="${work}/keepalive-nokey"; home "$h" 8.3.10; run "$h" "" GATEWAY_TRIAL_KEEPALIVE=true GATEWAY_API_TOKEN_REQUIRE_TLS=false
check "an 8.3 keepalive without an API key fails the start" '[ "$(cat "$h/rc")" != 0 ] && grep -q "GATEWAY_API_TOKEN isn.t set" "$h/out.txt"'
h="${work}/keepalive-badkey"; home "$h" 8.3.10; run "$h" "no-colon" GATEWAY_TRIAL_KEEPALIVE=true GATEWAY_API_TOKEN_REQUIRE_TLS=false
check "an 8.3 keepalive with a malformed key fails the start" '[ "$(cat "$h/rc")" != 0 ] && grep -q "ERROR: .*<name>:<secret>" "$h/out.txt"'
h="${work}/keepalive-81"; home "$h" 8.1.55; run "$h" "" GATEWAY_TRIAL_KEEPALIVE=true
check "an 8.1 keepalive without the admin login fails the start" '[ "$(cat "$h/rc")" != 0 ] && grep -q "GATEWAY_ADMIN_USERNAME and GATEWAY_ADMIN_PASSWORD" "$h/out.txt"'
h="${work}/keepalive-81-admin"; home "$h" 8.1.55; run "$h" "" GATEWAY_TRIAL_KEEPALIVE=true GATEWAY_ADMIN_USERNAME=admin GATEWAY_ADMIN_PASSWORD=pw
check "an 8.1 keepalive with the admin login starts" '[ "$(cat "$h/rc")" = 0 ]'
h="${work}/no-keepalive"; home "$h" 8.3.10; run "$h" "iac:${secret}"
check "without the keepalive the default starts" '[ "$(cat "$h/rc")" = 0 ]'

# security levels someone else defined in the external collection are kept
h="${work}/levels"; home "$h" 8.3.10
levels="$h/data/config/resources/external/ignition/security-levels"
mkdir -p "${levels}"
printf '{"securityLevels": [{"children": [], "name": "Site"}, {"children": [], "name": "Api"}]}\n' > "${levels}/config.json"
run "$h" "iac:${secret}"
check "existing levels that hold the key's level are left as they are" 'grep -q "\"name\": \"Site\"" "${levels}/config.json"'
printf '{"securityLevels": [{"children": [], "name": "Site"}]}\n' > "${levels}/config.json"
run "$h" "iac:${secret}"
check "existing levels without it are kept (the level is added with Jython)" 'grep -q "\"name\": \"Site\"" "${levels}/config.json"'

# a level of the same name nested under another isn't the top-level one: Jython decides
mkdir -p "$h/lib/runtime/jre/bin"
printf '#!/bin/sh\necho "$@" >> "%s/java-args"\n' "$h" > "$h/lib/runtime/jre/bin/java"
chmod +x "$h/lib/runtime/jre/bin/java"
printf '{"securityLevels": [{"children": [{"children": [], "name": "Api"}], "name": "Site"}]}\n' > "${levels}/config.json"
run "$h" "iac:${secret}"
check "a level named only as a child is still added at the top level" 'grep -q -- "--define ${levels}/config.json Api" "$h/java-args"'

h="${work}/81"; home "$h" 8.1.55; run "$h" "iac:${secret}"
check "8.1 does nothing" '[ ! -e "$h/data/config/resources/external/ignition" ]'
h="${work}/unset"; home "$h" 8.3.10; run "$h" ""
check "no variable, nothing written" '[ ! -e "$h/data/config/resources/external/ignition" ]'
h="${work}/bad"; home "$h" 8.3.10; run "$h" "no-colon"
check "a malformed variable is reported, nothing written" 'grep -q "must be <name>:<secret>" "$h/out.txt" && [ ! -e "$h/data/config/resources/external/ignition" ]'

if [ "${failures}" -ne 0 ]; then echo "${failures} failed"; exit 1; fi
echo "all passed"
