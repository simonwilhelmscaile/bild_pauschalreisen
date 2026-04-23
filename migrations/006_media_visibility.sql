-- Daily brand visibility percentages from Peec AI
CREATE TABLE media_visibility (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  brand text NOT NULL,
  date date NOT NULL,
  visibility_pct numeric(5,2) NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE(brand, date)
);
CREATE INDEX idx_media_vis_brand ON media_visibility(brand);
CREATE INDEX idx_media_vis_date ON media_visibility(date DESC);

-- Source domain citation data from Peec AI (per export period)
CREATE TABLE media_source_citations (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  source_domain text NOT NULL,
  domain_type text NOT NULL,
  used_pct numeric(5,2) NOT NULL,
  avg_citations numeric(5,2) NOT NULL,
  period_start date NOT NULL,
  period_end date NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE(source_domain, period_start, period_end)
);
CREATE INDEX idx_media_src_type ON media_source_citations(domain_type);
CREATE INDEX idx_media_src_period ON media_source_citations(period_end DESC);
