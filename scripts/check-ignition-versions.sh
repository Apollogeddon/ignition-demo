#!/usr/bin/env bash
# Check that every tracked file names the Ignition releases pinned in
# gateway/base/<line>/Dockerfile, which Dependabot moves on: after its pull
# request, this lists each place still on the old release.
#
#   scripts/check-ignition-versions.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

status=0
for line in 8.1 8.3; do
  pin=$(sed -n 's|^FROM docker\.io/inductiveautomation/ignition:||p' "gateway/base/${line}/Dockerfile")
  if [ -z "${pin}" ]; then
    echo "gateway/base/${line}/Dockerfile: no ignition image tag" >&2
    status=1
    continue
  fi
  # lockfiles and the changelog name other packages' versions and past releases,
  # the API stubs follow their own releases, and this script's test names others
  stale=$(git grep -nwE "${line//./\\.}\.[0-9]+" -- . ':!CHANGELOG.md' ':!*package-lock.json' \
    ':!projects/uv.lock' ':!projects/pyproject.toml' ':!scripts/tests/check-ignition-versions_test.sh' \
    | grep -vwE "${pin//./\\.}" || true)
  if [ -n "${stale}" ]; then
    echo "Ignition ${line} is pinned at ${pin}, but these name another ${line} release:" >&2
    printf '%s\n' "${stale}" >&2
    status=1
  fi
done
[ "${status}" -ne 0 ] || echo "Ignition versions match gateway/base"
exit "${status}"
