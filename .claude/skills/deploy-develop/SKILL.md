---
name: deploy-develop
description: Bring up the local develop stack (gateway and Postgres in Docker Compose, with the projects mounted live), configure an 8.3 gateway with develop/config, or tear it down. Use when the user asks to start, restart, configure or stop the develop environment.
disable-model-invocation: true
---

Every command runs from the repository root. Compose is `docker compose -f develop/docker-compose.yml`, or `podman compose`.

## Up

1. **Env file.** If `develop/.env` is missing, `cp develop/.env.example develop/.env`. Then ask the user to set the passwords and `IGNITION_VERSION` (8.3.x or 8.1.x). For 8.3 they also set `GATEWAY_API_TOKEN`, which the example shows how to generate. Never read or print `.env`: source it into the shell when needed.
2. **Start.** `docker compose -f develop/docker-compose.yml up -d --build`.
3. **Wait for RUNNING.** The compose healthcheck polls `/StatusPing`:

   ```sh
   until curl -fsS http://localhost:8088/StatusPing | grep -q RUNNING; do sleep 5; done
   ```

   Use `GATEWAY_HTTP_PORT` if `.env` changes it. On a first start, an 8.3 gateway with `GATEWAY_API_TOKEN` restarts itself once after commissioning to grant the key: `docker compose ... logs gateway | grep "restarting the gateway once"`. For about 30s after that, `/data/perspective` returns 503 and the API refuses the key, so wait for RUNNING again before step 4 or any check:

   ```sh
   until [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8088/data/perspective/client/project)" = 200 ]; do sleep 5; done
   ```

4. **8.3 config stage.** It needs the Ignition provider mirror (see `cluster/README.md`, or `/validate`). Then **stop and ask** before the apply:

   ```sh
   set -a; . develop/.env; set +a
   export IGNITION_TOKEN="$GATEWAY_API_TOKEN" TF_VAR_db_password="$DB_PASSWORD"
   tofu -chdir=develop/config init
   tofu -chdir=develop/config plan     # show the user the plan
   tofu -chdir=develop/config apply    # only once the user says so
   ```

   On 8.1 there is no config stage: the gateway seeds itself from `gateway/seed/seed.json`.

5. Report the gateway URL (<http://localhost:8088>, user `admin`) and the database (`localhost:5432`, `demo`). Don't print the passwords.

## Down

- `docker compose -f develop/docker-compose.yml down` keeps the data volumes.
- `down -v` deletes the gateway's and the database's data, and `develop/config`'s state then no longer matches the gateway. Run it only when the user asks for a reset. Afterwards, remove `develop/config/terraform.tfstate*` only with their go-ahead.

## Troubleshooting

- `set it in develop/.env`: a required variable is empty.
- The gateway never turns healthy: `docker compose ... logs gateway`. An image tag that isn't a real `inductiveautomation/ignition` tag fails the build.
- A project change doesn't show: the gateway rescans every 10s. A `resource.json` edited by hand must stay valid JSON, so check it with `scripts/sanitise.py --check`.
- Port in use: change `GATEWAY_HTTP_PORT`/`DB_PORT` in `.env`.
