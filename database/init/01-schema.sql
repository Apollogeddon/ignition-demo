-- The demo application's tables. PostgreSQL runs the files in this folder, in
-- name order, when it initialises an empty database (develop/ and the platform
-- module mount it at /docker-entrypoint-initdb.d).

CREATE TABLE area (
    name        text    PRIMARY KEY,
    description text    NOT NULL DEFAULT '',
    -- display order, upstream first
    position    integer NOT NULL DEFAULT 0
);

CREATE TABLE asset (
    id      integer PRIMARY KEY,
    name    text    NOT NULL,
    area    text    REFERENCES area (name),
    kind    text    NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    -- whether the asset is reporting; the overview counts online and offline
    online  boolean NOT NULL DEFAULT true,
    -- unit of the asset's readings (asset_reading.value)
    unit    text    NOT NULL DEFAULT ''
);

CREATE INDEX asset_area ON asset (area);

-- One measured value per asset and time: a pump's flow, a blower's air flow,
-- a mixer's speed or a tank's level, in the asset's unit.
CREATE TABLE asset_reading (
    asset_id integer          NOT NULL REFERENCES asset (id),
    ts       timestamptz      NOT NULL,
    value    double precision NOT NULL,
    PRIMARY KEY (asset_id, ts)
);

CREATE INDEX asset_reading_ts ON asset_reading (ts);

-- What happened to an asset: operator notes and acknowledgements (written by
-- the project's gateway message handler), and status changes.
CREATE TABLE asset_event (
    id       serial      PRIMARY KEY,
    asset_id integer     NOT NULL REFERENCES asset (id),
    ts       timestamptz NOT NULL DEFAULT now(),
    kind     text        NOT NULL CHECK (kind IN ('note', 'acknowledge', 'status')),
    message  text        NOT NULL DEFAULT '',
    operator text        NOT NULL DEFAULT ''
);

CREATE INDEX asset_event_ts ON asset_event (ts DESC);
CREATE INDEX asset_event_asset ON asset_event (asset_id, ts DESC);
