-- Hourly readings per area and kind over the 72 hours up to the latest
-- reading: the sum and the mean of each asset's hourly mean, with the hour's
-- day and hour of day (in the database's time zone) for the heatmap.
WITH latest AS (
    SELECT max(ts) AS ts FROM asset_reading
),
hourly AS (
    SELECT date_trunc('hour', r.ts) AS start, a.area, a.kind, r.asset_id, avg(r.value) AS value
    FROM asset_reading r
    JOIN asset a ON a.id = r.asset_id
    CROSS JOIN latest
    WHERE a.enabled AND r.ts > latest.ts - interval '72 hours'
    GROUP BY 1, 2, 3, 4
)
SELECT
    (extract(epoch FROM start) * 1000)::bigint AS time,
    to_char(start, 'Dy DD Mon') AS day,
    extract(hour FROM start)::integer AS hour,
    area,
    kind,
    round(sum(value)::numeric, 2)::double precision AS total,
    round(avg(value)::numeric, 2)::double precision AS mean
FROM hourly
GROUP BY start, area, kind
ORDER BY start, area, kind
