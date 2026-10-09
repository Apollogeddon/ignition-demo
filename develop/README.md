# Develop

A local development environment: a gateway and database in Docker (or Podman), built from the same `gateway/Dockerfile` as every other environment, with `projects/library/src` and `projects/project/src` mounted live into the gateway.

```sh
cp develop/.env.example develop/.env        # set the passwords, pick IGNITION_VERSION
docker compose -f develop/docker-compose.yml up -d --build
```

- Gateway: <http://localhost:8088> (`admin` / `IGNITION_ADMIN_PASSWORD`); open the Designer from there.
- Database: `localhost:5432`, database and user `demo` (`DB_PASSWORD`), initialised from `database/init` the first time the volume is created.
- Ignition 8.1 or 8.3: set `IGNITION_VERSION` in `.env` to any 8.1 or 8.3 image tag and rebuild with `up -d --build`. The projects, scripts and UDTs work on both.

## The loop

1. Edit in the Designer (or in an editor: the gateway rescans the project folders every 10 seconds). Changes land in `projects/*/src`.
2. Run the checks in `projects/` (see [`projects/README.md`](../projects/README.md)): ruff, basedpyright, `poe compat` and pytest.
3. Commit. `scripts/setup-git.sh` makes git strip the Designer's noise from `resource.json` files as they are staged.

## Gateway configuration

On 8.3, `config/` applies the cluster's `resources` module to this gateway. It authenticates with `GATEWAY_API_TOKEN` from `.env` (`.env.example` shows how to generate one), which the gateway installs for itself on start:

```sh
set -a; . develop/.env; set +a     # load GATEWAY_API_TOKEN and DB_PASSWORD
cd develop/config
export IGNITION_TOKEN="$GATEWAY_API_TOKEN"
tofu init && tofu apply -var db_password="$DB_PASSWORD"
```

The Ignition provider isn't on a registry; see [`cluster/README.md`](../cluster/README.md#3-config) for installing it from its network mirror.

On 8.1 there is no REST API; the gateway seeds itself from `gateway/seed/seed.json` on start (mounted live from the repository).

## Reset

```sh
docker compose -f develop/docker-compose.yml down        # keep the data volumes
docker compose -f develop/docker-compose.yml down -v     # start from scratch
```
