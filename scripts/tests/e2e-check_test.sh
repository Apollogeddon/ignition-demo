#!/usr/bin/env bash
# check() evals each condition later, so the single quotes are deliberate and the
# variables they name are used
# shellcheck disable=SC2016,SC2034
# Tests for e2e-check.sh, with kubectl and curl stubbed: a healthy deployment
# passes, each broken part fails its own check, checks retry, and the API key
# stays off the command line.
set -euo pipefail
script="$(cd "$(dirname "$0")/.." && pwd)/e2e-check.sh"
work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT
failures=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; failures=$((failures + 1)); fi; }

# The stubs answer from STUB_* variables and log what they were asked into $LOG
mkdir -p "${work}/bin"
cat > "${work}/bin/kubectl" <<'STUB'
#!/usr/bin/env bash
echo "kubectl $*" >> "${LOG}/kubectl"
case "$*" in
  *" get pods "*) printf '%b' "${STUB_PODS}" ;;
  *" get endpointslices "*) printf '%b' "${STUB_ENDPOINTS}" ;;
  *" exec "*) cat >> "${LOG}/sql"; printf '%s\n' "${STUB_ROWS}"; exit "${STUB_EXEC_RC:-0}" ;;
  *" create job "*) exit "${STUB_CREATE_RC:-0}" ;;
  *" get job "*) printf '%s' "${STUB_JOB}" ;;
  *) echo "unexpected kubectl $*" >&2; exit 2 ;;
esac
STUB
cat > "${work}/bin/curl" <<'STUB'
#!/usr/bin/env bash
echo "curl $*" >> "${LOG}/curl"
url=""; prev=""
for arg in "$@"; do
  if [ "${prev}" = -H ] && [ "${arg#@}" != "${arg}" ]; then cat "${arg#@}" >> "${LOG}/headers"; fi
  prev=${arg}; url=${arg}
done
case "${url}" in
  https://*/StatusPing)
    # STUB_PING_CODES answers each call in turn, then repeats its last
    n=$(($(cat "${LOG}/pings" 2>/dev/null || echo 0) + 1)); echo "${n}" > "${LOG}/pings"
    read -ra codes <<<"${STUB_PING_CODES}"
    code=${codes[$((n <= ${#codes[@]} ? n - 1 : ${#codes[@]} - 1))]}
    if [ "${code}" = 200 ]; then printf '{"state":"RUNNING"}\n%s' "${code}"; else printf 'Service Unavailable\n%s' "${code}"; fi ;;
  http://*/StatusPing) printf '%s' "${STUB_REDIRECT}" ;;
  */database-connection/*) printf '%s' "${STUB_DB}"; exit "${STUB_DB_RC:-0}" ;;
  *) echo "unexpected curl ${url}" >&2; exit 2 ;;
esac
STUB
chmod +x "${work}/bin/kubectl" "${work}/bin/curl"

healthy=(
  STUB_PODS='ignition-0=True\nignition-1=True\n'
  STUB_ENDPOINTS='10.42.0.5=true\n'
  STUB_PING_CODES=200
  STUB_REDIRECT='301 https://ignition.test/StatusPing'
  STUB_DB='{"healthchecks":{"status":{"result":{"healthy":true,"message":"Valid"}}}}'
  STUB_ROWS=6
  STUB_JOB=1/
)
query="${work}/query.sql"
printf 'SELECT id, name\nFROM asset\nORDER BY name;\n' > "${query}"

run() { # run <name> [VAR=value ...]: a healthy deployment with these changes; output in $work/<name>.out
  local log="${work}/$1" rc=0
  mkdir -p "${log}"
  env PATH="${work}/bin:${PATH}" LOG="${log}" HOST=ignition.test GATEWAY_API_TOKEN=iac:s3cret \
    QUERY_FILE="${query}" WAIT_SECONDS=0 INTERVAL=0 "${healthy[@]}" "${@:2}" \
    bash "${script}" > "${log}.out" 2>&1 || rc=$?
  echo "${rc}" > "${log}.rc"
}
passed() { [ "$(cat "${work}/$1.rc")" = 0 ]; }
failed() { [ "$(cat "${work}/$1.rc")" = 1 ] && grep -q "^FAIL $2" "${work}/$1.out"; }

run healthy
check "a healthy deployment passes every check" 'passed healthy && [ "$(grep -c "^ok " "${work}/healthy.out")" = 8 ]'
check "the named query runs as written, counted" 'grep -q "SELECT count(\*) FROM (SELECT id, name" "${work}/healthy/sql" && grep -q "ORDER BY name) AS named_query;" "${work}/healthy/sql"'
check "the API key is sent as a header" 'grep -qx "X-Ignition-API-Token: iac:s3cret" "${work}/healthy/headers"'
check "the API key is never on a command line" '! grep -q s3cret "${work}/healthy/curl" "${work}/healthy/kubectl"'
check "each backup CronJob is run once" 'grep -q "create job ignition-backup-e2e-[0-9]* --from=cronjob/ignition-backup" "${work}/healthy/kubectl" && grep -q "create job database-backup-e2e-[0-9]* --from=cronjob/database-backup" "${work}/healthy/kubectl"'
check "the system CAs verify the ingress unless CA_FILE is set" '! grep -q -- --cacert "${work}/healthy/curl"'

run ca CA_FILE=/tmp/ca.crt
check "CA_FILE verifies every HTTPS request" 'passed ca && [ "$(grep -c "https://" "${work}/ca/curl")" = "$(grep -c -- "--cacert /tmp/ca.crt" "${work}/ca/curl")" ]'

run one-ready STUB_PODS='ignition-0=True\nignition-1=False\n'
check "a gateway that isn't Ready fails" 'failed one-ready "the gateways are Ready: 1/2"'
run single GATEWAYS=1 STUB_PODS='ignition-0=True\n'
check "GATEWAYS sets how many must be Ready" 'passed single'
run no-endpoint STUB_ENDPOINTS='10.42.0.5=false\n'
check "an active Service with no ready endpoint fails" 'failed no-endpoint "the active Service routes to one gateway: 0"'
run two-endpoints STUB_ENDPOINTS='10.42.0.5=true\n10.42.0.6=true\n'
check "an active Service routing to both gateways fails" 'failed two-endpoints "the active Service routes to one gateway: 2"'
run unavailable STUB_PING_CODES=503
check "a StatusPing that never answers 200 fails" 'failed unavailable "https://ignition.test/StatusPing answers RUNNING through the ingress: 503"'
run no-redirect STUB_REDIRECT='200 '
check "plain HTTP that isn't redirected fails" 'failed no-redirect "plain HTTP redirects to HTTPS: 200"'
run wrong-redirect STUB_REDIRECT='302 https://other.test/'
check "a redirect elsewhere, or not permanent, fails" 'failed wrong-redirect "plain HTTP redirects to HTTPS"'
run faulted STUB_DB='{"healthchecks":{"status":{"result":{"healthy":false,"message":"Faulted"}}}}'
check "a database connection that isn't valid fails, with the gateway's message" 'failed faulted "the gateway reports the demo database connection valid: Faulted"'
run refused STUB_DB='' STUB_DB_RC=22
check "an API call the gateway refuses fails" 'failed refused "the gateway reports the demo database connection valid"'
run no-rows STUB_ROWS=0
check "a named query with no rows fails" 'failed no-rows "the Assets page.s named query returns rows: 0 row"'
run bad-sql STUB_ROWS='ERROR:  relation "asset" does not exist' STUB_EXEC_RC=1
check "a named query that errors fails" 'failed bad-sql "the Assets page.s named query returns rows"'
run backup-failed STUB_JOB=/1
check "a backup job that fails fails" 'failed backup-failed "the ignition-backup CronJob.s job completes"'
run no-backups BACKUP_CRONJOBS=
check "BACKUP_CRONJOBS empty runs no backup" 'passed no-backups && ! grep -q "create job" "${work}/no-backups/kubectl"'
run no-cronjob STUB_CREATE_RC=1
check "a missing backup CronJob fails" 'failed no-cronjob "the ignition-backup CronJob.s job could not be created"'

# the gateway restarts once after installing its API key: a 503 that clears is retried
run restart STUB_PING_CODES='503 503 200' WAIT_SECONDS=5
check "a StatusPing that recovers within WAIT_SECONDS passes" 'passed restart && [ "$(cat "${work}/restart/pings")" = 3 ]'

run all-broken STUB_PODS='ignition-0=False\n' STUB_PING_CODES=503 STUB_ROWS=0
check "every failed check is reported, with the count" 'grep -q "^3 check(s) failed" "${work}/all-broken.out"'

rc=0; env -u HOST GATEWAY_API_TOKEN=x bash "${script}" > "${work}/no-host.out" 2>&1 || rc=$?
check "HOST is required" '[ "${rc}" != 0 ] && grep -q "HOST must be" "${work}/no-host.out"'
rc=0; env -u GATEWAY_API_TOKEN HOST=x bash "${script}" > "${work}/no-token.out" 2>&1 || rc=$?
check "GATEWAY_API_TOKEN is required" '[ "${rc}" != 0 ] && grep -q "GATEWAY_API_TOKEN must be" "${work}/no-token.out"'

if [ "${failures}" -gt 0 ]; then echo "${failures} failure(s)"; exit 1; fi
echo "all passed"
