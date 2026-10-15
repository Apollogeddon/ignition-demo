#!/usr/bin/env bash
# Give an Ignition 8.3 gateway an API key from the environment, so OpenTofu
# (the ignition provider) can configure it from its very first start, with no
# key created by hand. entrypoint.sh runs this before every start.
#
#   GATEWAY_API_TOKEN        <name>:<secret>, the key OpenTofu authenticates
#                            with (IGNITION_TOKEN); the secret is base64url
#                            of 32 random bytes. Unset: nothing is done, unless
#                            GATEWAY_TRIAL_KEEPALIVE=true on 8.3, which fails the start
#   GATEWAY_API_TOKEN_LEVEL  security level the key carries (default Api)
#   GATEWAY_API_TOKEN_REQUIRE_TLS
#                            true (default): the gateway takes the key over
#                            HTTPS only (or behind a TLS proxy that sets
#                            X-Forwarded-Proto); false also takes it over plain
#                            HTTP, for a local gateway on loopback. With
#                            GATEWAY_TRIAL_KEEPALIVE=true on 8.3 it must be false,
#                            or GATEWAY_TRIAL_URL https://, or the start fails:
#                            the keepalive resets the trial with the key
#
# What it writes, and why where:
#   external collection   the key (its hash only), rewritten on every start so
#                         rotating the secret is a redeploy, and its security
#                         level, added to any levels already defined there
#   core collection       the level's read and write grants, merged into the
#                         gateway's security properties (core shadows external
#                         for those, and the gateway only creates core when it
#                         commissions); existing grants are kept
# On the very first start core does not exist yet: a background step waits
# for commissioning, adds the grants and restarts the gateway once.
#
# With GATEWAY_TRIAL_KEEPALIVE=true it also fails the start when the keepalive
# couldn't reset the trial: no usable key on 8.3, or no admin login on 8.1.
#
# 8.1 has no REST API; there it installs nothing.
set -euo pipefail

home="${IGNITION_HOME:-/usr/local/bin/ignition}"
resources="${home}/data/config/resources"
level="${GATEWAY_API_TOKEN_LEVEL:-Api}"
require_tls="${GATEWAY_API_TOKEN_REQUIRE_TLS:-true}"
java="${home}/lib/runtime/jre/bin/java"
[ -x "${java}" ] || java="${home}/lib/runtime/jre-nix/bin/java"

log() { echo "api-key  | $(date '+%Y/%m/%d %H:%M:%S') | $*"; }

# token hash as Ignition stores it: base64url(sha256(base64url-decoded secret))
hash_token() {
  local b64 hex i
  b64=$(printf '%s' "$1" | tr '_-' '/+')
  while [ $(( ${#b64} % 4 )) -ne 0 ]; do b64="${b64}="; done
  hex=$(printf '%s' "${b64}" | base64 -d | sha256sum | cut -c1-64)
  for ((i = 0; i < 64; i += 2)); do printf '%b' "\\x${hex:i:2}"; done | base64 -w0 | tr '+/' '-_' | tr -d '='
}

jython() {
  "${java}" -Dpython.import.site=false -cp "${home}/lib/core/common/*" \
    org.python.util.jython -S "${home}/assets/api_token_grant.py" "$@" 2>/dev/null
}

grant() { jython "${resources}/core" "${level}"; }

# names become a directory and JSON strings, so only plain ones are taken
plain() { [[ $1 =~ ^[A-Za-z0-9_.-]+$ && $1 != . && $1 != .. ]]; }

write_external() {
  local name=$1 hash=$2 dir
  dir="${resources}/external/ignition/api-token/${name}"
  mkdir -p "${dir}"
  cat > "${dir}/config.json" <<EOF
{
  "profile": {
    "secureChannelRequired": ${require_tls},
    "securityLevels": [
      {
        "children": [],
        "name": "Authenticated"
      },
      {
        "children": [],
        "name": "${level}"
      }
    ],
    "timestamp": 1735689600000,
    "type": "basic-token"
  },
  "settings": {
    "tokenHash": "${hash}"
  }
}
EOF
  printf '{\n  "attributes": {\n    "enabled": true\n  },\n  "files": [\n    "config.json"\n  ],\n  "overridable": true,\n  "restricted": false,\n  "scope": "A",\n  "version": 1\n}\n' > "${dir}/resource.json"
  dir="${resources}/external/ignition/security-levels"
  # levels defined there already are kept: only a missing one is added
  if [ -f "${dir}/config.json" ]; then
    # --define checks the top-level names itself: 3 means the level is already there
    local status=0
    jython --define "${dir}/config.json" "${level}" || status=$?
    [ "${status}" -eq 0 ] || [ "${status}" -eq 3 ] || log "WARNING: could not add security level ${level} to ${dir}/config.json"
    return 0
  fi
  mkdir -p "${dir}"
  cat > "${dir}/config.json" <<EOF
{
  "securityLevels": [
    {
      "children": [
        {
          "children": [
            {
              "children": [],
              "description": "System generated security level representing read and write privileges to Gateway configuration",
              "name": "Administrator"
            }
          ],
          "description": "Represents the roles that a user has.",
          "name": "Roles"
        }
      ],
      "description": "Represents a user who has been authenticated by the system.",
      "name": "Authenticated"
    },
    {
      "children": [],
      "description": "Held by the gateway's infrastructure-as-code API key",
      "name": "${level}"
    }
  ]
}
EOF
  printf '{\n  "attributes": {\n    "enabled": true\n  },\n  "files": [\n    "config.json"\n  ],\n  "overridable": true,\n  "restricted": false,\n  "scope": "A",\n  "version": 1\n}\n' > "${dir}/resource.json"
}

# first start: wait for commissioning to create core, grant, restart once
after_commissioning() {
  local i status
  for i in $(seq 360); do
    if curl -s -m 3 http://localhost:8088/StatusPing 2>/dev/null | grep -q RUNNING; then
      status=0
      grant || status=$?
      if [ "${status}" -eq 0 ]; then
        log "granted ${level} after commissioning; restarting the gateway once to apply it"
        "${home}/gwcmd.sh" -r >/dev/null 2>&1 || log "WARNING: gateway restart failed; restart it to enable the API key"
        return
      fi
      [ "${status}" -eq 3 ] && return
    fi
    sleep 5
  done
  log "WARNING: gateway did not commission within 30 minutes; API key grants not added"
}

# keepalive_needs_key: trial-keepalive.sh resets an 8.3 trial with this key
keepalive_needs_key() { [ "${GATEWAY_TRIAL_KEEPALIVE:-false}" = true ]; }

# not_installed <reason>: no key is installed. That's a warning, unless the trial keepalive
# needs the key, when the start fails now rather than the keepalive at the trial's expiry.
not_installed() {
  if keepalive_needs_key; then
    log "ERROR: GATEWAY_TRIAL_KEEPALIVE=true resets an 8.3 trial with the API key, but $1"
    return 1
  fi
  log "WARNING: $1; no API key installed"
}

main() {
  local version name secret
  version=$(sed -n 's/^gateway\.version=//p' "${home}/lib/install-info.txt" 2>/dev/null || true)
  case "${version}" in
    8.1.*)
      # the 8.1 keepalive signs in as the gateway admin instead
      if keepalive_needs_key && { [ -z "${GATEWAY_ADMIN_USERNAME:-}" ] || [ -z "${GATEWAY_ADMIN_PASSWORD:-}" ]; }; then
        log "ERROR: GATEWAY_TRIAL_KEEPALIVE=true resets an 8.1 trial by signing in as the gateway admin; set GATEWAY_ADMIN_USERNAME and GATEWAY_ADMIN_PASSWORD"
        return 1
      fi
      return 0
      ;;
  esac
  if [ -z "${GATEWAY_API_TOKEN:-}" ]; then
    keepalive_needs_key || return 0
    not_installed "GATEWAY_API_TOKEN isn't set"
    return
  fi
  case "${GATEWAY_API_TOKEN}" in
    *:*) name=${GATEWAY_API_TOKEN%%:*}; secret=${GATEWAY_API_TOKEN#*:} ;;
    *) not_installed "GATEWAY_API_TOKEN must be <name>:<secret>"; return ;;
  esac
  if ! plain "${name}" || ! plain "${level}"; then
    not_installed "the key name and GATEWAY_API_TOKEN_LEVEL may only hold letters, digits, '.', '_' and '-'"
    return
  fi
  case "${require_tls}" in
    true | false) ;;
    *) not_installed "GATEWAY_API_TOKEN_REQUIRE_TLS must be true or false"; return ;;
  esac
  # the keepalive sends the key to GATEWAY_TRIAL_URL, plain HTTP on loopback unless set, which
  # a key that needs TLS is refused on
  if keepalive_needs_key && [ "${require_tls}" = true ] \
    && [[ ${GATEWAY_TRIAL_URL:-http://localhost:8088} != https://* ]]; then
    log "ERROR: GATEWAY_TRIAL_KEEPALIVE=true resets the trial with the API key over plain HTTP, which the key refuses; set GATEWAY_API_TOKEN_REQUIRE_TLS=false (a gateway on loopback or a private network) or an https:// GATEWAY_TRIAL_URL"
    return 1
  fi
  if [ ! -d "${resources}/external" ]; then
    not_installed "there's no external config collection"
    return
  fi
  write_external "${name}" "$(hash_token "${secret}")"
  if [ -d "${resources}/core" ]; then
    local status=0
    grant || status=$?
    [ "${status}" -eq 0 ] && log "granted ${level} gateway read and write access"
  else
    after_commissioning &
  fi
  log "API key ${name} installed (level ${level})"
}

# run unless sourced (the tests source it for hash_token)
[ "${BASH_SOURCE[0]}" != "$0" ] || main "$@"
