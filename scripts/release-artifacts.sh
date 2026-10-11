#!/bin/bash
# Builds the files attached to a GitHub release, in <out-dir>:
#   ignition-<project>-<version>.zip  each Ignition project, as the gateway's
#                                     project import takes it (project.json at the top)
#   images-<version>.txt              the release's gateway images by digest, from
#                                     the files given after <out-dir> (one image@digest
#                                     line each)
#   SHA256SUMS                        the checksums of the files above
# The zips are git archives of the commit, dated with its commit time, so the same
# commit always gives the same bytes. Usage: release-artifacts.sh <version> <out-dir> [image-digest-file...]
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <version> <out-dir> [image-digest-file...]" >&2
  exit 2
fi
version=$1
out=$2
shift 2

root=$(git rev-parse --show-toplevel)
mkdir -p "$out"
out=$(realpath "$out")
# an archive of a tree (not a commit) is otherwise dated now
mtime=$(git -C "$root" log -1 --format=%cI HEAD)

for dir in "$root"/projects/*/src; do
  [ -f "$dir/project.json" ] || continue
  project=$(basename "$(dirname "$dir")")
  git -C "$root" archive --format=zip --mtime="$mtime" -o "$out/ignition-$project-$version.zip" \
    "HEAD:projects/$project/src"
done

if [ $# -gt 0 ]; then
  sort "$@" >"$out/images-$version.txt"
fi

files=$(cd "$out" && find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%f\n' | LC_ALL=C sort)
# shellcheck disable=SC2086 # the names are ours: no spaces
(cd "$out" && sha256sum $files >SHA256SUMS)
ls -l "$out"
