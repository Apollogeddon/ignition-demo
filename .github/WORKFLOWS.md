# GitHub Workflows Documentation

This repository uses GitHub Actions to check the projects and the infrastructure code, build and publish the gateway image, and deploy the documentation site.

## 🏗️ Orchestration: The CI Workflow

The [`ci.yaml`](./workflows/ci.yaml) workflow runs on every pull request, every push to `main` and every `v*` tag:

1. **Projects, Resources & OpenTofu**: Run in parallel.
2. **Gateway Image**: Triggered only after the project and resource checks pass.

---

## 🧪 Projects

The `projects` job checks the project scripts, once per Ignition API (8.1 and 8.3), using that version's [Ignition API stubs](https://pypi.org/project/ignition-api-stubs/):

- **Ruff**: Checks formatting and lints the scripts.
- **Pyright**: Type-checks the scripts against the API stubs.
- **Pytest**: Runs the unit tests, with mocks for the `system.*` modules.

## 🔍 Resources and Scripts

The `resources` job checks the repository tooling and the project resources:

- **Sanitiser Tests**: Unit tests for the resource sanitiser.
- **Sanitised Resources**: Fails if a committed `resource.json` still carries the Designer's noise.
- **Asset Installer Tests**: Tests the gateway image's asset installer.
- **Event Scripts**: Fails if the 8.1 gateway event scripts are out of date with their script files.

## 🏔️ OpenTofu

The `tofu` job checks the infrastructure code:

- **Format**: Runs `tofu fmt -check` over `cluster/` and `develop/`.
- **Validate**: Validates the `platform` and `gateway` modules and the k3s `infra` stage.

## 🐳 Gateway Image

The `image` job builds the gateway image, once per Ignition version (8.1 and 8.3):

- **Build**: Builds `gateway/Dockerfile` with the projects baked in.
- **Smoke Test**: Starts the image and checks the projects load, the icon library and web files are served, and the asset installer ran.
- **Publish**: On pushes to `main` and `v*` tags, publishes the image to GHCR. Every tag carries the Ignition version (e.g. `8.3.10-main`, `8.3.10-sha-<commit>`, `8.3.10-1.2.0`).

## 📖 Documentation

The [`webpage.yaml`](./workflows/webpage.yaml) workflow manages the [Astro](https://astro.build/)-based documentation site:

- **Build**: Installs dependencies and builds the static site located in the `webpage/` directory.
- **Deploy**: Publishes the build artifacts to **GitHub Pages**.
