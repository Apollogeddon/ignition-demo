#!/usr/bin/env bash
# Give an Ignition 8.3 gateway an API key from the environment, so OpenTofu
# (the ignition provider) can configure it from its very first start, with no
# key created by hand. entrypoint.sh runs this before every start.
#
#   GATEWAY_API_TOKEN        <name>:<secret>, the key OpenTofu authenticates
#                            with (IGNITION_TOKEN); the secret is base64url
#                            of 32 random bytes. Unset: nothing is done.
#   GATEWAY_API_TOKEN_LEVEL  security level the key carries (default Api)
#
# What it writes, and why where:
#   external collection   the key (its hash only) and a security level for it;
#                         rewritten on every start, so rotating the secret is
#                         a redeploy
#   core collection       the level's read and write grants, merged into the
#                         gateway's security properties (core shadows external
#                         for those, and the gateway only creates core when it
#                         commissions); existing grants are kept
# On the very first start core does not exist yet: a background step waits
# for commissioning, adds the grants and restarts the gateway once.
#
# 8.1 has no REST API; there this does nothing.
set -euo pipefail

home="${IGNITION_HOME:-/usr/local/bin/ignition}"
resources="${home}/data/config/resources"
level="${GATEWAY_API_TOKEN_LEVEL:-Api}"
java="${home}/lib/runtime/jre/bin/java"
[ -x "${java}" ] || java="${home}/lib/runtime/jre-nix/bin/java"

log() { echo "api-key  | $(date '+%Y/%m/%d %H:%M:%S') | $*"; }

# token hash as Ignition stores it: base64url(sha256(base64url-decoded secret))
hash_token() {
  local b64 hex i
  b64=$(printf '%s' "$1" | tr '_-' '/+')
  while [ $(( ${#b64} % 4 )) -ne 0 ]; do b64="${b64}="; done
  hex=$(printf '%s' "${b64}" | base64 -d | sha256sum | cut -c1-64)
  for ((i = 0; i < 64; i += 2)); do printf "\\x${hex:i:2}"; done | base64 -w0 | tr '+/' '-_' | tr -d '='
}

grant() {
  "${java}" -Dpython.import.site=false -cp "${home}/lib/core/common/*" \
    org.python.util.jython -S "${home}/assets/api_token_grant.py" "${resources}/core" "${level}" 2>/dev/null
}

write_external() {
  local name=$1 hash=$2 dir
  dir="${resources}/external/ignition/api-token/${name}"
  mkdir -p "${dir}"
  cat > "${dir}/config.json" <<EOF
{
  "profile": {
    "secureChannelRequired": false,
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

main() {
  [ -n "${GATEWAY_API_TOKEN:-}" ] || return 0
  local version name secret
  version=$(sed -n 's/^gateway\.version=//p' "${home}/lib/install-info.txt" 2>/dev/null || true)
  case "${version}" in
    8.1.*) return 0 ;;
  esac
  case "${GATEWAY_API_TOKEN}" in
    *:*) name=${GATEWAY_API_TOKEN%%:*}; secret=${GATEWAY_API_TOKEN#*:} ;;
    *) log "WARNING: GATEWAY_API_TOKEN must be <name>:<secret>; no API key installed"; return 0 ;;
  esac
  if [ ! -d "${resources}/external" ]; then
    log "WARNING: no external config collection; no API key installed"
    return 0
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
