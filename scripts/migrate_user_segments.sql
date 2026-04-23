-- Migration: Split life_situation into user_segment + problem_category
-- Run this in the Supabase SQL editor

-- Step 1: Add new columns
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS user_segment TEXT;
ALTER TABLE social_items ADD COLUMN IF NOT EXISTS problem_category TEXT;

-- Step 2: Migrate existing life_situation values to user_segment
UPDATE social_items SET user_segment = life_situation
WHERE life_situation IN (
  'schwangerschaft', 'buero_arbeit', 'sport_aktiv', 'senioren',
  'eltern_baby', 'pendler', 'schichtarbeit', 'homeoffice',
  'pflegende_angehoerige', 'studenten', 'reisende', 'fitness_ems'
) AND user_segment IS NULL;

-- Step 3: Migrate existing life_situation values to problem_category
UPDATE social_items SET problem_category = life_situation
WHERE life_situation IN (
  'chronisch_krank', 'post_op', 'uebergewicht', 'stress_burnout',
  'frisch_diagnostiziert', 'medikamenten_nebenwirkungen_sucher',
  'migraene_patient', 'fibromyalgie_patient', 'endometriose'
) AND problem_category IS NULL;

-- Note: life_situation column is kept for backward compatibility.
-- After re-classification, life_situation = COALESCE(user_segment, problem_category).
