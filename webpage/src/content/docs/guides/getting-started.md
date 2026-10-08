---
title: Getting Started
description: Clone the template, run a local gateway and make your first change.
---

This guide gets a gateway running on your machine with the demo projects loaded, then walks through one change from the Designer to a commit.

## Prerequisites

- **Docker** (or Podman) with Compose
- **uv**, for the script checks and the resource sanitiser
- **Git**

OpenTofu and a Kubernetes cluster are only needed to deploy; see [Cluster](../../components/cluster/).

## 1. Clone and enable the sanitiser

```sh
git clone https://github.com/apollogeddon/ignition-demo.git
cd ignition-demo
scripts/setup-git.sh          # once per clone (setup-git.ps1 on Windows)
```

`setup-git.sh` registers a git filter that strips the Designer's timestamps and signatures from `resource.json` files as they are staged. Without it, every Designer save shows up as a change. See [Projects](../../components/projects/#the-resource-sanitiser).

## 2. Start the develop stack

```sh
cp develop/.env.example develop/.env        # set the passwords
docker compose -f develop/docker-compose.yml up -d --build
```

This builds the gateway image from `gateway/Dockerfile`, the same image every environment runs, and starts it with a PostgreSQL database initialised from `db/init`.

| Service | Address | Login |
| --- | --- | --- |
| Gateway | <http://localhost:8088> | `admin` / `IGNITION_ADMIN_PASSWORD` |
| Database | `localhost:5432` | database and user `demo` / `DB_PASSWORD` |

> **Tip:** set `IGNITION_VERSION` in `develop/.env` to run any 8.1 or 8.3 image tag, then rebuild with `up -d --build`. The projects, scripts and UDTs work on both.

## 3. Configure the gateway (8.3)

On Ignition 8.3, apply the same gateway configuration the cluster uses, so the local gateway gets the `demo` database connection and alarm journal:

```sh
cd develop/config
export IGNITION_TOKEN='<name>:<secret>'      # an API key created in the gateway
tofu init && tofu apply -var db_password="$DB_PASSWORD"
```

On 8.1 there is no REST API, so create the `demo` database connection in the gateway web UI instead (PostgreSQL, `jdbc:postgresql://database:5432/demo`).

## 4. Make a change

1. Open the Designer from the gateway's home page and edit a view or script. The project folders are mounted live, so the change lands straight in `projects/*/src`.
2. Run the checks:

   ```sh
   cd projects
   uv sync
   uv run ruff format --check . && uv run ruff check .
   uv run pyright
   uv run pytest
   ```

3. Commit. The sanitiser keeps the diff to what you actually changed.

## Next steps

- [Architecture](../architecture/): how the image, the chart and OpenTofu divide the work.
- [Development Workflow](../workflow/): the edit, check and commit loop in more detail.
- [Cluster](../../components/cluster/): deploy the same image to Kubernetes.
