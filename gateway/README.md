# Gateway image

The gateway image: Ignition 8.1 or 8.3 with the projects from `projects/` baked in at `/usr/local/bin/ignition/assets/projects`, plus web files, icon libraries, certificates and any `.modl` files placed in `modules/`. The develop stack and every cluster environment run this same image.

Build it from the repository root, so the projects are in the build context. `IGNITION_VERSION` selects the base image (default `8.3.10`):

```sh
docker build -f gateway/Dockerfile -t ignition-gateway:dev .
docker build -f gateway/Dockerfile --build-arg IGNITION_VERSION=8.1.55 -t ignition-gateway:8.1 .
```

CI builds and smoke-tests the image for Ignition 8.1.55 and 8.3.10, and publishes it from `main` to `ghcr.io/apollogeddon/ignition-gateway` with tags such as `8.3.10-main`, `8.3.10-sha-<commit>` and, for a release, `8.3.10-1.0.0`.

Start the gateway with these arguments, which point it at the baked-in projects. The `gateway` OpenTofu module and `develop/docker-compose.yml` set them; the develop stack rescans every 10 seconds instead of 60.

```text
-- -Dignition.projects.dir=/usr/local/bin/ignition/assets/projects -Dignition.projects.scanFrequency=60
```

## Why the projects live in the image

- **One source of truth.** The tag a gateway runs fully describes its projects; there is nothing to drift.
- **Redundancy.** Master and Backup run the same image, so they always have the same projects, independent of redundancy sync.
- **Rollback.** Rolling back is deploying the previous tag.

The flip side is that the deployed gateway's projects are read-only in practice: Designer edits there are lost on the next restart. Make changes with the develop stack, where the project folders are mounted live, and commit them.

## Contents

| Path | Contents |
| --- | --- |
| `assets/` | Web files (served at `/<file>`), Perspective icon libraries and certificates; `install-assets.sh` puts them in place on every start, for 8.1 and 8.3 |
| `entrypoint.sh` | The image's entrypoint: runs the asset installer, the API key installer and the trial keepalive, then Ignition's own entrypoint |
| `seed/seed.json` | The 8.1 gateway configuration, applied by the startup event |
| `api-token.sh`, `api_token_grant.py` | Installs the 8.3 API key from `GATEWAY_API_TOKEN` and grants its security level access |
| `modules/` | Third-party modules (`.modl`), copied into the image's `user-lib/modules/` |
| `trial-keepalive.sh` | Keeps an unlicensed trial running when `GATEWAY_TRIAL_KEEPALIVE=true` |
| `tests/` | The installer and API key tests, and the image smoke test (`tests/smoke.sh <image>`) |

The [Gateway Image](https://apollogeddon.github.io/ignition-demo/docs/components/gateway-image/) page describes each in full, including the environment variables the image reads.
