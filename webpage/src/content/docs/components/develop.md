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

Starting the stack accepts the [Ignition EULA](https://inductiveautomation.com/ignition/license) for this local image: the compose file sets `ACCEPT_IGNITION_EULA: "Y"`, so only start it if you accept it.

| Service | Address | Notes |
| --- | --- | --- |
| Gateway | <http://localhost:8088> | `admin` / `IGNITION_ADMIN_PASSWORD`; open the Designer from here |
| Database | `localhost:5432` | database and user `demo`; initialised from `database/init` the first time the volume is created |

Both publish their ports on 127.0.0.1 only, so the `change-me` passwords in `.env.example` aren't reachable from the network.

## Settings

`develop/.env` (copied from `.env.example`, and ignored by git):

| Variable | Default | Purpose |
| --- | --- | --- |
| `IGNITION_VERSION` | an 8.3 release | Any 8.1 or 8.3 image tag; rebuild with `up -d --build` after changing it |
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
3. Commit. `scripts/setup-git.sh` makes git strip the Designer's noise from `resource.json` files as they are staged (see [Projects](../projects/#the-resource-sanitiser)).

## Gateway resources

**8.3.** `develop/config/` applies the cluster's `resources` module to this gateway, so it gets the same resources as a deployed one. It's required: it creates the `demo` database connection the project's named queries use, the `demo` historian the tag history needs and the alarm journal, and until it's applied the Assets page shows an ERROR in its table. It authenticates with the key from `GATEWAY_API_TOKEN`, which the gateway installs for itself on start (the compose file sets `GATEWAY_API_TOKEN_REQUIRE_TLS=false`, so the gateway takes it over plain HTTP on loopback):

```sh
set -a; . develop/.env; set +a     # load GATEWAY_API_TOKEN and DB_PASSWORD
cd develop/config
export IGNITION_TOKEN="$GATEWAY_API_TOKEN"
tofu init && tofu apply -var db_password="$DB_PASSWORD"
```

The Ignition provider isn't on a registry; see [Cluster](../cluster/#5-config) for installing it from its network mirror.

On its first start with an API key, the gateway restarts once to load it, as the key's grants only apply after commissioning. For about 30 seconds `/data/perspective` and the API answer 503: if `tofu apply` fails with 503, apply again a minute later.

**8.1.** There is no REST API; the gateway seeds itself from `gateway/seed/seed.json` on start (see [Gateway image](../gateway-image/#81-the-seed)). The seed folder is mounted live, so an edit to the spec is applied the next time the project restarts its scripts. A new gateway's seeded alarm journal only starts at its second start: 8.1's journal manager ignores a journal added while it runs, so restart the gateway once (`docker compose -f develop/docker-compose.yml restart gateway`) before relying on the Alarms page's journal.

## Reset

```sh
docker compose -f develop/docker-compose.yml down        # keep the data volumes
docker compose -f develop/docker-compose.yml down -v     # start from scratch
```
