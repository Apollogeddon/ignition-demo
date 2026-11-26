#!/usr/bin/env bash
# Checks a deployed k3s environment (cluster/environments/k3s, 8.3) end to end,
# without Perspective, as the e2e pipeline runs it after the infra and config
# stages:
#
#   - every gateway pod is Ready, and the active Service routes to exactly one;
#   - https://<host>/StatusPing answers 200 RUNNING through the ingress, and
#     plain HTTP answers 301 to the same HTTPS URL;
#   - the gateway API reports the database connection healthy (with the API key
#     the infra stage generated);
#   - the Assets page's named query returns rows: its SQL
#     (projects/project/.../named-query/assets/list/query.sql), run in the
#     database the connection points at;
#   - each backup CronJob's job completes, when run once by hand (it reaches the
#     gateway through the ingress host from inside the cluster).
#
# Each check retries until WAIT_SECONDS run out, as an 8.3 gateway restarts
# itself once after installing its API key (/StatusPing and the API answer 503
# for about 30 seconds). Exits 1 if any check fails.
#
#   HOST=ignition.10.0.0.2.nip.io GATEWAY_API_TOKEN=iac:... CA_FILE=ca.crt scripts/e2e-check.sh
#
# Settings (environment):
#   HOST               the ingress host (required)
#   GATEWAY_API_TOKEN  the gateway's API key, name:secret (required)
#   CA_FILE            CA certificate the ingress's certificate chains to; empty for the system CAs
#   NAMESPACE          the release's namespace (ignition)
#   RELEASE            the gateway's name, the chart's applicationName (ignition)
#   GATEWAYS           how many gateway pods must be Ready (2: a redundant pair)
#   CONNECTION         the gateway's database connection (demo)
#   DATABASE_POD       the database pod, whose postgres container runs the query (database-0)
#   QUERY_FILE         the named query's SQL (the Assets page's)
#   BACKUP_CRONJOBS    CronJobs to run once and wait for ("ignition-backup database-backup"); empty for none
#   WAIT_SECONDS       how long each check retries (300); INTERVAL seconds between tries (10)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
: "${HOST:?HOST must be the gateway ingress host}"
: "${GATEWAY_API_TOKEN:?GATEWAY_API_TOKEN must be the gateway API key (name:secret)}"
NAMESPACE=${NAMESPACE:-ignition}
RELEASE=${RELEASE:-ignition}
GATEWAYS=${GATEWAYS:-2}
CONNECTION=${CONNECTION:-demo}
DATABASE_POD=${DATABASE_POD:-database-0}
QUERY_FILE=${QUERY_FILE:-${root}/projects/project/src/ignition/named-query/assets/list/query.sql}
BACKUP_CRONJOBS=${BACKUP_CRONJOBS-ignition-backup database-backup}
WAIT_SECONDS=${WAIT_SECONDS:-300}
INTERVAL=${INTERVAL:-10}

https=(-sS --max-time 20)
if [ -n "${CA_FILE:-}" ]; then https+=(--cacert "${CA_FILE}"); fi

failures=0
# check <description> <function>: runs the function until it succeeds or
# WAIT_SECONDS pass, then prints ok or FAIL with its last output
check() {
  local deadline=$((SECONDS + WAIT_SECONDS)) out
  while true; do
    if out=$("$2" 2>&1); then
      echo "ok   $1${out:+: ${out}}"
      return 0
    fi
    if [ "${SECONDS}" -ge "${deadline}" ]; then
      echo "FAIL $1${out:+: ${out}}"
      failures=$((failures + 1))
      return 0
    fi
    sleep "${INTERVAL}"
  done
}

gateways_ready() {
  local pods ready
  pods=$(kubectl -n "${NAMESPACE}" get pods \
    -l "app.kubernetes.io/name=${RELEASE},app.kubernetes.io/instance=${RELEASE}" \
    -o jsonpath='{range .items[*]}{.metadata.name}={.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}')
  ready=$(grep -c '=True$' <<<"${pods}" || true)
  echo "${ready}/${GATEWAYS} Ready" "$(tr '\n' ' ' <<<"${pods}")"
  [ "${ready}" -eq "${GATEWAYS}" ]
}

# active routing: the -active Service selects the Active gateway alone
active_endpoint() {
  local endpoints ready
  endpoints=$(kubectl -n "${NAMESPACE}" get endpointslices \
    -l "kubernetes.io/service-name=${RELEASE}-active" \
    -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}={.conditions.ready}{"\n"}{end}')
  ready=$(grep -c '=true$' <<<"${endpoints}" || true)
  echo "${ready} ready endpoint(s)" "$(tr '\n' ' ' <<<"${endpoints}")"
  [ "${ready}" -eq 1 ]
}

status_ping() {
  local out code
  out=$(curl "${https[@]}" -w '\n%{http_code}' "https://${HOST}/StatusPing")
  code=${out##*$'\n'}
  echo "${code} ${out%$'\n'*}"
  [ "${code}" = 200 ] && grep -q RUNNING <<<"${out}"
}

http_redirect() {
  local out
  out=$(curl -sS --max-time 20 -o /dev/null -w '%{http_code} %{redirect_url}' "http://${HOST}/StatusPing")
  echo "${out}"
  [ "${out}" = "301 https://${HOST}/StatusPing" ]
}

# the API key goes in a header file, so it's never on a command line
database_connection() {
  local body
  body=$(curl "${https[@]}" -f -H @<(printf 'X-Ignition-API-Token: %s\n' "${GATEWAY_API_TOKEN}") \
    "https://${HOST}/data/api/v1/resources/find/ignition/database-connection/${CONNECTION}")
  jq -r '.healthchecks.status.result.message // "no status"' <<<"${body}"
  jq -e '.healthchecks.status.result.healthy == true' <<<"${body}" >/dev/null
}

named_query_rows() {
  local sql rows
  sql=$(sed -e 's/;[[:space:]]*$//' "${QUERY_FILE}")
  # psql over the container's socket, as the database's own user, from the
  # container's environment
  # shellcheck disable=SC2016
  rows=$(kubectl -n "${NAMESPACE}" exec -i "${DATABASE_POD}" -c postgres -- \
    sh -c 'psql -X -v ON_ERROR_STOP=1 -tA -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    <<<"SELECT count(*) FROM (${sql}) AS named_query;")
  rows=$(tr -d '[:space:]' <<<"${rows}")
  echo "${rows} row(s)"
  [[ "${rows}" =~ ^[0-9]+$ ]] && [ "${rows}" -gt 0 ]
}

backup_job() {
  local status
  status=$(kubectl -n "${NAMESPACE}" get job "${job}" -o jsonpath='{.status.succeeded}/{.status.failed}')
  echo "succeeded/failed ${status}"
  [ "${status%%/*}" = 1 ]
}

check "the gateways are Ready" gateways_ready
check "the active Service routes to one gateway" active_endpoint
check "https://${HOST}/StatusPing answers RUNNING through the ingress" status_ping
check "plain HTTP redirects to HTTPS" http_redirect
check "the gateway reports the ${CONNECTION} database connection valid" database_connection
check "the Assets page's named query returns rows" named_query_rows
for cronjob in ${BACKUP_CRONJOBS}; do
  job="${cronjob}-e2e-$(date +%s)"
  if kubectl -n "${NAMESPACE}" create job "${job}" --from="cronjob/${cronjob}" >/dev/null; then
    check "the ${cronjob} CronJob's job completes" backup_job
  else
    echo "FAIL the ${cronjob} CronJob's job could not be created"
    failures=$((failures + 1))
  fi
done

if [ "${failures}" -gt 0 ]; then
  echo "${failures} check(s) failed"
  exit 1
fi
echo "every check passed"
