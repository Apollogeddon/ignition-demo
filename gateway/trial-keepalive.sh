#!/usr/bin/env bash
# Keep an unlicensed gateway's two-hour trial running, for demo and trial
# environments only (GATEWAY_TRIAL_KEEPALIVE=true; never on a licensed site).
# entrypoint.sh starts it in the background of each gateway container, so
# every gateway of a redundant pair, each with its own trial clock, is covered.
#
# It reads the trial state, sleeps until just after it expires (Ignition only
# accepts a reset once the trial has expired), resets it, and repeats: one
# check per trial period, not a poll.
#   8.3  GET /data/api/v1/trial, then POST it with the API key
#        (GATEWAY_API_TOKEN, see api-token.sh)
#   8.1  GET /data/status/trial, then sign in as the gateway admin
#        (GATEWAY_ADMIN_USERNAME / GATEWAY_ADMIN_PASSWORD) and PUT it; the
#        sign-in is the gateway's OIDC flow, as its own pages run it
set -uo pipefail

home="${IGNITION_HOME:-/usr/local/bin/ignition}"
base="${GATEWAY_TRIAL_URL:-http://localhost:8088}"
buffer=3
retry=30
# a failing reset is retried after retry seconds, doubling up to this, so a wrong
# password doesn't sign in every 30 s for as long as the gateway runs
max_backoff=3600

log() { echo "trial    | $(date '+%Y/%m/%d %H:%M:%S') | $*"; }
field() { sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\{0,1\}\([^,\"}]*\).*/\1/p" | head -1; }
query() { sed -n "s/.*[?&]$2=\([^&]*\).*/\1/p" <<< "$1"; }

# json_string <value>: the value as a JSON string, so a password holding " or \ (or a
# control character) can't break the sign-in request, without needing jq in the image.
json_string() {
  local s=$1 out="" c code i
  for ((i = 0; i < ${#s}; i++)); do
    c=${s:i:1}
    case "${c}" in
      '"') out+='\"' ;;
      "\\") out+="\\\\" ;;
      *)
        printf -v code '%d' "'${c}"
        if [ "${code}" -ge 0 ] && [ "${code}" -lt 32 ]; then printf -v c '\\u%04x' "${code}"; fi
        out+=${c}
        ;;
    esac
  done
  printf '"%s"' "${out}"
}

version=$(sed -n 's/^gateway\.version=//p' "${home}/lib/install-info.txt" 2>/dev/null || true)
case "${version}" in
  8.1.*) status_path=/data/status/trial; left_field=remainingSeconds ;;
  *) status_path=/data/api/v1/trial; left_field=trialSecondsLeft ;;
esac

reset_83() {
  curl -s -f -m 10 -X POST -H "X-Ignition-API-Token: ${GATEWAY_API_TOKEN:?}" "${base}/data/api/v1/trial" >/dev/null
}

reset_81() {
  local jar loc oidc state nonce authn t1 t2 t3 t4 url
  jar=$(mktemp)
  hop() { curl -s -o /dev/null -b "${jar}" -c "${jar}" -w '%{redirect_url}' "$1"; }
  loc=$(hop "${base}/web/status/licenses"); t1=$(query "${loc}" token)
  oidc=$(hop "${base}/web/login?token=${t1}"); state=$(query "${oidc}" state); nonce=$(query "${oidc}" nonce)
  authn=$(hop "${oidc}"); t2=$(query "${authn}" token)
  t3=$(curl -s -b "${jar}" -c "${jar}" -H 'content-type: application/json' \
    -d "{\"username\":$(json_string "${GATEWAY_ADMIN_USERNAME:?}"),\"password\":$(json_string "${GATEWAY_ADMIN_PASSWORD:?}"),\"token\":$(json_string "${t2}"),\"rememberMe\":false}" \
    "${base}/idp/default/authn/submit-username-password-challenge" | field token)
  t4=$(curl -s -b "${jar}" -c "${jar}" -H 'content-type: application/json' -d "{\"token\":\"${t3}\"}" \
    "${base}/idp/default/authn/next-challenge" | field token)
  url="${base}/idp/default/oidc/auth?app=gateway&response_type=code&client_id=ignition&redirect_uri=%2Fdata%2Ffederate%2Fcallback%2Fignition&scope=openid&state=${state}&nonce=${nonce}&token=${t4}"
  for _ in 1 2 3 4 5 6; do
    [ -n "${url}" ] || break
    case "${url}" in /*) url="${base}${url}" ;; esac
    url=$(hop "${url}")
  done
  curl -s -f -m 10 -X PUT -b "${jar}" -H "origin: ${base}" -H "referer: ${base}/web/status/" "${base}/data/status/trial" >/dev/null
  local rc=$?
  rm -f "${jar}"
  return ${rc}
}

main() {
  [ "${GATEWAY_TRIAL_KEEPALIVE:-false}" = true ] || return 0
  log "keeping the trial running (Ignition ${version})"
  local state left expired delay=${retry}
  while true; do
    state=$(curl -s -m 10 "${base}${status_path}" 2>/dev/null)
    left=$(field "${left_field}" <<< "${state}")
    expired=$(field expired <<< "${state}")
    if [ -z "${expired}" ]; then
      sleep "${retry}"
      continue
    fi
    if [ "${expired}" != true ]; then
      # sleep until just after the predicted expiry (at most an hour, to
      # correct for drift and gateway restarts)
      left=${left%%.*}
      # only digits reach the arithmetic, which would otherwise evaluate what the gateway sent
      case "${left}" in '' | *[!0-9]*) left=0 ;; esac
      [ "${#left}" -gt 6 ] && left=3600
      left=$(( 10#${left} + buffer ))
      [ "${left}" -gt 3600 ] && left=3600
      # the trial runs again, reset some other way: a later failure starts its backoff afresh
      delay=${retry}
      sleep "${left}"
      continue
    fi
    if case "${version}" in 8.1.*) reset_81 ;; *) reset_83 ;; esac; then
      log "trial reset"
      delay=${retry}
    else
      log "WARNING: trial reset failed; retrying in ${delay}s"
      sleep "${delay}"
      delay=$(( delay * 2 ))
      [ "${delay}" -gt "${max_backoff}" ] && delay=${max_backoff}
    fi
  done
}

[ "${BASH_SOURCE[0]}" != "$0" ] || main "$@"
