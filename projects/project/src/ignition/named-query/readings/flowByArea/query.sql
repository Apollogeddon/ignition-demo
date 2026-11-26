-- Hourly pumped flow per area (L/s, the sum of each pump's hourly mean) over
-- the 72 hours up to the latest reading, so seeded data still charts later.
WITH latest AS (
    SELECT max(ts) AS ts FROM asset_reading
),
hourly AS (
    SELECT date_trunc('hour', r.ts) AS hour, a.area, r.asset_id, avg(r.value) AS flow
    FROM asset_reading r
    JOIN asset a ON a.id = r.asset_id
    CROSS JOIN latest
    WHERE a.enabled AND a.kind = 'pump' AND r.ts > latest.ts - interval '72 hours'
    GROUP BY 1, 2, 3
)
SELECT
    (extract(epoch FROM hour) * 1000)::bigint AS time,
    area,
    round(sum(flow)::numeric, 1)::double precision AS flow
FROM hourly
GROUP BY hour, area
ORDER BY hour, area
