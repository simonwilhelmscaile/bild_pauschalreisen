import { CATEGORY_LABELS_DE } from "../constants";

export function buildExecutiveDashboard(
  executiveSummary: Record<string, any>,
  extras?: {
    volume_by_category?: Record<string, number>;
    alerts?: Record<string, any[]>;
    competitive_intelligence?: Record<string, any>;
    wow_metrics?: Record<string, any>;
  },
) {
  const sentimentPct = executiveSummary.overall_sentiment_pct || {};
  const volumeByCat = extras?.volume_by_category || {};
  const alerts = extras?.alerts || {};
  const compIntel = extras?.competitive_intelligence || {};
  const wowMetrics = extras?.wow_metrics || {};

  // --- Deterministic insights ---
  const insights: Array<{ icon: string; text: string; tab?: string }> = [];

  // Insight 1: Volume leader (top non-"other" category)
  const catEntries = Object.entries(volumeByCat)
    .filter(([k]) => k !== "other" && k !== "unclassified")
    .sort((a, b) => b[1] - a[1]);
  if (catEntries.length > 0) {
    const [topCat, topCount] = catEntries[0];
    const label = CATEGORY_LABELS_DE[topCat] || topCat;
    insights.push({
      icon: "trending_up",
      text: `${label}-Diskussionen dominieren mit ${topCount} Erwähnungen (${catEntries.length > 1 ? `vor ${CATEGORY_LABELS_DE[catEntries[1][0]] || catEntries[1][0]}` : "führende Kategorie"}).`,
      tab: "insights",
    });
  }

  // Insight 2: Competitor weakness
  const compWeaknesses = compIntel.competitor_weaknesses || [];
  if (compWeaknesses.length > 0) {
    const top = compWeaknesses[0];
    insights.push({
      icon: "sports_martial_arts",
      text: `Wettbewerber-Schwäche: ${top.competitor} hat ${top.count} negative Erwähnung${top.count !== 1 ? "en" : ""} (${top.issue}).`,
      tab: "competitors",
    });
  }

  // Insight 3: WoW change or device questions count
  if (wowMetrics.available && wowMetrics.mentions_delta != null) {
    const delta = wowMetrics.mentions_delta;
    const direction = delta > 0 ? "gestiegen" : delta < 0 ? "gesunken" : "unverändert";
    insights.push({
      icon: delta > 0 ? "arrow_upward" : delta < 0 ? "arrow_downward" : "swap_vert",
      text: `Erwähnungen im Vergleich zur Vorperiode ${direction} (${wowMetrics.mentions_change}).`,
    });
  } else {
    const deviceQCount = executiveSummary.device_questions_count || 0;
    if (deviceQCount > 0) {
      insights.push({
        icon: "help_outline",
        text: `${deviceQCount} geräte-relevante Fragen identifiziert — Content-/Support-Potenzial.`,
        tab: "content",
      });
    }
  }

  // Fallback insights to guarantee non-empty array
  if (insights.length < 3) {
    const totalMentions = executiveSummary.total_mentions || 0;
    if (totalMentions > 0) {
      insights.push({ icon: "monitoring", text: `${totalMentions} Erwähnungen in dieser Periode erfasst.` });
    }
  }
  if (insights.length < 3) {
    const negPct = sentimentPct.negative || 0;
    const posPct = sentimentPct.positive || 0;
    insights.push({
      icon: negPct > posPct ? "sentiment_dissatisfied" : "sentiment_satisfied",
      text: `Sentiment-Verteilung: ${posPct}% positiv, ${negPct}% negativ.`,
      tab: "sentiment",
    });
  }
  if (insights.length < 3) {
    insights.push({ icon: "groups", text: "Keine weiteren auffälligen Muster in dieser Periode." });
  }

  // --- Deterministic actions ---
  const actions: Array<{ priority: string; text: string; category: string }> = [];

  // Action 1: Critical alerts → support
  const criticalAlerts = alerts.critical || [];
  if (criticalAlerts.length > 0) {
    const topAlert = criticalAlerts[0];
    const product = topAlert.product || "Produkt";
    actions.push({
      priority: "high",
      text: `Kritisches Feedback zu ${product} prüfen und Support-Eskalation einleiten.`,
      category: "support",
    });
  }

  // Action 2: Opportunity alerts → content
  const opportunityAlerts = alerts.opportunity || [];
  if (opportunityAlerts.length > 0) {
    const topOpp = opportunityAlerts[0];
    const topic = (topOpp.title || "").slice(0, 60);
    actions.push({
      priority: "medium",
      text: topic
        ? `Positive Erwähnung verstärken: ${topic}.`
        : "Positive Nutzerstimmen für Content-Marketing nutzen.",
      category: "content",
    });
  }

  // Action 3: Competitor weakness → positioning
  if (compWeaknesses.length > 0) {
    const top = compWeaknesses[0];
    actions.push({
      priority: "medium",
      text: top.content_idea || `Beurer-Vorteile vs. ${top.competitor} kommunizieren.`,
      category: "positioning",
    });
  }

  // Fallback actions to guarantee non-empty array
  if (actions.length < 3) {
    const negPct = sentimentPct.negative || 0;
    if (negPct > 20) {
      actions.push({ priority: "medium", text: `Negative Stimmung (${negPct}%) analysieren und Ursachen identifizieren.`, category: "analysis" });
    }
  }
  if (actions.length < 3) {
    actions.push({ priority: "low", text: "Top-Beiträge prüfen und relevante Community-Fragen beantworten.", category: "engagement" });
  }
  if (actions.length < 3) {
    actions.push({ priority: "low", text: "Content-Opportunities-Tab für neue Inhaltsideen konsultieren.", category: "content" });
  }

  return {
    kpis: {
      mentions: executiveSummary.total_mentions || 0,
      mentions_change: wowMetrics.mentions_change || null,
      positive_pct: sentimentPct.positive || 0,
      negative_pct: sentimentPct.negative || 0,
      competitor_mentions: executiveSummary.competitor_mention_count || 0,
      device_questions: executiveSummary.device_questions_count || 0,
    },
    top_3_insights: insights.slice(0, 3),
    top_3_actions: actions.slice(0, 3),
  };
}
