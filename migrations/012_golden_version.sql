-- Migration: 012_golden_version.sql
-- Add golden_version column to blog_articles for marking approved baseline versions.
-- golden_version stores a self-contained snapshot: {version, marked_at, marked_by, article_html, article_json, word_count}

ALTER TABLE blog_articles ADD COLUMN IF NOT EXISTS golden_version JSONB DEFAULT NULL;

COMMENT ON COLUMN blog_articles.golden_version IS 'Self-contained snapshot of the reviewer-approved baseline version';
