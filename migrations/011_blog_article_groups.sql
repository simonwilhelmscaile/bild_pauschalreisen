-- Group articles by topic across languages for hreflang linking
ALTER TABLE blog_articles
ADD COLUMN IF NOT EXISTS article_group_id UUID;

-- Index for finding sibling articles in the same group
CREATE INDEX IF NOT EXISTS idx_blog_articles_group
ON blog_articles (article_group_id)
WHERE article_group_id IS NOT NULL;
