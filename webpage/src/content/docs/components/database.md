---
title: Database
description: The demo application's schema and seed data.
---

`db/init/` holds the demo application's PostgreSQL schema and seed rows, shared by every environment. PostgreSQL runs the files in name order when it creates an empty database. Both the develop stack and the `platform` OpenTofu module mount this folder at `/docker-entrypoint-initdb.d`, so every environment starts from the same data.

| File | Contents |
| --- | --- |
| `01-schema.sql` | The `area` and `asset` tables |
| `02-seed.sql` | Example areas and assets for the asset summary view |

## Schema

```sql
CREATE TABLE area (
    name        text PRIMARY KEY,
    description text NOT NULL DEFAULT ''
);

CREATE TABLE asset (
    id      integer PRIMARY KEY,
    name    text    NOT NULL,
    area    text    REFERENCES area (name),
    kind    text    NOT NULL,
    enabled boolean NOT NULL DEFAULT true
);
```

An asset's `kind` (`pump`, `blower`, `mixer`, `level`) matches one of the equipment UDTs in the `library` project (see [Projects](../projects/#udt-definitions)).

## Connecting

The gateway reaches the database through the `demo` connection, which the `gateway-config` OpenTofu module creates on 8.3 and the seed (`gateway/seed/seed.json`) creates on 8.1. The `project` project's named queries use that connection.

> **Note:** the init scripts only run when the database volume is first created. To reload them locally, reset the develop stack with `docker compose -f develop/docker-compose.yml down -v`.
