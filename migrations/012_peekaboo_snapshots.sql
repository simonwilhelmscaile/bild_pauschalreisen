-- Store daily Peekaboo API snapshots for trend visualization
CREATE TABLE IF NOT EXISTS peekaboo_snapshots (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  snapshot_date date NOT NULL,
  brand_score integer NOT NULL DEFAULT 0,
  brand_rank integer NOT NULL DEFAULT 0,
  total_citations integer NOT NULL DEFAULT 0,
  total_chats integer NOT NULL DEFAULT 0,
  competitors jsonb NOT NULL DEFAULT '[]',
  raw_snapshot jsonb,
  created_at timestamptz DEFAULT now(),
  UNIQUE(snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_peekaboo_snap_date
ON peekaboo_snapshots(snapshot_date DESC);
