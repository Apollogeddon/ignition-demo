---
title: Database
description: The demo application's schema and seed data.
---

`database/init/` holds the demo application's PostgreSQL schema and seed rows, shared by every environment. PostgreSQL runs the files in name order when it creates an empty database. Both the develop stack and the `platform` OpenTofu module mount this folder at `/docker-entrypoint-initdb.d`, so every environment starts from the same data.

| File | Contents |
| --- | --- |
| `01-schema.sql` | The `area`, `asset`, `asset_reading` and `asset_event` tables |
| `02-seed.sql` | Example areas and assets, three days of readings ending when the database is created, and a few events |

## Schema

```sql
CREATE TABLE area (
    name        text    PRIMARY KEY,
    description text    NOT NULL DEFAULT '',
    position    integer NOT NULL DEFAULT 0      -- display order
);

CREATE TABLE asset (
    id      integer PRIMARY KEY,
    name    text    NOT NULL,
    area    text    REFERENCES area (name),
    kind    text    NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    online  boolean NOT NULL DEFAULT true,      -- reporting or not
    unit    text    NOT NULL DEFAULT ''         -- unit of its readings
);

CREATE TABLE asset_reading (                    -- one value per asset and time
    asset_id integer          NOT NULL REFERENCES asset (id),
    ts       timestamptz      NOT NULL,
    value    double precision NOT NULL,
    PRIMARY KEY (asset_id, ts)
);

CREATE TABLE asset_event (                      -- notes, acknowledgements, status changes
    id       serial      PRIMARY KEY,
    asset_id integer     NOT NULL REFERENCES asset (id),
    ts       timestamptz NOT NULL DEFAULT now(),
    kind     text        NOT NULL CHECK (kind IN ('note', 'acknowledge', 'status')),
    message  text        NOT NULL DEFAULT '',
    operator text        NOT NULL DEFAULT ''
);
```

The seed generates a reading every 15 minutes for the 72 hours before the database is created: a daily cycle with noise, the same on every fresh database. The two offline assets read zero for the last six hours. The views chart the 72 hours up to the latest reading, so the seeded data still charts days later.

An asset's `kind` (`pump`, `blower`, `mixer`, `level`) matches one of the equipment UDTs in the `library` project (see [Projects](../projects/#udt-definitions)).

## Connecting

The gateway reaches the database through the `demo` connection, which the `resources` OpenTofu module creates on 8.3 and the seed (`gateway/seed/seed.json`) creates on 8.1. The `project` project's named queries use that connection, and its `recordEvent` gateway message handler writes operator notes and acknowledgements to `asset_event` (see [Projects](../projects/#the-demo-application)).

> **Note:** the init scripts only run when the database volume is first created, so an existing database keeps its old tables and rows. To reload them locally, reset the develop stack with `docker compose -f develop/docker-compose.yml down -v`.
