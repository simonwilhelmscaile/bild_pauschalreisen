-- Add feedback_history column for storing regeneration feedback
ALTER TABLE blog_articles ADD COLUMN IF NOT EXISTS feedback_history JSONB DEFAULT '[]'::jsonb;

-- Expand status check constraint to include 'regenerating'
ALTER TABLE blog_articles DROP CONSTRAINT IF EXISTS blog_articles_status_check;
ALTER TABLE blog_articles ADD CONSTRAINT blog_articles_status_check
    CHECK (status IN ('pending','generating','completed','failed','regenerating'));
