---
title: Gateway image
description: Ignition with the projects baked in, built once and run everywhere.
---

`gateway/Dockerfile` builds Ignition with the projects from `projects/` baked in at `/usr/local/bin/ignition/assets/projects`, plus web files, icon libraries, certificates and modules from `gateway/`. The develop stack and every cluster environment run this same image, on Ignition 8.1 or 8.3.

## Building

Build from the repository root, so the projects are in the build context:

```sh
docker build -f gateway/Dockerfile -t ignition-gateway:dev .
docker build -f gateway/Dockerfile --build-arg IGNITION_VERSION=8.1.55 -t ignition-gateway:8.1 .
```

`IGNITION_VERSION` selects the base image (default `8.3.10`); any 8.1 or 8.3 tag works.

## Published images

CI builds the image for Ignition 8.1.55 and 8.3.10 and runs `gateway/tests/smoke.sh` against each: the asset installer ran, the projects load and Perspective serves them, the startup event imports the UDTs, and the icon library and web files are served. On pushes to `main` it publishes the images to `ghcr.io/apollogeddon/ignition-gateway`. Every tag starts with the Ignition version:

| Tag | Published |
| --- | --- |
| `<ignition version>-main`, e.g. `8.3.10-main` | Every push to `main` |
| `<ignition version>-sha-<commit>` | Every push to `main`, with the full commit SHA |
| `<ignition version>-<release version>`, e.g. `8.3.10-1.0.0` | Each release |

## Gateway arguments

Start the gateway with these arguments, which point it at the baked-in projects. The `gateway` OpenTofu module and `develop/docker-compose.yml` set them; the develop stack rescans every 10 seconds instead of 60:

```text
-- -Dignition.projects.dir=/usr/local/bin/ignition/assets/projects -Dignition.projects.scanFrequency=60
```

## Why the projects live in the image

- **One source of truth.** The tag a gateway runs fully describes its projects; there is nothing to drift.
- **Redundancy.** Master and Backup run the same image, so they always have the same projects, independent of redundancy sync.
- **Rollback.** Rolling back is deploying the previous tag.

Ignition 8.1 needs the projects folder to be writable (it keeps a `.resources` cache next to the projects); the image's folder is.

> **Note:** a deployed gateway's projects are read-only in practice. Designer edits made there are lost on the next restart. Make changes with the [develop stack](../develop/), where the project folders are mounted live, and commit them.

## Modules

Third-party modules (`.modl` files) placed in `gateway/modules/` are copied into the image's `user-lib/modules/`, so they are installed the same way in every environment.

## Assets

Files in `gateway/assets/` are part of the image; `gateway/install-assets.sh` puts the ones that belong in the data volume into place on every start, because the data volume outlives the image. They are copied, not linked (a dangling link in `data/` breaks redundancy state transfer), and an asset a newer image no longer has is removed again.

| Asset | Ignition 8.1 | Ignition 8.3 |
| --- | --- | --- |
| `web/*` | served at `/<file>` from `webserver/webapps/main` | the same |
| `icons/<library>.svg` (icon sprite) | `data/modules/com.inductiveautomation.perspective/icons/` | an icon library resource in the `external` config collection |
| `certs/*.crt`, `*.cer`, `*.pem` | `data/certificates/supplemental/` | the same |

Views reference an icon as `<library>/<icon id>`, e.g. `equipment/pump`, and a web file as `/<file>`, e.g. `/operator-guide.html`.

## Gateway configuration from the environment

How a gateway gets its configuration depends on its version, and every input is an environment variable, so secrets stay out of the image:

| Variable | Version | Purpose |
| --- | --- | --- |
| `GATEWAY_API_TOKEN` | 8.3 | `<name>:<secret>` API key the Ignition provider authenticates with; the secret is base64url of 32 random bytes |
| `GATEWAY_API_TOKEN_LEVEL` | 8.3 | Security level the key carries (default `Api`) |
| `GATEWAY_DB_DEMO_URL`, `_USER`, `_PASSWORD`, `DEMO_USERS_PASSWORD` | 8.1 | Values for the seed spec |
| `GATEWAY_TRIAL_KEEPALIVE` | both | `true` keeps an unlicensed gateway's trial running (demo and trial environments only) |

### 8.3: an API key from the start

`gateway/api-token.sh` installs the key before every start, so OpenTofu can configure the gateway with no key created by hand. It writes the key's hash (never the secret) and its security level to the `external` config collection, and grants that level read and write access in the `core` collection's security properties, adding to what is there rather than replacing it. The gateway only creates `core` when it commissions, so on the very first start the grant is added after commissioning and the gateway restarts once; later starts need no restart.

### 8.1: the seed

8.1 has no configuration API, so the `project` startup event applies `gateway/seed/seed.json` (see `library.seed`). Each item is created only if it is missing: a fresh gateway gets the whole configuration, and changes made later in the gateway are kept, as with a first-boot backup restore, but reviewable as text. Values can read the environment with `${NAME}` or `${NAME:-default}`.

| Section | Creates |
| --- | --- |
| `securityLevels` | Top-level security level trees |
| `databases` | Database connections |
| `userSources` | User sources, with their roles and users |
| `identityProviders` | Ignition identity providers backed by a user source |
| `alarmJournals` | Alarm journals |
| `auditProfiles` | Audit profiles |
| `emailProfiles`, `alarmNotificationProfiles` | SMTP profiles and the Alarm Notification module's profiles |
| `gateway` | System settings, e.g. the gateway's audit profile (applied when they differ) |

8.3 ignores the seed; there the `gateway-config` OpenTofu module configures the gateway through its REST API instead (see [Cluster](../cluster/)).

## Trial keepalive

With `GATEWAY_TRIAL_KEEPALIVE=true`, `gateway/trial-keepalive.sh` runs beside the gateway and resets its two-hour trial once it has expired (8.1 only accepts a reset then): with the API key on 8.3, by signing in as the gateway admin on 8.1. It sleeps until the predicted expiry, so it makes one call per trial period. Each gateway keeps its own trial clock, and each container runs its own keepalive, so a redundant pair is covered. Never enable it on a licensed gateway.
