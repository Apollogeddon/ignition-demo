# GitHub workflows

This repository uses GitHub Actions to check the projects and the infrastructure code, version the repository, build and publish the gateway image, and deploy the documentation site. This page describes each workflow for contributors and maintainers.

## CI orchestration

The [`ci.yaml`](./workflows/ci.yaml) workflow runs on every pull request, every push to `main`, and on manual dispatch:

1. **Changes**: on a pull request, works out which checks the change needs. Each check runs only when its own files, or `ci.yaml`, changed. A push to `main` or a manual run checks everything.
2. **Projects**, **Resources and scripts**, and **OpenTofu and config scan** run in parallel.
3. **Version**: on a push to `main`, after those checks, opens or updates release-please's release pull request, and creates the release when it merges.
4. **Gateway image**: after the project and resource checks pass. On `main` it publishes the image, with the release's version when Version created one.
5. **Webpage**: on a pull request, the documentation site's checks and build ([below](#documentation-site)).
6. **Auto-merge**: on a pull request, merges a Dependabot pull request through [forgepy](https://github.com/apollogeddon/forgepy)'s `merge.yml`, once every job above has passed or been skipped.

A new push to a pull request cancels its previous run. Runs on `main` are never cancelled, so a release is never created without its images.

## Projects

The `projects` job runs [forgepy](https://github.com/apollogeddon/forgepy)'s reusable `testing.yml` on `projects/` with Python 3.12, once per Ignition API (8.1 and 8.3). Each run installs that version's [Ignition API stubs](https://pypi.org/project/ignition-api-stubs/) from its uv dependency group (`ignition81` or `ignition83`):

- **Ruff**: checks formatting and lints the scripts, with forgepy's Jython 2.7 rules.
- **basedpyright**: type-checks the scripts against the API stubs.
- **Jython 2.7 compatibility** (`poe compat`): vermin fails on syntax, modules or functions Jython 2.7 lacks, and `forgepy check-jython` fails on the commas after `*args` that Jython rejects.
- **forgepy sync check**: fails if forgepy's managed configs under `projects/.forgepy/` are out of date.
- **Pytest**: runs the unit tests, with mocks for the `system.*` modules.
- **OSV-Scanner**: reports known vulnerabilities in `uv.lock`. On `main`, the 8.3 run upgrades the vulnerable packages and commits the new lock file.

Gitleaks is turned off here, as the webpage checks already scan the whole repository.

## Resources and scripts

The `resources` job checks the repository tooling and the project resources:

- **shellcheck**: lints every shell script in the repository, with a pinned shellcheck version.
- **Sanitiser tests**: unit tests for the resource sanitiser.
- **Sanitised resources**: fails if a committed `resource.json` still carries the Designer's noise.
- **Asset installer tests**: tests the gateway image's asset installer.
- **API key bootstrap tests**: tests the script that installs the 8.3 API key.
- **Event scripts**: fails if the 8.1 gateway event scripts are out of date with their script files.

## OpenTofu and config scan

The `tofu` job checks the infrastructure code:

- **Format**: runs `tofu fmt -check` over `cluster/` and `develop/`.
- **Validate**: validates the `platform` and `gateway` modules and the k3s `infra` stage.
- **Trivy**: scans the OpenTofu code, the Compose file and the Dockerfile for misconfigurations, failing on high or critical ones. `.trivyignore` lists the accepted findings, each with its reason.

## Gateway image

The `image` job builds the gateway image once per Ignition version (8.1.55 and 8.3.10):

- **Build**: builds `gateway/Dockerfile` with the projects baked in.
- **Smoke test**: starts the image and checks that the asset installer ran, the projects load, Perspective serves them, the startup event imports the UDTs, and the icon library and web files are served.
- **Publish**: on pushes to `main`, publishes the image to `ghcr.io/apollogeddon/ignition-gateway`.

Every tag starts with the Ignition version:

| Tag | Example | Published |
| --- | --- | --- |
| `<ignition version>-main` | `8.3.10-main` | Every push to `main` |
| `<ignition version>-sha-<commit>` | `8.3.10-sha-<full commit SHA>` | Every push to `main` |
| `<ignition version>-<release version>` | `8.3.10-1.0.0` | When the run creates a release |

## Releases

release-please (`.github/release.json`) versions the repository from Conventional Commits. It keeps a release pull request open with the next version and the `CHANGELOG.md` entry, and creates the GitHub release and its `v<version>` tag when that pull request merges.

The image job publishes the release's images in the same run, because a tag that release-please creates with `GITHUB_TOKEN` doesn't start a workflow of its own.

## Documentation site

The [`webpage.yaml`](./workflows/webpage.yaml) workflow checks and deploys the [Astro](https://astro.build/) documentation site in `webpage/`. It runs on pushes to `main` and on manual dispatch, and `ci.yaml` calls it on pull requests:

- **Markdown**: lints every Markdown file in the repository with `markdownlint-cli2`.
- **Website**: calls [forgejs](https://github.com/apollogeddon/forgejs)'s reusable `website.yml`: Gitleaks over the whole repository, OSV-Scanner on the site's dependencies, Biome, the type check and the build. These run on pull requests too, so a broken site fails the pull request. On `main` it also commits any OSV security patches and deploys the site to GitHub Pages.
