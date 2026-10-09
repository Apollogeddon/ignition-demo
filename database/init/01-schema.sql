-- The demo application's tables. PostgreSQL runs the files in this folder, in
-- name order, when it initialises an empty database (develop/ and the platform
-- module mount it at /docker-entrypoint-initdb.d).

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

CREATE INDEX asset_area ON asset (area);
