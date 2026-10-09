---
title: Develop
description: A local gateway and database in Docker Compose, with the projects mounted live.
---

`develop/` is the local development environment: a gateway and a PostgreSQL database in Docker (or Podman). The gateway is built from the same `gateway/Dockerfile` as every other environment, with `projects/library/src` and `projects/project/src` mounted live into it.

## Starting

```sh
cp develop/.env.example develop/.env        # set the passwords, pick IGNITION_VERSION
docker compose -f develop/docker-compose.yml up -d --build
```

| Service | Address | Notes |
| --- | --- | --- |
| Gateway | <http://localhost:8088> | `admin` / `IGNITION_ADMIN_PASSWORD`; open the Designer from here |
| Database | `localhost:5432` | database and user `demo`; initialised from `db/init` the first time the volume is created |

## Settings

`develop/.env` (copied from `.env.example`, and ignored by git):

| Variable | Default | Purpose |
| --- | --- | --- |
| `IGNITION_VERSION` | `8.3.10` | Any 8.1 or 8.3 image tag; rebuild with `up -d --build` after changing it |
| `IGNITION_ADMIN_PASSWORD` | `change-me` | Gateway admin password |
| `DB_PASSWORD` | `change-me` | Database password for the `demo` user |
| `DEMO_USERS_PASSWORD` | `change-me` | 8.1: password of the seeded `operator` and `engineer` users |
| `GATEWAY_API_TOKEN` | empty | 8.3: API key for `develop/config`, as `<name>:<secret>` (see `.env.example` for generating one); empty installs none |
| `GATEWAY_HTTP_PORT` / `GATEWAY_HTTPS_PORT` | `8088` / `8043` | Host ports for the gateway |
| `DB_PORT` | `5432` | Host port for the database |
| `GATEWAY_MEMORY_MB` | `1024` | Gateway JVM heap |

## The loop

1. Edit in the Designer, or in an editor: the gateway rescans the project folders every 10 seconds. Changes land in `projects/*/src`.
2. Run the checks in `projects/`: ruff, basedpyright, `poe compat` and pytest (see [Projects](../projects/#checks)).
3. Commit. The resource sanitiser strips the Designer's noise from `resource.json` files as they are staged.

## Gateway configuration

**8.3.** `develop/config/` applies the cluster's `gateway-config` module to this gateway, so it gets the same configuration as a deployed one. It authenticates with the key from `GATEWAY_API_TOKEN`, which the gateway installs for itself on start:

```sh
set -a; . develop/.env; set +a     # load GATEWAY_API_TOKEN and DB_PASSWORD
cd develop/config
export IGNITION_TOKEN="$GATEWAY_API_TOKEN"
tofu init && tofu apply -var db_password="$DB_PASSWORD"
```

The Ignition provider isn't on a registry; see [Cluster](../cluster/#3-config) for installing it from its network mirror.

**8.1.** There is no REST API; the gateway seeds itself from `gateway/seed/seed.json` on start (see [Gateway image](../gateway-image/#81-the-seed)). The seed folder is mounted live, so an edit to the spec is applied the next time the project restarts its scripts.

## Reset

```sh
docker compose -f develop/docker-compose.yml down        # keep the data volumes
docker compose -f develop/docker-compose.yml down -v     # start from scratch
```
