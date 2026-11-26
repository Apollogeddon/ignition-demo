# Claude Code Instructions

General working rules (subagent routing, tool use, response style) live in the user-level `~/.claude/CLAUDE.md`. This file is project-specific.

## Reading the codebase

`cluster/`, `develop/`, `gateway/`, `scripts/` and the projects' scripts are small: read what you need directly. Use an `Explore` agent only for `webpage/` (a separate Astro package), `node_modules` and `projects/.venv`. Secrets and noise are denied to `Read` in `settings.json`, and `.claude/hooks/guard.py` blocks any other `*.tfvars`, `.env` or `backend.hcl`: tfstate, real tfvars, `backend.hcl`, `develop/.env`, `.terraform/`, the lockfiles (`uv.lock`, `package-lock.json`, `.terraform.lock.hcl`) and `webpage/dist`. Read the `.example` instead, and check a resolved version with `uv tree`, `npm ls <pkg>` or `tofu providers`.

A `PostToolUse` hook (`.claude/hooks/read_counter.py`) reminds you past 10 Read/Grep/Glob calls in a session.

## Quality Control

- A `PostToolUse` hook (`.claude/hooks/lint_on_edit.py`) runs on every file touched by `Edit`/`Write`: `tofu fmt` on `*.tf`/`*.tftest.hcl`, `ruff check --fix` + `ruff format` on `projects/**/*.py` (the projects' uv env), `shellcheck` on `*.sh`, `actionlint` on workflows, and `scripts/sanitise.py --check` on a project's `resource.json`. Errors it can't fix are returned to you: fix them before moving on. A tool not on PATH is skipped silently, so run its check yourself or say it wasn't run.
- `/validate` runs every check below and reports per area. Before reporting a change complete, run the checks for each area it touches:
  - **cluster/develop:** `tofu fmt -check -recursive cluster develop`; `tofu validate` in each module and stage (`init -backend=false` first); `tofu test` in `cluster/modules/{platform,gateway,resources}` and `cluster/environments/k3s/infra`. `resources`, the config stages and `develop/config` need the Ignition provider mirror in `TF_CLI_CONFIG_FILE` (see `/validate`).
  - **scripts/gateway:** `scripts/check-ignition-versions.sh`, `uv run --no-project --with pytest pytest -q scripts/tests`, `bash scripts/tests/*_test.sh`, `bash gateway/tests/*_test.sh`, shellcheck on every `*.sh`, and `sanitise.py --check` on every `resource.json`.
  - **projects:** in `projects/`, `uv run poe lint`, `type`, `compat`, `test` and `sync-check`, for both the `ignition83` (default) and `ignition81` groups.
  - **ci:** `actionlint` on changed workflows.
  - **docs:** `npm run lint:md` (markdownlint-cli2, `.markdownlint-cli2.jsonc`).
- Run `/code-review` (medium+) on non-trivial diffs before considering them done; use `/simplify` as a cleanup pass afterward.

## Architecture

Ignition 8.1 or 8.3 as code: one repository builds the gateway image, its configuration and its projects.

- **`gateway/`** is the image: `gateway/Dockerfile` (one `IGNITION_VERSION` build arg for both lines) bakes in `projects/*/src`, assets and the 8.1 seed (`seed/seed.json`). `api-token.sh` installs the 8.3 API key on start and restarts the gateway once. `gateway/base/<line>/Dockerfile` only pins each line's release for Dependabot.
- **`projects/`** is the Ignition projects (`library`, inherited by `project`) as the Designer writes them, plus their Python checks: forgepy's Jython setup, ruff, basedpyright against the `ignition-api-stubs` group per version, `poe compat` (vermin + `forgepy check-jython`) and pytest with `system.*` mocks in `conftest.py`. `scripts/sanitise.py` (a git filter, `scripts/setup-git.sh`) strips Designer noise from `resource.json`.
- **`develop/`** is the compose stack: the gateway built from `gateway/Dockerfile` with the project folders mounted live, and Postgres. `develop/config` applies the cluster's `resources` module to it on 8.3.
- **`cluster/`** is three modules, `platform` (namespace, Postgres, backups), `gateway` (the `ignition-failover` chart, its Secret, backups) and `resources` (gateway resources through the Ignition provider, 8.3), and the k3s environment's two stages: `infra` (platform + gateway) and then `config` (resources, reading `infra`'s state). Both use the kubernetes backend (a Secret plus Lease in `tofu-state`) with state and plans encrypted by `TF_VAR_state_passphrase`. `chart_path` installs a local, unreleased chart; a chart from 5.0, or a local one, takes the module's own Secret through `existingSecret`.
- **`webpage/`** is the Astro docs site. `webpage/src/content/docs/components/*.md` mirror the component READMEs.
- **CI.** `.github/workflows/.index.yml` is the root workflow. Its `changes` job path-filters the checks, and each job calls one pipeline: forgepy's `library`/`version`/`patch`/`merge` and forgejs's `website`/`pages` at `@main`, plus the repository's own `scripts.yml`, `infra.yml`, `docker.yml` and `deploy.yml`. `deploy.yml` runs only on a manual run (or `DEPLOY_ON_PUSH`), and plans in the `k3s-plan` environment and applies the reviewed, encrypted plan in `k3s`. `.github/WORKFLOWS.md` documents every job.

## Change checklist

- **A module or stage input:**
  1. `variables.tf` (with a `validation` where it has rules);
  2. the inputs table in `cluster/README.md`;
  3. a `run` in the module's `tests/*.tftest.hcl`;
  4. the k3s `infra`/`config` wiring, `k3s.example.tfvars`, and `develop/config` if it applies there.
- **A chart value:** the key must exist in the chart's `values.schema.json` for the pinned `chart_version` (and any `chart_path` chart). Every container needs `run_as_non_root`: kubernetes provider 3.5 sends an unset one as false, and restricted Pod Security rejects it.
- **An Ignition version:** follow `/bump-ignition`; `scripts/check-ignition-versions.sh` lists every place still on the old release.
- **A `resource.json`:** keep it sanitised (`scripts/sanitise.py --fix`), and regenerate the 8.1 event scripts with `scripts/generate-event-scripts.sh` when a gateway event script changes.
- **A project script:** Jython 2.7 rules (type comments, `.format()`, `from .code import *` in `__init__.py`, listed in `resource.json`), plus a test in `projects/<project>/tests`.
- **A workflow:** actionlint, the job table in `.github/WORKFLOWS.md`, and the `changes` filter in `.index.yml` if it adds paths.
- **Docs:** update the README, and its mirror under `webpage/src/content/docs/`, in the same change.

## Deployment rules

- Never run `tofu apply`/`destroy`, `state rm/mv/push`, `import`, `kubectl apply/delete`, `helm install/upgrade/uninstall` or `docker compose down -v` without the user asking for that run. `settings.json` asks for these anyway. `/deploy-develop` and `/deploy-k3s` stop before each one.
- State, plans, `terraform.tfvars`, `backend.hcl` and `develop/.env` hold secrets. Never read, print, commit or paste them. Pass passwords and keys as `TF_VAR_*` or in git-ignored files.
- Only the user can accept the Ignition EULA. Never set `accept_eula = true` in a committed file other than a test, and keep it commented out in `k3s.example.tfvars`; `guard.py` blocks it in example files. `develop/` and the smoke tests accept it for the local image only.

## Commits

A one-line, lowercase conventional subject, `type(scope): what, so why`, with the scope `cluster`, `develop`, `gateway`, `projects`, `ci` or `docs` (`deps` is Dependabot's). For example: `fix(cluster): set runAsNonRoot on every container, as kubernetes provider 3.5 sends it unset as false`. No body or trailers unless asked. Stage paths explicitly, never `git add -A`.
