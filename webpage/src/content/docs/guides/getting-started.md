---
title: Getting started
description: Clone the repository, run a local gateway and make your first change.
---

This guide is for anyone trying the demo for the first time. It gets a gateway running on your machine with the demo projects loaded, then walks through one change from the Designer to a commit.

## Prerequisites

- Docker or Podman with Compose
- [uv](https://docs.astral.sh/uv/), for the script checks and the resource sanitiser
- Node.js and npm, for the commit hooks
- Git

You only need OpenTofu and a Kubernetes cluster to deploy; see [Cluster](../../components/cluster/).

## 1. Clone and enable the sanitiser

```sh
git clone https://github.com/apollogeddon/ignition-demo.git
cd ignition-demo
scripts/setup-git.sh          # once per clone (setup-git.ps1 on Windows)
npm ci                        # installs the git hooks
```

`setup-git.sh` registers a git filter that strips the Designer's timestamps and signatures from `resource.json` files as they are staged. Without it, every Designer save shows up as a change. See [Projects](../../components/projects/#the-resource-sanitiser).

`npm ci` installs lefthook, which lints staged scripts and checks that commit messages follow [Conventional Commits](https://www.conventionalcommits.org/). It also installs [forgejs](https://github.com/apollogeddon/forgejs) from GitHub Packages, so it needs a GitHub token with `read:packages` in your user `~/.npmrc` (`npm config set "//npm.pkg.github.com/:_authToken" "<token>"`).

## 2. Start the develop stack

```sh
cp develop/.env.example develop/.env        # then set the passwords
docker compose -f develop/docker-compose.yml up -d --build
```

This builds the gateway image from `gateway/Dockerfile`, the same image every environment runs, and starts it with a PostgreSQL database initialised from `db/init`.

| Service | Address | Login |
| --- | --- | --- |
| Gateway | <http://localhost:8088> | `admin` / `IGNITION_ADMIN_PASSWORD` |
| Database | `localhost:5432` | database and user `demo` / `DB_PASSWORD` |

> **Tip:** set `IGNITION_VERSION` in `develop/.env` to any 8.1 or 8.3 image tag, then rebuild with `up -d --build`. The projects, scripts and UDTs work on both. The default is 8.3.10.

## 3. Configure the gateway (8.3)

On Ignition 8.3, apply the same gateway configuration the cluster uses, so the local gateway gets the `demo` database connection, alarm journal and the rest.

1. Set `GATEWAY_API_TOKEN` in `develop/.env` (`.env.example` shows how to generate one) and restart the stack with `up -d`. The gateway installs the key for itself on start.
2. Point OpenTofu at the Ignition provider's network mirror: see [Cluster](../../components/cluster/#3-config).
3. Apply the configuration:

   ```sh
   set -a; . develop/.env; set +a     # load GATEWAY_API_TOKEN and DB_PASSWORD
   cd develop/config
   export IGNITION_TOKEN="$GATEWAY_API_TOKEN"
   tofu init && tofu apply -var db_password="$DB_PASSWORD"
   ```

On 8.1 there is nothing to apply: the gateway has no REST API, and seeds the same configuration itself on start from `gateway/seed/seed.json`.

## 4. Make a change

1. Open the Designer from the gateway's home page and edit a view or script. The project folders are mounted live, so the change lands straight in `projects/*/src`.
2. Run the checks:

   ```sh
   cd projects
   uv sync
   uv run ruff format --check . && uv run ruff check .
   uv run basedpyright
   uv run poe compat
   uv run pytest
   ```

3. Commit. The sanitiser keeps the diff to what you actually changed.

## Next steps

- [Architecture](../architecture/): how the image, the chart and OpenTofu divide the work.
- [Development workflow](../workflow/): the edit, check and commit loop in more detail.
- [Cluster](../../components/cluster/): deploy the same image to Kubernetes.
