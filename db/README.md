# Database

`init/` holds the demo application's schema and seed rows. PostgreSQL runs the
files in name order when it creates an empty database; both the develop stack and
the `platform` OpenTofu module mount this folder at `/docker-entrypoint-initdb.d`.

The gateway reaches the database through the `demo` connection, which the
`gateway-config` OpenTofu module creates, and the `project` project's named
queries use that connection.
