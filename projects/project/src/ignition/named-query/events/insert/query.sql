-- Record an operator's event against an asset; returns the new row's id and time.
INSERT INTO asset_event (asset_id, kind, message, operator)
VALUES (:assetId, :kind, :message, :operator)
RETURNING id, (extract(epoch FROM ts) * 1000)::bigint AS time
