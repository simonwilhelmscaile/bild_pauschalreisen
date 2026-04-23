/**
 * TypeScript interfaces for social items and dashboard data.
 */

export interface SocialItem {
  id?: string;
  source?: string;
  source_url?: string;
  title?: string;
  content?: string;
  question_content?: string;
  posted_at?: string;
  category?: string;
  sentiment?: string;
  relevance_score?: number;
  device_relevance_score?: number;
  keywords?: string[];
  product_mentions?: string[];
  emotion?: string;
  intent?: string;
  sentiment_intensity?: number;
  engagement_score?: number;
  language?: string;
  resolved_source?: string;
  has_answers?: boolean;
  answer_count?: number;
  raw_data?: Record<string, any>;
  // Journey fields
  journey_stage?: string;
  pain_category?: string;
  solutions_mentioned?: string[];
  collection_type?: string;
  beurer_opportunity?: string;
  bridge_moment?: string;
  // Deep insight fields
  pain_location?: string;
  pain_severity?: string;
  pain_duration?: string;
  bp_concern_type?: string;
  bp_severity?: string;
  coping_strategies?: string[];
  medications_mentioned?: string[];
  life_situation?: string;
  user_segment?: string;
  problem_category?: string;
  solution_frustrations?: string[];
  negative_root_cause?: string;
  key_insight?: string;
  content_opportunity?: string;
  // Enriched by fetch layer
  _entities?: EntityRow[];
  _aspects?: AspectRow[];
  _answer_count?: number;
  _top_answers?: AnswerRow[];
  _display_source?: string;
}

export interface EntityRow {
  social_item_id?: string;
  entity_id?: string;
  mention_type?: string;
  sentiment?: string;
  confidence?: number;
  context_snippet?: string;
  entities?: {
    canonical_name?: string;
    entity_type?: string;
    category?: string;
    brand?: string;
  };
}

export interface AspectRow {
  social_item_id?: string;
  aspect?: string;
  sentiment?: string;
  intensity?: number;
  evidence_snippet?: string;
}

export interface AnswerRow {
  social_item_id?: string;
  content?: string;
  author?: string;
  votes?: number;
  is_accepted?: boolean;
  position?: number;
}

export interface DashboardData {
  period: { start: string; end: string; week_number: number };
  generated_at: string;
  _source?: string;
  executive_summary: Record<string, any>;
  alerts: Record<string, any[]>;
  volume_by_source: Record<string, number>;
  volume_by_source_category: Record<string, number>;
  volume_by_source_by_category: Record<string, Record<string, number>>;
  volume_by_category: Record<string, number>;
  sentiment_by_category: Record<string, any>;
  trending_topics: Array<{ topic: string; count: number }>;
  product_intelligence: Record<string, any>;
  product_mentions: Record<string, any>;
  user_voice: Record<string, any>;
  content_opportunities: any[];
  top_posts: any[];
  source_highlights: any[];
  appendices: Record<string, any[]>;
  executive_dashboard: Record<string, any>;
  key_actions: any[];
  sentiment_deepdive: Record<string, any>;
  competitive_intelligence: Record<string, any>;
  journey_intelligence: Record<string, any>;
  deep_insights: Record<string, any>;
  category_deep_insights: Record<string, any>;
  category_journeys: Record<string, any>;
  wow_metrics: Record<string, any>;
  brand_sentiment: { positive: number; neutral: number; negative: number; total: number; note: string };
  topic_sentiment: { positive: number; neutral: number; negative: number; total: number; note: string };
  other_breakdown: Record<string, number>;
  purchase_intent_feed: Array<{
    title: string;
    source: string;
    source_url: string;
    category: string;
    intent_signal: string;
    reach_estimate: number;
    posted_at: string;
    matched_products: string[];
  }>;
  news?: {
    articles: Array<{
      title: string;
      url: string;
      source: string;
      posted_at: string;
      summary: string;
      author: string | null;
      score: number;
      tier: "must_read" | "interesting" | "worth_reading";
      topic_tags: string[];
      is_competitor: boolean;
      news_category: "industry" | "company" | "competitor" | "curated";
      submitted_by?: string;
    }>;
    by_topic: Record<string, number>;
    by_source: Record<string, number>;
    total: number;
  };
  available_weeks?: any[];
  kundendienstInsights?: {
    heatmap: {
      products: Array<{ model: string; category: string | null; reasons: Record<string, number>; total: number }>;
      allReasons: string[];
      totalCases: number;
    };
    trends: {
      weeks: Array<{ week: string; total: number; byReason: Record<string, number> }>;
      allReasons: string[];
    };
    alerts: Array<{
      product: string;
      reason: string;
      currentCount: number;
      avgCount: number;
      changePercent: number;
      severity: "warning" | "critical";
    }>;
    summary: {
      totalCases: number;
      topProduct: { model: string; count: number } | null;
      topReason: { reason: string; count: number } | null;
      alertCount: number;
    };
  };
}
