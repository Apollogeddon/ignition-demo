-- One asset's readings over the 72 hours up to its latest one.
SELECT (extract(epoch FROM r.ts) * 1000)::bigint AS time, r.value
FROM asset_reading r
WHERE r.asset_id = :assetId
  AND r.ts > (SELECT max(ts) FROM asset_reading WHERE asset_id = :assetId) - interval '72 hours'
ORDER BY r.ts
