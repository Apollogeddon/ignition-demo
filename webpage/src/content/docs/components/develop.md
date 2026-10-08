---
title: Develop
description: A local gateway and database in Docker Compose, with the projects mounted live.
---

`develop/` runs a gateway and a PostgreSQL database in Docker (or Podman). The gateway is built from the same `gateway/Dockerfile` as every other environment, with `projects/library/src` and `projects/project/src` mounted live into it.

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
| `GATEWAY_HTTP_PORT` / `GATEWAY_HTTPS_PORT` | `8088` / `8043` | Host ports for the gateway |
| `DB_PORT` | `5432` | Host port for the database |
| `GATEWAY_MEMORY_MB` | `1024` | Gateway JVM heap |

## The loop

1. Edit in the Designer, or in an editor: the gateway rescans the project folders every 10 seconds. Changes land in `projects/*/src`.
2. Run the checks: `uv run pytest`, ruff and pyright (see [Projects](../projects/#checks)).
3. Commit. The resource sanitiser strips the Designer's noise from `resource.json` files as they are staged.

## Gateway configuration (8.3)

`develop/config/` applies the cluster's `gateway-config` module to this gateway, so it gets the same database connection and alarm journal as a deployed one:

```sh
cd develop/config
export IGNITION_TOKEN='<name>:<secret>'      # an API key created in the gateway
tofu init && tofu apply -var db_password="$DB_PASSWORD"
```

On 8.1 there is no REST API; create the `demo` database connection in the gateway web UI (PostgreSQL, `jdbc:postgresql://database:5432/demo`).

## Reset

```sh
docker compose -f develop/docker-compose.yml down        # keep the data volumes
docker compose -f develop/docker-compose.yml down -v     # start from scratch
```
