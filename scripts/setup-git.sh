#!/usr/bin/env sh
# Enable the Ignition resource sanitiser for this clone: every resource.json is
# passed through scripts/sanitise.py when it is staged (see .gitattributes), so
# Designer saves only show up as diffs when something real changed.
set -eu
cd "$(git rev-parse --show-toplevel)"
git config filter.ignition-resource.clean "uv run --no-project --quiet scripts/sanitise.py"
git config filter.ignition-resource.smudge cat
# re-stage tracked resources through the filter
git ls-files -z -- '*resource.json' | xargs -0 -r git add --renormalize --
echo "resource sanitiser enabled"
