/** Raw service case row from Supabase */
export interface ServiceCase {
  id: string;
  client_id: string;
  case_id: string;
  product_raw: string;
  product_model: string | null;
  product_category: string | null;
  reason: string;
  case_date: string; // YYYY-MM-DD
  imported_at: string;
  import_batch_id: string;
}

/** Product row in the heatmap */
export interface HeatmapProduct {
  model: string;
  category: string | null;
  reasons: Record<string, number>;
  total: number;
}

/** Heatmap data (View A) */
export interface HeatmapData {
  products: HeatmapProduct[];
  allReasons: string[];
  totalCases: number;
}

/** Single week in the trend chart */
export interface TrendWeek {
  week: string; // ISO week, e.g. "2026-W04"
  total: number;
  byReason: Record<string, number>;
}

/** Trend data (View B) */
export interface TrendData {
  weeks: TrendWeek[];
  allReasons: string[];
}

/** Single risk alert */
export interface ServiceCaseAlert {
  product: string;
  reason: string;
  currentCount: number;
  avgCount: number;
  changePercent: number;
  severity: "warning" | "critical";
}

/** Combined output for the Kundendienst tab */
export interface KundendienstInsights {
  heatmap: HeatmapData;
  trends: TrendData;
  alerts: ServiceCaseAlert[];
  summary: {
    totalCases: number;
    topProduct: { model: string; count: number } | null;
    topReason: { reason: string; count: number } | null;
    alertCount: number;
  };
}
