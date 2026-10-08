<br />
<div align="center">
  <a href="https://apollogeddon.github.io/ignition-demo">
    <img src="../webpage/public/favicon.png" alt="Logo" width="100" height="100">
  </a>
  <h3 align="center">Ignition Demo</h3>
  <p align="center">
    A best-practice template for running Inductive Automation Ignition as code.
    <br />
    <a href="https://apollogeddon.github.io/ignition-demo"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/apollogeddon/ignition-demo/issues">Report Bug</a>
    ·
    <a href="https://github.com/apollogeddon/ignition-demo/issues">Request Feature</a>
  </p>
</div>

## 🚀 Overview

A template for running Ignition 8.1 and 8.3 as code: the gateway, its configuration and its projects all come from this repository, and every environment is built the same way. It brings together the [Ignition Helm charts](https://github.com/apollogeddon/ignition-helm) and the [Ignition Terraform provider](https://github.com/apollogeddon/ignition-tfpl).

## ✨ Features

- **Projects as Code**: Each Ignition project lives in `projects/` as the files the Designer writes. A sanitiser strips the Designer's noise (timestamps, actors, signatures) so diffs show only real changes.
- **Tested Scripts**: Project scripts are formatted, linted, type-checked and unit tested under Python 3.12 against the Ignition API stubs, for both 8.1 and 8.3.
- **Immutable Gateway Image**: `gateway/` bakes the projects into the image, so shipping a project means shipping a new image tag, and both gateways in a redundant pair run the same code.
- **Platform as Code**: `cluster/` uses OpenTofu to install the `ignition-failover` chart with redundancy, TLS and active routing, plus its database.
- **Gateway Configuration**: `cluster/` also configures the running gateway through its REST API with the Ignition provider: database connections, alarm journals and so on.
- **One Owner per Setting**: The image, the chart and OpenTofu each own a distinct set of settings, so nothing fights over them.

## 📦 Installation

### Prerequisites

- **Docker** or **Podman** with Compose, for the develop stack
- **uv**, for the project checks
- **OpenTofu** (v1.8+) and a Kubernetes cluster, to deploy

### Setup

Once per clone, enable the resource sanitiser:

```sh
scripts/setup-git.sh
```

## 🛠️ Usage

### Local Gateway

Run a gateway and database locally, with the projects mounted live:

```sh
cp develop/.env.example develop/.env
docker compose -f develop/docker-compose.yml up -d --build
# Gateway: http://localhost:8088
```

### Checks

```sh
cd projects
uv sync
uv run ruff format --check . && uv run ruff check .
uv run pyright
uv run pytest
```

### Deploy

Each environment is applied in two stages: `infra` (the platform and the gateway), then `config` (the gateway's configuration). See [`cluster/`](../cluster/README.md) for the k3s reference environment.

## 🗂️ Layout

| Path | What it holds |
| :--- | :--- |
| `projects/library/` | An inheritable project: shared scripts, styles and views |
| `projects/project/` | The application project; inherits from `library` |
| `gateway/` | The gateway image: Ignition plus the projects |
| `db/` | The demo database's schema and seed data |
| `cluster/modules/` | OpenTofu modules: `platform`, `gateway`, `gateway-config` |
| `cluster/environments/` | One root module per environment (`k3s` is the reference) |
| `develop/` | Docker Compose for local development, with the projects mounted live |
| `scripts/` | Repository tooling: the resource sanitiser and git setup |

## 🧩 Who Owns What

| Owner | Owns |
| :--- | :--- |
| The gateway image | Project contents (views, scripts, named queries) |
| The Helm chart | Redundancy, the Gateway Network, certificates, pod security |
| OpenTofu (`gateway-config`) | Gateway resources: connections, providers, users, alarming |

Projects are deliberately not managed through the REST API: the image is their single source, so a gateway never drifts from the tag it runs.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
