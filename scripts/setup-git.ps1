# Enable the Ignition resource sanitiser for this clone (see setup-git.sh).
$ErrorActionPreference = 'Stop'
Set-Location (git rev-parse --show-toplevel)
git config filter.ignition-resource.clean 'uv run --no-project --quiet scripts/sanitise.py'
git config filter.ignition-resource.smudge cat
git add --renormalize -- '*resource.json'
Write-Output 'resource sanitiser enabled'
