# Gateway image

`Dockerfile` builds Ignition with the projects from `projects/` baked in at `/usr/local/bin/ignition/assets/projects`, plus any `.modl` files placed in `modules/`.

```sh
docker build -f gateway/Dockerfile -t ignition-gateway:dev .
docker build -f gateway/Dockerfile --build-arg IGNITION_VERSION=8.1.55 -t ignition-gateway:8.1 .
```

The gateway must be started with these arguments (the `gateway` OpenTofu module and `develop/docker-compose.yml` set them):

```text
-- -Dignition.projects.dir=/usr/local/bin/ignition/assets/projects -Dignition.projects.scanFrequency=60
```

## Why the projects live in the image

- **One source of truth.** The tag a gateway runs fully describes its projects; there is nothing to drift.
- **Redundancy.** Master and Backup run the same image, so they always have the same projects, independent of redundancy sync.
- **Rollback.** Rolling back is deploying the previous tag.

The flip side is that the deployed gateway's projects are read-only in practice: Designer edits there are lost on the next restart. Make changes with the develop stack, where the project folders are mounted live, and commit them.

## What else is in here

| Path | What it is |
| --- | --- |
| `assets/` | Web files (served at `/<file>`), Perspective icon libraries and certificates; `install-assets.sh` puts them in place on every start, for 8.1 and 8.3 |
| `seed/seed.json` | The 8.1 gateway configuration, applied by the startup event |
| `api-token.sh` | Installs the 8.3 API key from `GATEWAY_API_TOKEN` |
| `trial-keepalive.sh` | Keeps an unlicensed trial running when `GATEWAY_TRIAL_KEEPALIVE=true` |
| `tests/` | The installer and API key tests, and the image smoke test (`tests/smoke.sh <image>`) |

The [Gateway Image](https://apollogeddon.github.io/ignition-demo/docs/components/gateway-image/) page describes each in full.
