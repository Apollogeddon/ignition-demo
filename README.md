<br />
<div align="center">
  <a href="https://apollogeddon.github.io/ignition-demo">
    <img src="webpage/public/favicon.png" alt="Logo" width="100" height="100">
  </a>
  <h3 align="center">Ignition Demo</h3>
  <p align="center">
    A reference setup for running Inductive Automation's Ignition as code.
    <br />
    <a href="https://apollogeddon.github.io/ignition-demo"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/apollogeddon/ignition-demo/issues">Report Bug</a>
    ·
    <a href="https://github.com/apollogeddon/ignition-demo/issues">Request Feature</a>
  </p>
</div>

## Overview

Ignition Demo is a reference repository for teams that want to run Ignition 8.1 or 8.3 as code. The gateway, its configuration and its projects all come from this repository, so every environment is built the same way. It brings together the [Ignition Helm charts](https://github.com/apollogeddon/ignition-helm) and the [Ignition Terraform provider](https://github.com/apollogeddon/ignition-tfpl).

## Features

- **Projects as code.** Each Ignition project lives in `projects/` as the files the Designer writes. A git filter strips the Designer's noise (timestamps, actors, signatures) so diffs show only real changes.
- **Tested scripts.** Project scripts are formatted, linted, type-checked, checked for Jython 2.7 compatibility and unit tested under Python 3.12 against the Ignition API stubs, for both 8.1 and 8.3.
- **Immutable gateway image.** `gateway/` bakes the projects into the image, so shipping a project means shipping a new image tag, and both gateways in a redundant pair run the same code.
- **Platform as code.** `cluster/` uses OpenTofu to install the `ignition-failover` Helm chart with redundancy, TLS and active routing, plus its database.
- **Gateway configuration as code.** On 8.3, `cluster/` configures the running gateway through its REST API with the Ignition provider: database connections, alarm journals, user sources and more. On 8.1, the gateway seeds the same configuration itself on start.
- **One owner per setting.** The image, the chart and OpenTofu each own a distinct set of settings, so nothing is managed from two places.

## Prerequisites

- Docker or Podman with Compose, for the local develop stack
- [uv](https://docs.astral.sh/uv/), for the script checks and the resource sanitiser
- Node.js and npm, for the commit hooks
- OpenTofu 1.8 or later and a Kubernetes cluster, to deploy

## Setup

Once per clone, enable the resource sanitiser and install the commit hooks:

```sh
scripts/setup-git.sh    # setup-git.ps1 on Windows
npm ci
```

`npm ci` installs lefthook, which lints staged Python scripts and shell scripts and checks that commit messages follow Conventional Commits. It also installs `@apollogeddon/forgejs` from GitHub Packages, which needs a GitHub token with `read:packages` in your user `~/.npmrc`:

```sh
npm config set "//npm.pkg.github.com/:_authToken" "<token>"
```

## Quick start

Run a gateway and database locally, with the projects mounted live:

```sh
cp develop/.env.example develop/.env    # then set the passwords
docker compose -f develop/docker-compose.yml up -d --build
```

The gateway is then at <http://localhost:8088>. See [`develop/`](develop/README.md) for the settings and the edit loop.

Run the script checks:

```sh
cd projects
uv sync
uv run ruff format --check . && uv run ruff check .
uv run basedpyright
uv run poe compat
uv run pytest
```

See [`projects/`](projects/README.md) for the script conventions and every task.

## Gateway images

CI publishes the gateway image to `ghcr.io/apollogeddon/ignition-gateway` for Ignition 8.1.55 and 8.3.10. Every tag starts with the Ignition version:

| Tag | Published |
| --- | --- |
| `<ignition version>-main` | On every push to `main`, e.g. `8.3.10-main` |
| `<ignition version>-sha-<commit>` | On every push to `main`, for the full commit SHA |
| `<ignition version>-<release version>` | For each release, e.g. `8.3.10-1.0.0` |

## Deploy

Each environment is applied in two stages: `infra` (the platform and the gateway), then `config` (the gateway's configuration). See [`cluster/`](cluster/README.md) for the k3s reference environment.

## Repository layout

| Path | Contents |
| --- | --- |
| `projects/library/` | An inheritable project: shared scripts, styles, views and UDT definitions |
| `projects/project/` | The application project; inherits from `library` |
| `gateway/` | The gateway image: Ignition plus the projects |
| `database/` | The demo database's schema and seed data |
| `cluster/modules/` | OpenTofu modules: `platform`, `gateway`, `resources` |
| `cluster/environments/` | One root module per environment (`k3s` is the reference) |
| `develop/` | Docker Compose for local development, with the projects mounted live |
| `scripts/` | Repository tooling: the resource sanitiser, git setup and the 8.1 event script generator |
| `webpage/` | The documentation site (Astro) |

## Who owns what

| Owner | Owns |
| --- | --- |
| The gateway image | Project contents: views, scripts, named queries, UDT definitions |
| The Helm chart | Redundancy, the Gateway Network, certificates, Pod Security |
| OpenTofu (`resources`) | Gateway resources: connections, providers, users, alarming |

Projects are deliberately not managed through the REST API. The image is their single source, so a gateway never drifts from the tag it runs.

## Documentation

The [documentation site](https://apollogeddon.github.io/ignition-demo) covers the architecture, the development workflow and each component in detail. CI and release automation are described in [`.github/WORKFLOWS.md`](.github/WORKFLOWS.md), and security reporting in [`.github/SECURITY.md`](.github/SECURITY.md).

## Contributing

Pull requests are welcome. Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat: ...`, `fix(webpage): ...`), which the commit hook checks; releases and `CHANGELOG.md` are generated from them.

## License

Released under the [MIT License](LICENSE).

Ignition is a trademark of Inductive Automation. This project is not affiliated with or endorsed by Inductive Automation.
