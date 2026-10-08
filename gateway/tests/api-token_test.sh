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
run() { IGNITION_HOME="$1" GATEWAY_API_TOKEN="$2" bash "${script}" > "$1/out.txt" 2>&1 || true; }

h="${work}/83"; home "$h" 8.3.10; run "$h" "iac:${secret}"
tok="$h/data/config/resources/external/ignition/api-token/iac"
check "8.3 key written to the external collection" '[ -f "${tok}/config.json" ] && [ -f "${tok}/resource.json" ]'
check "8.3 key stores the hash, not the secret" 'grep -q "\"tokenHash\": \"$(hash_token "${secret}")\"" "${tok}/config.json" && ! grep -q "${secret}" "${tok}/config.json"'
check "8.3 key carries the Api level and a timestamp" 'grep -q "\"name\": \"Api\"" "${tok}/config.json" && grep -q "\"timestamp\"" "${tok}/config.json"'
check "8.3 Api security level defined" 'grep -q "\"name\": \"Api\"" "$h/data/config/resources/external/ignition/security-levels/config.json"'

h="${work}/81"; home "$h" 8.1.55; run "$h" "iac:${secret}"
check "8.1 does nothing" '[ ! -e "$h/data/config/resources/external/ignition" ]'
h="${work}/unset"; home "$h" 8.3.10; run "$h" ""
check "no variable, nothing written" '[ ! -e "$h/data/config/resources/external/ignition" ]'
h="${work}/bad"; home "$h" 8.3.10; run "$h" "no-colon"
check "a malformed variable is reported, nothing written" 'grep -q "must be <name>:<secret>" "$h/out.txt" && [ ! -e "$h/data/config/resources/external/ignition" ]'

if [ "${failures}" -ne 0 ]; then echo "${failures} failed"; exit 1; fi
echo "all passed"
