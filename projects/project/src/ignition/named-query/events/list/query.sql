-- The latest events, newest first: every asset's when assetId is 0, else one's.
SELECT
    e.id,
    (extract(epoch FROM e.ts) * 1000)::bigint AS time,
    e.asset_id,
    a.name AS asset,
    a.area,
    e.kind,
    e.message,
    e.operator
FROM asset_event e
JOIN asset a ON a.id = e.asset_id
WHERE :assetId = 0 OR e.asset_id = :assetId
ORDER BY e.ts DESC, e.id DESC
LIMIT :limit
