-- Blog articles generated from content opportunities
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS blog_articles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source_item_id UUID REFERENCES social_items(id) ON DELETE SET NULL,
    keyword TEXT NOT NULL,
    headline TEXT,
    meta_description TEXT,
    article_html TEXT,
    article_json JSONB,
    language TEXT DEFAULT 'de',
    word_count INTEGER,
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending','generating','completed','failed')),
    error_message TEXT,
    social_context JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_blog_articles_source_item
    ON blog_articles(source_item_id) WHERE source_item_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_blog_articles_status ON blog_articles(status);

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION update_blog_articles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER blog_articles_updated_at
    BEFORE UPDATE ON blog_articles
    FOR EACH ROW
    EXECUTE FUNCTION update_blog_articles_updated_at();
