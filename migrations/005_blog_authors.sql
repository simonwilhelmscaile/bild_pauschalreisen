-- Migration: Blog authors table
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS blog_authors (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  title TEXT DEFAULT '',
  bio TEXT DEFAULT '',
  image_url TEXT DEFAULT '',
  credentials TEXT[] DEFAULT '{}',
  linkedin_url TEXT DEFAULT '',
  twitter_url TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add author_id to blog_articles
ALTER TABLE blog_articles ADD COLUMN IF NOT EXISTS author_id UUID REFERENCES blog_authors(id);

CREATE INDEX IF NOT EXISTS idx_blog_articles_author ON blog_articles(author_id);
