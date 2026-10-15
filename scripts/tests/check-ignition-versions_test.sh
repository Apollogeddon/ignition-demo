#!/usr/bin/env bash
# check() evals each condition later, so the single quotes are deliberate
# shellcheck disable=SC2016
# Tests for check-ignition-versions.sh, in a scratch repository.
set -euo pipefail
script="$(cd "$(dirname "$0")/.." && pwd)/check-ignition-versions.sh"
work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT
failures=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; failures=$((failures + 1)); fi; }

repo() { # repo <dir>: pins at 8.1.55 and 8.3.10, and a file naming both
  git init -q "$1"
  mkdir -p "$1/gateway/base/8.1" "$1/gateway/base/8.3" "$1/scripts"
  echo "FROM docker.io/inductiveautomation/ignition:8.1.55" > "$1/gateway/base/8.1/Dockerfile"
  echo "FROM docker.io/inductiveautomation/ignition:8.3.10" > "$1/gateway/base/8.3/Dockerfile"
  printf 'ignition: ["8.1.55", "8.3.10"]\n' > "$1/index.yaml"
  echo "8.3.9 was the last" > "$1/CHANGELOG.md"
  cp "${script}" "$1/scripts/"
  git -C "$1" add -A
}
run() { (cd "$1" && bash scripts/check-ignition-versions.sh) > "$1.out" 2>&1; }

r="${work}/same"; repo "$r"
check "versions that match the pins pass, past ones in the changelog ignored" 'run "$r"'

r="${work}/bumped"; repo "$r"
echo "FROM docker.io/inductiveautomation/ignition:8.3.11" > "$r/gateway/base/8.3/Dockerfile"; git -C "$r" add -A
check "a bumped pin fails" '! run "$r"'
check "and names the file still on the old release" 'grep -q "index.yaml:1:" "$r.out" && grep -q "pinned at 8.3.11" "$r.out"'

if [ "${failures}" -ne 0 ]; then echo "${failures} failed"; exit 1; fi
echo "all passed"
