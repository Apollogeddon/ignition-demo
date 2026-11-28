-- Append an asset's reading: the process timer logs every asset's every five
-- minutes, so the charts built on the seeded 72 hours keep growing.
INSERT INTO asset_reading (asset_id, ts, value)
VALUES (:assetId, date_trunc('second', now()), :value)
ON CONFLICT DO NOTHING
