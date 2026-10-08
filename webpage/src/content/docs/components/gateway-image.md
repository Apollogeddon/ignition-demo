---
title: Gateway Image
description: Ignition with the projects baked in, built once and run everywhere.
---

`gateway/Dockerfile` builds Ignition with the projects from `projects/` baked in at `/usr/local/bin/ignition/assets/projects`, plus any `.modl` files placed in `gateway/modules/`. The develop stack and every cluster environment run this same image.

## Building

Build from the repository root, so the projects are in the build context:

```sh
docker build -f gateway/Dockerfile -t ignition-gateway:dev .
docker build -f gateway/Dockerfile --build-arg IGNITION_VERSION=8.3.9 -t ignition-gateway:dev .
```

`IGNITION_VERSION` selects the base image; any 8.1 or 8.3 tag works. CI builds the image on every pull request and publishes it to GHCR from `main` and `v*` tags.

## Gateway arguments

The gateway must be started with these arguments, which point it at the baked-in projects. The `gateway` OpenTofu module and `develop/docker-compose.yml` set them:

```text
-- -Dignition.projects.dir=/usr/local/bin/ignition/assets/projects -Dignition.projects.scanFrequency=60
```

## Why the projects live in the image

- **One source of truth.** The tag a gateway runs fully describes its projects; there is nothing to drift.
- **Redundancy.** Master and Backup run the same image, so they always have the same projects, independent of redundancy sync.
- **Rollback.** Rolling back is deploying the previous tag.

> **Note:** a deployed gateway's projects are read-only in practice. Designer edits made there are lost on the next restart. Make changes with the [develop stack](../develop/), where the project folders are mounted live, and commit them.

## Modules

Third-party modules (`.modl` files) placed in `gateway/modules/` are copied into the image's `user-lib/modules/`, so they are installed the same way in every environment.
