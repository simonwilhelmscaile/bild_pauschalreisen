-- Add dedicated meta_title column (meta_description already exists)
ALTER TABLE blog_articles ADD COLUMN IF NOT EXISTS meta_title TEXT;

-- Backfill from article_json for existing articles
UPDATE blog_articles
SET meta_title = article_json->>'Meta_Title'
WHERE meta_title IS NULL
  AND article_json IS NOT NULL
  AND article_json->>'Meta_Title' IS NOT NULL;
