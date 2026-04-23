-- Add publish status tracking to blog_articles
ALTER TABLE blog_articles
  ADD COLUMN IF NOT EXISTS publish_status TEXT NOT NULL DEFAULT 'unpublished',
  ADD COLUMN IF NOT EXISTS publish_date TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS publish_url TEXT;

-- Constraint for valid values
ALTER TABLE blog_articles
  ADD CONSTRAINT blog_articles_publish_status_check
  CHECK (publish_status IN ('unpublished', 'scheduled', 'published'));
