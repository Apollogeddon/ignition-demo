# GitHub Workflows Documentation

This repository uses GitHub Actions to check the projects and the infrastructure code, build and publish the gateway image, and deploy the documentation site.

## 🏗️ Orchestration: The CI Workflow

The [`ci.yaml`](./workflows/ci.yaml) workflow runs on every pull request and every push to `main`:

1. **Changes**: On a pull request, works out which checks the change needs. Each check runs only when its own files, or `ci.yaml`, changed; a push to `main` runs them all.
2. **Projects, Resources & OpenTofu**: Run in parallel.
3. **Version**: On `main`, opens or updates release-please's release pull request, and creates the release when it merges.
4. **Gateway Image**: After the project and resource checks pass; on `main` it publishes the image, with a release's version when Version created one.
5. **Webpage**: On a pull request, the documentation site's checks and build ([below](#-documentation)).
6. **Auto-merge**: Merges a Dependabot pull request through [forgepy](https://github.com/apollogeddon/forgepy)'s `merge.yml`, once every job above has passed or been skipped.

A new push to a pull request cancels its previous run.

---

## 🧪 Projects

The `projects` job runs [forgepy](https://github.com/apollogeddon/forgepy)'s `testing.yml` on `projects/`, once per Ignition API (8.1 and 8.3), each with that version's [Ignition API stubs](https://pypi.org/project/ignition-api-stubs/) from its uv dependency group:

- **Ruff**: Checks formatting and lints the scripts, with forgepy's Jython 2.7 rules.
- **basedpyright**: Type-checks the scripts against the API stubs.
- **Jython 2.7 compatibility**: vermin fails on syntax, modules or functions Jython 2.7 lacks, and `forgepy check-jython` on the commas after `*args` that it rejects.
- **forgepy sync check**: Fails if forgepy's managed configs under `projects/.forgepy/` are out of date.
- **Pytest**: Runs the unit tests, with mocks for the `system.*` modules.
- **OSV-Scanner**: Reports known vulnerabilities in `uv.lock`; on `main`, the 8.3 job upgrades the vulnerable packages and commits the new lock file.

## 🔍 Resources and Scripts

The `resources` job checks the repository tooling and the project resources:

- **shellcheck**: Lints every shell script in the repository.
- **Sanitiser Tests**: Unit tests for the resource sanitiser.
- **Sanitised Resources**: Fails if a committed `resource.json` still carries the Designer's noise.
- **Asset Installer Tests**: Tests the gateway image's asset installer.
- **Event Scripts**: Fails if the 8.1 gateway event scripts are out of date with their script files.

## 🏔️ OpenTofu and Config Scan

The `tofu` job checks the infrastructure code:

- **Format**: Runs `tofu fmt -check` over `cluster/` and `develop/`.
- **Validate**: Validates the `platform` and `gateway` modules and the k3s `infra` stage.
- **Trivy**: Scans the OpenTofu code, the compose file and the Dockerfile for misconfigurations, failing on high or critical ones. `.trivyignore` lists the accepted ones, with the reason.

## 🐳 Gateway Image

The `image` job builds the gateway image, once per Ignition version (8.1 and 8.3):

- **Build**: Builds `gateway/Dockerfile` with the projects baked in.
- **Smoke Test**: Starts the image and checks the projects load, the icon library and web files are served, and the asset installer ran.
- **Publish**: On pushes to `main`, publishes the image to GHCR. Every tag carries the Ignition version (`8.3.10-main`, `8.3.10-sha-<commit>`), and a release adds its version (`8.3.10-1.2.0`).

## 🏷️ Releases

release-please (`.github/release.json`) versions the repository from Conventional Commits: it keeps a release pull request open with the next version and `CHANGELOG.md`, and creates the release when that pull request merges. The image job publishes the release's images in the same run, as the tag release-please creates with `GITHUB_TOKEN` doesn't start a workflow of its own.

## 📖 Documentation

The [`webpage.yaml`](./workflows/webpage.yaml) workflow manages the [Astro](https://astro.build/)-based documentation site:

- **Markdown**: Lints every Markdown file in the repository with `markdownlint-cli2`.
- **Website**: Calls [forgejs](https://github.com/apollogeddon/forgejs)'s `website.yml`: Gitleaks over the whole repository, OSV-Scanner on the site's dependencies, Biome, the type check and the build, on pull requests too, so a broken site fails the pull request. On `main` it commits any OSV security patches and deploys to **GitHub Pages**.
