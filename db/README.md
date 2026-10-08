# Database

The demo application's PostgreSQL schema and seed data, shared by every environment.

`init/` holds the SQL files. PostgreSQL runs them in name order when it creates an empty database; both the develop stack and the `platform` OpenTofu module mount this folder at `/docker-entrypoint-initdb.d`.

| File | Contents |
| --- | --- |
| `init/01-schema.sql` | The `area` and `asset` tables |
| `init/02-seed.sql` | Example areas and assets |

The gateway reaches the database through the `demo` connection, which the `gateway-config` OpenTofu module creates on 8.3 and the seed (`gateway/seed/seed.json`) creates on 8.1. The `project` project's named queries use that connection.

The init scripts only run when the database volume is first created. To reload them locally, reset the develop stack with `docker compose -f develop/docker-compose.yml down -v`.
