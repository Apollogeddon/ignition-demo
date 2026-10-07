# Gateway image

`Dockerfile` builds Ignition with the projects from `projects/` baked in at
`/usr/local/bin/ignition/assets/projects`, plus any `.modl` files placed in
`modules/`.

```sh
docker build -f gateway/Dockerfile -t ignition-gateway:dev .
docker build -f gateway/Dockerfile --build-arg IGNITION_VERSION=8.3.9 -t ignition-gateway:dev .
```

The gateway must be started with these arguments (the `gateway` OpenTofu
module and `local/docker-compose.yml` set them):

```
-- -Dignition.projects.dir=/usr/local/bin/ignition/assets/projects -Dignition.projects.scanFrequency=60
```

## Why the projects live in the image

- **One source of truth.** The tag a gateway runs fully describes its projects;
  there is nothing to drift.
- **Redundancy.** Master and Backup run the same image, so they always have the
  same projects, independent of redundancy sync.
- **Rollback.** Rolling back is deploying the previous tag.

The flip side is that the deployed gateway's projects are read-only in
practice: Designer edits there are lost on the next restart. Make changes with
the local stack, where the project folders are mounted live, and commit them.
