# Database

The demo application's PostgreSQL schema and seed data, shared by every environment.

`init/` holds the SQL files. PostgreSQL runs them in name order when it creates an empty database; both the develop stack and the `platform` OpenTofu module mount this folder at `/docker-entrypoint-initdb.d`.

| File | Contents |
| --- | --- |
| `init/01-schema.sql` | The `area`, `asset`, `asset_reading` and `asset_event` tables |
| `init/02-seed.sql` | Example areas and assets, three days of readings ending when the database is created, and a few events |

The gateway reaches the database through the `demo` connection, which the `resources` OpenTofu module creates on 8.3 and the seed (`gateway/seed/seed.json`) creates on 8.1. The `project` project's named queries use that connection: its views chart the last 72 hours of readings up to the latest one, so the seeded data still charts days later, and its `recordEvent` gateway message handler writes operator notes and acknowledgements to `asset_event`.

The init scripts only run when the database volume is first created: a database created before a change to them keeps its old tables and rows. To reload them locally, reset the develop stack with `docker compose -f develop/docker-compose.yml down -v`.
