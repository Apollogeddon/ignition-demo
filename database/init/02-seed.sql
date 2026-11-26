-- Example rows for the project's views: areas, assets, three days of readings
-- and a few events. The readings end when the database is created; the views
-- chart the last 72 hours of whatever is there.

INSERT INTO area (name, description, position) VALUES
    ('North', 'Intake and pumping', 1),
    ('South', 'Treatment',          2),
    ('East',  'Storage',            3);

INSERT INTO asset (id, name, area, kind, online, unit) VALUES
    (1,  'Intake pump 1',     'North', 'pump',   true,  'L/s'),
    (2,  'Intake pump 2',     'North', 'pump',   true,  'L/s'),
    (3,  'Blower 1',          'South', 'blower', true,  'm³/h'),
    (4,  'Dosing pump',       'South', 'pump',   true,  'L/s'),
    (5,  'Mixer',             'South', 'mixer',  true,  'rpm'),
    (6,  'Reservoir level',   'East',  'level',  true,  '%'),
    (7,  'Intake pump 3',     'North', 'pump',   false, 'L/s'),
    (8,  'Intake well level', 'North', 'level',  true,  '%'),
    (9,  'Blower 2',          'South', 'blower', false, 'm³/h'),
    (10, 'Transfer pump 1',   'East',  'pump',   true,  'L/s'),
    (11, 'Transfer pump 2',   'East',  'pump',   true,  'L/s');

-- Every 15 minutes for 72 hours: a daily cycle peaking in the morning and
-- evening, with noise; seeded, so every fresh database gets the same shape.
-- The offline assets went down six hours ago and have read zero since.
SELECT setseed(0.42);

WITH profile (asset_id, base, swing, noise) AS (
    VALUES
        (1,  42.0, 12.0, 2.5),
        (2,  38.0, 10.0, 2.5),
        (3,  1450.0, 260.0, 40.0),
        (4,  1.8,  0.5,  0.1),
        (5,  58.0, 6.0,  1.5),
        (6,  64.0, 14.0, 0.8),
        (7,  35.0, 9.0,  2.5),
        (8,  48.0, 18.0, 1.2),
        (9,  1300.0, 220.0, 40.0),
        (10, 30.0, 11.0, 2.0),
        (11, 27.0, 9.0,  2.0)
),
times AS (
    SELECT generate_series(
        date_trunc('hour', now()) - interval '72 hours',
        date_trunc('hour', now()),
        interval '15 minutes'
    ) AS ts
)
INSERT INTO asset_reading (asset_id, ts, value)
SELECT
    p.asset_id,
    t.ts,
    CASE
        WHEN NOT a.online AND t.ts > date_trunc('hour', now()) - interval '6 hours' THEN 0
        ELSE round((greatest(0,
            p.base
            + p.swing * sin(2 * pi() * extract(epoch FROM t.ts) / 86400.0)
            + 0.4 * p.swing * sin(4 * pi() * extract(epoch FROM t.ts) / 86400.0 + 1.3)
            + p.noise * (random() * 2 - 1)
        ))::numeric, 2)::double precision
    END
FROM profile p
JOIN asset a ON a.id = p.asset_id
CROSS JOIN times t;

INSERT INTO asset_event (asset_id, ts, kind, message, operator) VALUES
    (7, date_trunc('hour', now()) - interval '6 hours',  'status',      'Tripped on motor overload; isolated for inspection', 'system'),
    (9, date_trunc('hour', now()) - interval '30 hours', 'status',      'Taken out of service for a bearing change',          'system'),
    (9, date_trunc('hour', now()) - interval '29 hours', 'note',        'Bearings on order, expected Friday',                 'engineer'),
    (6, date_trunc('hour', now()) - interval '12 hours', 'note',        'Level trending high overnight; transfer pumps on auto', 'operator'),
    (7, date_trunc('hour', now()) - interval '5 hours',  'acknowledge', 'Seen; electrician called out',                       'operator');
