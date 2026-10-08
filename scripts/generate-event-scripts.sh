#!/usr/bin/env bash
# Regenerate each project's Ignition 8.1 gateway events (event-scripts/data.bin)
# from its 8.3 event script files (ignition/startup/onStartup.py, ...), using
# Ignition 8.1's own serializer in its Docker image. Run after changing an
# event script; CI checks the generated files are up to date.
#
#   scripts/generate-event-scripts.sh [project ...]     (default: every project
#                                                        with event scripts)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
image="docker.io/inductiveautomation/ignition:${IGNITION_81_VERSION:-8.1.55}"
engine=${CONTAINER_ENGINE:-$(command -v docker >/dev/null && echo docker || echo podman)}
export MSYS_NO_PATHCONV=1

projects=("$@")
if [ ${#projects[@]} -eq 0 ]; then
  shopt -s nullglob
  for dir in projects/*/src/ignition; do
    events=("${dir}"/startup/on*.py "${dir}"/update/on*.py "${dir}"/shutdown/on*.py)
    [ ${#events[@]} -gt 0 ] && projects+=("$(basename "$(dirname "$(dirname "${dir}")")")")
  done
  shopt -u nullglob
fi

root=$(pwd)
command -v cygpath >/dev/null && root=$(cygpath -m "${root}")
for project in "${projects[@]}"; do
  echo "${project}:"
  "${engine}" run --rm --user "$(id -u):$(id -g)" \
    -v "${root}/projects/${project}/src:/project" \
    -v "${root}/scripts/ignition:/tools:ro" \
    --entrypoint /usr/local/bin/ignition/lib/runtime/jre-nix/bin/java "${image}" \
    -Dpython.import.site=false -cp "/usr/local/bin/ignition/lib/core/common/*" \
    org.python.util.jython -S /tools/event_scripts.py /project 2>&1 | grep -v ' DEBUG '
done
