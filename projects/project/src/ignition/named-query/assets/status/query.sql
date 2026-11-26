-- One row per enabled asset: its area, whether it is online, its latest
-- reading and the time of its latest event (epoch milliseconds, or null).
SELECT
    a.id,
    a.name,
    a.area,
    ar.description AS area_description,
    a.kind,
    a.online,
    a.unit,
    a.capacity,
    r.value,
    (extract(epoch FROM r.ts) * 1000)::bigint AS reading_ms,
    (extract(epoch FROM e.ts) * 1000)::bigint AS event_ms
FROM asset a
LEFT JOIN area ar ON ar.name = a.area
LEFT JOIN LATERAL (
    SELECT value, ts FROM asset_reading WHERE asset_id = a.id ORDER BY ts DESC LIMIT 1
) r ON true
LEFT JOIN LATERAL (
    SELECT max(ts) AS ts FROM asset_event WHERE asset_id = a.id
) e ON true
WHERE a.enabled
ORDER BY ar.position, a.area, a.name
