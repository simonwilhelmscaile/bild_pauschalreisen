-- Migration 001: Q&A support, enrichment columns, answers table, entity registry, aspects
-- All changes are additive with safe defaults — zero risk to existing data.
-- Run in Supabase SQL Editor.

-- Q&A support on social_items
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS question_content TEXT;
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS has_answers BOOLEAN DEFAULT FALSE;
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS answer_count INTEGER DEFAULT 0;

-- Enrichment columns
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS emotion TEXT;
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS intent TEXT;
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS sentiment_intensity SMALLINT;
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS engagement_score REAL;
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'de';
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS resolved_source TEXT;

-- Answers table
CREATE TABLE IF NOT EXISTS social_item_answers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    social_item_id UUID NOT NULL REFERENCES social_items(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    author TEXT,
    position INTEGER DEFAULT 0,
    votes INTEGER DEFAULT 0,
    is_accepted BOOLEAN DEFAULT FALSE,
    posted_at TEXT,
    source_id TEXT,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sia_item_id ON social_item_answers(social_item_id);
CREATE INDEX IF NOT EXISTS idx_sia_accepted ON social_item_answers(is_accepted) WHERE is_accepted = TRUE;

-- Entity registry
CREATE TABLE IF NOT EXISTS entities (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    entity_type TEXT NOT NULL,
    category TEXT,
    brand TEXT,
    aliases TEXT[] DEFAULT '{}',
    priority INTEGER DEFAULT 3,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Item-entity junction (per-entity sentiment)
CREATE TABLE IF NOT EXISTS item_entities (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    social_item_id UUID NOT NULL REFERENCES social_items(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    mention_type TEXT DEFAULT 'direct',
    sentiment TEXT,
    confidence REAL DEFAULT 1.0,
    context_snippet TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(social_item_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_ie_item ON item_entities(social_item_id);
CREATE INDEX IF NOT EXISTS idx_ie_entity ON item_entities(entity_id);

-- Aspect-based sentiment
CREATE TABLE IF NOT EXISTS item_aspects (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    social_item_id UUID NOT NULL REFERENCES social_items(id) ON DELETE CASCADE,
    aspect TEXT NOT NULL,
    sentiment TEXT NOT NULL,
    intensity SMALLINT DEFAULT 3,
    evidence_snippet TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(social_item_id, aspect)
);
CREATE INDEX IF NOT EXISTS idx_ia_item ON item_aspects(social_item_id);
CREATE INDEX IF NOT EXISTS idx_ia_aspect ON item_aspects(aspect);
