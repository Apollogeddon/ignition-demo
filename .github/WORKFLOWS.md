# GitHub workflows

This repository uses GitHub Actions to check the projects and the infrastructure code, version the repository, build and publish the gateway image, and deploy the documentation site. This page describes each workflow for contributors and maintainers.

## CI orchestration

The root workflow, [`.index.yml`](./workflows/.index.yml) (`index`), runs on every pull request, every push to `main`, a manual run, the `auto-merged` dispatch the merge pipeline sends, and weekly for the patch pipelines. Each of its jobs calls one pipeline, or is a stage of one, so the run page lists every job as `<pipeline> / <stage>`. The pipelines are [forgepy](https://github.com/apollogeddon/forgepy)'s and [forgejs](https://github.com/apollogeddon/forgejs)'s shared ones, and three of the repository's own: [`scripts.yml`](./workflows/scripts.yml), [`infra.yml`](./workflows/infra.yml) and [`docker.yml`](./workflows/docker.yml).

| Job | Pipeline | Runs |
| --- | --- | --- |
| `changes` | (this workflow) | Always: on a pull request, works out which checks the change needs. Each check runs only when its own files, or a workflow, changed |
| `version / release` | forgepy's `version.yml` | On `main`, except on the weekly schedule ([Releases](#releases)) |
| `library (8.1)`, `library (8.3)` / `lint`, `scan`, `test` | forgepy's `library.yml` | On a pull request that changes `projects/`, and on `main` when the run creates a release ([Projects](#projects)) |
| `scripts / lint`, `scripts / test` | `scripts.yml` | On a pull request that changes the scripts, the gateway or the projects, and for a release ([Scripts](#scripts)) |
| `infra / lint`, `infra / scan` | `infra.yml` | On a pull request that changes the OpenTofu code or the Dockerfile, and for a release ([Infra](#infra)) |
| `docker (8.1)`, `docker (8.3)` / `build`, `test`, `push` | `docker.yml` | On a pull request that changes the image, once the library and scripts checks pass; on every push to `main`, which pushes the image ([Gateway image](#gateway-image)) |
| `publish / assets` | (this workflow) | When the run creates a release, once its checks and images pass ([Releases](#releases)) |
| `website / lint`, `scan`, `build`, `check` | forgejs's `website.yml` | Every run but the weekly one ([Documentation site](#documentation-site)) |
| `website / lint (markdown)` | (this workflow) | Every run but the weekly one |
| `pages / deploy` | forgejs's `pages.yml` | On `main`, once the site's checks pass |
| `patch (projects) / update`, `patch (webpage) / update` | forgepy's and forgejs's `patch.yml` | Weekly, on a manual run, and after the `auto-merged` dispatch ([Patches](#patches)) |
| `merge / review`, `merge / squash` | forgepy's `merge.yml` | On Dependabot's pull requests, once every check above passed or was skipped ([Dependabot](#dependabot)) |

A new push to a pull request cancels its previous run. Every other run has a concurrency group of its own, so a run on `main`, running or queued, is never cancelled and a release is never created without its images.

## Projects

The `library` job runs [forgepy](https://github.com/apollogeddon/forgepy)'s `library.yml` on `projects/`, once per Ignition API (8.1 and 8.3). Each run installs that version's [Ignition API stubs](https://pypi.org/project/ignition-api-stubs/) from its uv dependency group (`ignition81` or `ignition83`):

- **Ruff**: checks formatting and lints the scripts, with forgepy's Jython 2.7 rules.
- **basedpyright**: type-checks the scripts against the API stubs.
- **Jython 2.7 compatibility** (`poe compat`): vermin fails on syntax, modules or functions Jython 2.7 lacks, and `forgepy check-jython` fails on the commas after `*args` that Jython rejects.
- **forgepy sync check**: fails if forgepy's managed configs under `projects/.forgepy/` are out of date.
- **Pytest**: runs the unit tests, with mocks for the `system.*` modules.
- **OSV-Scanner**: reports known vulnerabilities in `uv.lock`, failing a pull request on a high or critical one.

There's nothing to build, so the `build` stage is off, and Gitleaks is turned off, as the website's scan already covers the whole repository.

## Scripts

[`scripts.yml`](./workflows/scripts.yml) checks the repository tooling and the project resources.

`scripts / lint`:

- **shellcheck**: lints every shell script in the repository, with a pinned shellcheck version.
- **Sanitised resources**: fails if a committed `resource.json` still carries the Designer's noise.
- **Ignition versions**: `scripts/check-ignition-versions.sh` fails if a file names an Ignition release other than the ones pinned in `gateway/base/<line>/Dockerfile`. Dependabot moves those pins on to each line's patch releases, and this check then lists every other place the new release must go.
- **Event scripts**: fails if the 8.1 gateway event scripts are out of date with their script files.

`scripts / test`:

- **Sanitiser tests**: unit tests for the resource sanitiser.
- **Ignition version check tests**: tests `scripts/check-ignition-versions.sh` itself.
- **Asset installer tests**: tests the gateway image's asset installer.
- **API key bootstrap tests**: tests the script that installs the 8.3 API key.
- **Trial keepalive tests**: tests that the 8.1 sign-in sends any admin password as valid JSON, and that failing resets back off.

## Infra

[`infra.yml`](./workflows/infra.yml) checks the infrastructure code with OpenTofu.

`infra / lint`:

- **Format**: runs `tofu fmt -check` over `cluster/` and `develop/`.
- **Validate**: validates the `platform`, `gateway` and `resources` modules, the k3s `infra` and `config` stages, and `develop/config`. The config stages install the Ignition provider from its network mirror, checked against the build each stage's committed `.terraform.lock.hcl` records.

`infra / scan`:

- **Trivy**: scans the OpenTofu code, the Compose file and the Dockerfile for misconfigurations, failing on high or critical ones. `.trivyignore` lists the accepted findings, each with its reason.

## Gateway image

[`docker.yml`](./workflows/docker.yml) builds the gateway image once per Ignition version, as `docker (8.1)` and `docker (8.3)`. It stays local rather than forgepy's `docker.yml`, as the image is `gateway/Dockerfile` with the Ignition version as a build argument, `main` pushes it as well as a release, and the pushed image is smoke-tested again:

- **`build`**: builds `gateway/Dockerfile` with the projects baked in, into the Actions cache.
- **`test`**: loads the image from that cache and smoke-tests it: that the asset installer ran, the projects load, Perspective serves them, the startup event imports the UDTs, and the icon library and web files are served. On 8.3 it also starts two gateways with an API key and checks that the key is refused over plain HTTP, taken behind a TLS proxy (`X-Forwarded-Proto: https`, as Traefik sends), and taken over plain HTTP with `GATEWAY_API_TOKEN_REQUIRE_TLS=false`.
- **`push`**: on `main`, pushes the image to `ghcr.io/apollogeddon/ignition-gateway`, with an SPDX SBOM and SLSA provenance (`mode=max`) attached as BuildKit attestations. The push builds again from the cache, so it then smoke-tests the pushed image, by digest; if that fails, a release stays a draft. When the run creates a release, it also records the release's image by digest for the release's files.

Every tag starts with the Ignition version:

| Tag | Published |
| --- | --- |
| `<ignition version>-main` | Every push to `main` |
| `<ignition version>-sha-<full commit SHA>` | Every push to `main` |
| `<ignition version>-<release version>` | When the run creates a release |

## Releases

release-please (`.github/release.json`) versions the repository from Conventional Commits. It keeps a release pull request open with the next version and the `CHANGELOG.md` entry, and creates the GitHub release and its `v<version>` tag when that pull request merges.

The release is created as a draft, with its tag created straight away (`draft` and `force-tag-creation`), because the repository's releases are immutable once published and can't take files afterwards. In the same run, as a tag that release-please creates with `GITHUB_TOKEN` doesn't start a workflow of its own:

1. The release's checks run: `library`, `scripts` and `infra`, whatever the release changed.
2. `docker / push` publishes the release's images and records each one by digest.
3. `publish / assets` runs `scripts/release-artifacts.sh` on the release's tag. It builds a zip of each Ignition project (a git archive of `projects/<project>/src`, dated with the commit, so the same commit gives the same bytes), `images-<version>.txt` with the images by digest, and `SHA256SUMS`. It attaches them to the draft and then publishes it.

If a check or an image fails, the release stays a draft. Re-running the failed jobs attaches the files and publishes it.

## Documentation site

Three jobs check the [Astro](https://astro.build/) documentation site in `webpage/` and one deploys it. They aren't path filtered, as Gitleaks scans the whole repository here:

- **`website`**: calls [forgejs](https://github.com/apollogeddon/forgejs)'s `website.yml`: Gitleaks over the whole repository and OSV-Scanner on the site's dependencies (`scan`), Biome and the type check (`lint`), the build (`build`), then the built site's internal links with lychee and every page against WCAG 2.2 A and AA with axe (`check`), so a broken or inaccessible site fails the pull request.
- **`website / lint (markdown)`**: a website stage of the repository's own, as no shared pipeline lints Markdown: `markdownlint-cli2` over every Markdown file in the repository.
- **`pages / deploy`**: on `main`, once both pass, forgejs's `pages.yml` deploys the built site to GitHub Pages. Every push to `main` deploys it, not only a release, as a documentation change makes no release.

## Patches

Weekly, on a manual run, and after the merge pipeline's `auto-merged` dispatch, the patch pipelines commit to `main`:

- **`patch (projects)`**: forgepy's `patch.yml` refreshes forgepy's managed configs in `projects/.forgepy/` and upgrades the packages in `projects/uv.lock` with known vulnerabilities.
- **`patch (webpage)`**: forgejs's `patch.yml` updates the site's vulnerable npm dependencies, after the projects' patch so the two never push at once.

## Dependabot

`merge` calls forgepy's `merge.yml` on Dependabot's pull requests: `review` asks the owner for a review, which CODEOWNERS doesn't request on a bot's, and `squash` turns on squash auto-merge once every check in the run passed or was skipped, then sends the `auto-merged` dispatch so `main`'s pipeline runs for the merge. GitHub Actions updates change workflow files, which the workflow token may not merge, so a person merges those.
