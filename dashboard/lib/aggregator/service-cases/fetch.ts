import { SupabaseClient } from "@supabase/supabase-js";
import { ServiceCase } from "./types";

/**
 * Fetch service cases for a date range.
 * Returns empty array if the table doesn't exist (graceful degradation).
 */
export async function fetchServiceCases(
  supabase: SupabaseClient,
  startDate: string,
  endDate: string,
  clientId: string = "beurer"
): Promise<ServiceCase[]> {
  try {
    const { data, error } = await supabase
      .from("service_cases")
      .select("*")
      .eq("client_id", clientId)
      .gte("case_date", startDate)
      .lte("case_date", endDate);

    if (error) {
      // Table may not exist yet — degrade gracefully
      console.warn("service_cases fetch error (non-blocking):", error.message);
      return [];
    }
    return (data || []) as ServiceCase[];
  } catch (e) {
    console.warn("service_cases fetch failed (non-blocking):", e);
    return [];
  }
}
