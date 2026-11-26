---
name: validate
description: Run every check CI runs on this repository (OpenTofu fmt/validate/test, the scripts and their tests, the projects' ruff/basedpyright/compat/pytest for 8.1 and 8.3, actionlint, markdownlint) and report pass/fail per area. Use before calling a change done, or when asked to validate, lint or test.
---

Run from the repository root. Run every area unless the user named some. Never stop at the first failure. End with one table, `area | check | pass/fail/skipped (why)`. Print only the failing output.

## 0. Tools

`SCRATCH` is the session's scratchpad directory, or `mktemp -d`: nothing below writes into the tree beyond the git-ignored caches. Each Bash call starts a fresh shell, so set `SCRATCH` and `TF_CLI_CONFIG_FILE` in every call that needs them.

`command -v tofu uv shellcheck actionlint npx`. A missing tool marks its checks **skipped (not installed)**, never passed. If there's no `tofu`, say so: CI uses OpenTofu 1.13.1. A copy unzipped from `github.com/opentofu/opentofu/releases` into the scratchpad works, if the user agrees.

## 1. cluster / develop (OpenTofu)

Write the Ignition provider's mirror to a scratch CLI config, as `infra.yml` does, and keep `.terraform/` out of the tree:

```sh
cat >"$SCRATCH/tofurc" <<'EOF'
provider_installation {
  network_mirror {
    url     = "https://apollogeddon.github.io/ignition-tofu/providers/"
    include = ["registry.opentofu.org/apollogeddon/ignition"]
  }
  direct {
    exclude = ["registry.opentofu.org/apollogeddon/ignition"]
  }
}
EOF
export TF_CLI_CONFIG_FILE="$SCRATCH/tofurc"
tofu fmt -check -recursive cluster develop
for dir in cluster/modules/platform cluster/modules/gateway cluster/modules/resources \
           cluster/environments/k3s/infra cluster/environments/k3s/config develop/config; do
  export TF_DATA_DIR="$SCRATCH/tfdata/${dir//\//_}"
  lock=; case "$dir" in cluster/modules/*) ;; *) lock=-lockfile=readonly ;; esac
  tofu -chdir="$dir" init -backend=false -input=false $lock >/dev/null && tofu -chdir="$dir" validate
done
# tofu test (mock providers): the three modules and the k3s infra stage
for dir in cluster/modules/platform cluster/modules/gateway cluster/modules/resources cluster/environments/k3s/infra; do
  TF_DATA_DIR="$SCRATCH/tfdata/${dir//\//_}" tofu -chdir="$dir" test
done
```

- The stages' `.terraform.lock.hcl` are committed: `-lockfile=readonly` keeps `init` from rewriting them. The modules' lock files are git-ignored.
- `doesn't match any of the checksums previously recorded`: a stale local module lock file. Validate a copy of `cluster/` in the scratchpad without it, or ask before deleting it.
- **Sandboxes:** `registry.opentofu.org` or `apollogeddon.github.io` may be blocked by the proxy. Without the registry, nothing installs. Then mark tofu validate/test **skipped (registry blocked)** and keep `fmt`, which needs no providers. Without the mirror, only `resources`, `k3s/config` and `develop/config` fail. Either way, a filesystem mirror works:
  1. Somewhere with access, run `tofu providers mirror <dir>` in each stage.
  2. Copy `<dir>` over.
  3. Replace `network_mirror { url = ... }` with `filesystem_mirror { path = "<dir>" }` in the tofurc.

## 2. scripts / gateway

```sh
scripts/check-ignition-versions.sh
uv run --no-project --with pytest pytest -q -p no:cacheprovider scripts/tests
for t in scripts/tests/*_test.sh gateway/tests/*_test.sh; do bash "$t" >/dev/null || echo "FAIL $t"; done
git ls-files -z '*.sh' | xargs -0 shellcheck
git ls-files -z -- '*resource.json' | xargs -0 uv run --no-project scripts/sanitise.py --check
```

`gateway/tests/smoke.sh` needs Docker and a built image (CI's `docker / test`). Run it only when asked.

## 3. projects (both Ignition API groups)

```sh
cd projects
uv sync --frozen
uv run poe sync-check
uv run ruff format --check . && uv run ruff check .
uv run poe type && uv run poe compat && uv run poe test
export UV_PROJECT_ENVIRONMENT="${SCRATCH}/venv-81"
uv sync --frozen --no-default-groups --group dev --group ignition81
uv run --no-sync basedpyright && uv run --no-sync pytest -q
```

`poe lint` rewrites files, so the check-only ruff commands stand in for it here. `forgepy` comes from a git tag on github.com: if `uv sync` can't fetch it, reuse an existing `projects/.venv` with `--no-sync`.

## 4. ci

`actionlint` (it reads `.github/workflows/`). Not installed: **skipped**. CI has no actionlint stage, so say that a workflow change is unchecked.

## 5. docs

`npx markdownlint-cli2 "**/*.{md,mdx}"` (check only; `npm run lint:md` adds `--fix`). It needs `npm ci`, which needs a GitHub Packages token for `@apollogeddon/forgejs`. Without one: **skipped**. `webpage/` lint and build (`npm run lint`, `type`, `build` there) run only when the site changed.
