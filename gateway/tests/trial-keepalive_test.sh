#!/usr/bin/env bash
# check() evals each condition later, so the single quotes are deliberate and the
# variables they name are used; the curl and sleep stubs are called by the script
# shellcheck disable=SC2016,SC2034,SC2329
# Tests for trial-keepalive.sh: the 8.1 sign-in JSON and the backoff after failed resets.
set -uo pipefail
script="$(cd "$(dirname "$0")/.." && pwd)/trial-keepalive.sh"
work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT
failures=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; failures=$((failures + 1)); fi; }
python=$(command -v python3 || command -v python || true)
# valid_json <file> <key> <value>: the file is JSON whose <key> is exactly <value>
valid_json() {
  if [ -n "${python}" ] && "${python}" -c 1 2>/dev/null; then
    "${python}" -c 'import json,sys; sys.exit(json.load(open(sys.argv[1]))[sys.argv[2]] != sys.argv[3])' "$@"
  else
    uv run --no-project python -c 'import json,sys; sys.exit(json.load(open(sys.argv[1]))[sys.argv[2]] != sys.argv[3])' "$@"
  fi
}

# shellcheck source=/dev/null
source "${script}"

# the 8.1 sign-in, against a curl that records the username/password challenge's body
curl() {
  local body="" prev="" a
  for a in "$@"; do [ "${prev}" = -d ] && body=${a}; prev=${a}; done
  case "$*" in *submit-username-password-challenge*) printf '%s' "${body}" > "${work}/signin.json" ;; esac
  case "$*" in *-w*) printf '' ;; *) printf '{"token":"t"}' ;; esac
}
for password in 'pa"ss\word' $'tab\there' 'plain' 'ünïcode "quoted"'; do
  rm -f "${work}/signin.json"
  GATEWAY_ADMIN_USERNAME='ad"min' GATEWAY_ADMIN_PASSWORD="${password}" reset_81 > /dev/null 2>&1
  check "the sign-in carries password ${password@Q} as valid JSON" \
    '[ -s "${work}/signin.json" ] && valid_json "${work}/signin.json" password "${password}" && valid_json "${work}/signin.json" username "ad\"min"'
done
unset -f curl

# a reset that keeps failing backs off, doubling to max_backoff, rather than signing in
# every 30 s for as long as the gateway runs
backoff() {
  (
    sleeps=0
    curl() { case "$*" in *-X\ POST*) return 22 ;; *) printf '{"trialSecondsLeft":0,"expired":true}' ;; esac; }
    sleep() { echo "$1" >> "${work}/sleeps"; sleeps=$((sleeps + 1)); [ "${sleeps}" -lt 9 ] || exit 0; }
    GATEWAY_TRIAL_KEEPALIVE=true GATEWAY_API_TOKEN=k version=8.3.10 main > /dev/null
  )
}
rm -f "${work}/sleeps"; backoff
check "failed resets back off from 30 s, doubling to an hour" \
  '[ "$(tr "\n" " " < "${work}/sleeps")" = "30 60 120 240 480 960 1920 3600 3600 " ]'

# a trial seen running again, reset some other way, starts the next failure's backoff at
# 30 s rather than where the earlier failures left it
rm -f "${work}/sleeps" "${work}/polls"
(
  sleeps=0
  curl() {
    case "$*" in *-X\ POST*) return 22 ;; esac
    echo poll >> "${work}/polls"
    case "$(wc -l < "${work}/polls")" in
      *3) printf '{"trialSecondsLeft":0,"expired":false}' ;;
      *) printf '{"trialSecondsLeft":0,"expired":true}' ;;
    esac
  }
  sleep() { echo "$1" >> "${work}/sleeps"; sleeps=$((sleeps + 1)); [ "${sleeps}" -lt 4 ] || exit 0; }
  GATEWAY_TRIAL_KEEPALIVE=true GATEWAY_API_TOKEN=k version=8.3.10 main > /dev/null
)
check "a trial running again resets the backoff to 30 s" '[ "$(tr "\n" " " < "${work}/sleeps")" = "30 60 3 30 " ]'

# the seconds left come from the gateway: anything but digits sleeps the shortest time,
# and is never evaluated
for sent in '120' '120.5' '"a[$(touch ${work}/pwned)]"' '-5' '99999999999999999999'; do
  rm -f "${work}/sleeps"
  # shellcheck disable=SC2329
  curl() { printf '{"trialSecondsLeft":%s,"expired":false}' "${sent}"; }
  ( sleep() { echo "$1" >> "${work}/sleeps"; exit 0; }; GATEWAY_TRIAL_KEEPALIVE=true version=8.3.10 main > /dev/null 2>&1 )
  case "${sent}" in 120*) want=123 ;; 9999*) want=3600 ;; *) want=3 ;; esac
  check "trialSecondsLeft ${sent} sleeps ${want} s" '[ "$(cat "${work}/sleeps" 2>/dev/null)" = "${want}" ] && [ ! -e "${work}/pwned" ]'
done
unset -f curl

if [ "${failures}" -ne 0 ]; then echo "${failures} failed"; exit 1; fi
echo "all passed"
