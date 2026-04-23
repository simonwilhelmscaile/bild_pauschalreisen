-- Migration: Article management (review status + comments)
-- Run in Supabase SQL Editor

ALTER TABLE blog_articles ADD COLUMN IF NOT EXISTS review_status TEXT DEFAULT 'draft'
  CHECK (review_status IN ('draft','review','approved','published'));

CREATE TABLE IF NOT EXISTS article_comments (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  article_id UUID NOT NULL REFERENCES blog_articles(id) ON DELETE CASCADE,
  author TEXT NOT NULL DEFAULT 'Reviewer',
  comment_text TEXT NOT NULL,
  selected_text TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_article_comments_article ON article_comments(article_id);
