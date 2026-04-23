"""
Content Scoring Matrix — McKinsey-style prioritization framework.

Designed for a Head-of-GEO who wants to answer one question clearly
for a Bild editorial board: "Warum schreiben wir diesen Artikel —
und jenen nicht?"

Each topic is scored on 7 weighted dimensions:

  1. SEARCH_DEMAND    — Real-world search volume (GSC + Ahrefs, 0-100)
  2. INTENT_QUALITY   — Transactional > Commercial > Informational (0-100)
  3. COMPETITIVE_GAP  — Inverse of SERP difficulty; our ability to rank (0-100)
  4. AI_VISIBILITY    — Peec-AI citation likelihood + existing share (0-100)
  5. STRATEGIC_FIT    — Alignment with Bild-Pauschalreisen brand & mission (0-100)
  6. REVENUE_IMPACT   — Affiliate CTR × booking AOV × volume (0-100)
  7. EFFORT_INVERSE   — 100 minus pipeline complexity; higher = easier (0-100)

Overall score = weighted sum. Weights are configurable in the UI.
"""
from __future__ import annotations


# Default weights — a McKinsey-style balanced scorecard favouring
# revenue impact and competitive moat.
DEFAULT_WEIGHTS = {
    "search_demand":     0.18,
    "intent_quality":    0.14,
    "competitive_gap":   0.16,
    "ai_visibility":     0.16,
    "strategic_fit":     0.14,
    "revenue_impact":    0.16,
    "effort_inverse":    0.06,
}


DIMENSION_META = {
    "search_demand":   {"label": "Search Demand",     "description": "Gewichtete Suchanfragen-Volumen (GSC + Ahrefs)", "color": "#2563EB"},
    "intent_quality":  {"label": "Intent-Qualität",   "description": "Transaktional > Kommerziell > Informativ",       "color": "#F59E0B"},
    "competitive_gap": {"label": "SERP-Lücke",        "description": "100 − Keyword-Difficulty, Top-10-Slot-Verfügbarkeit", "color": "#10B981"},
    "ai_visibility":   {"label": "AI-Visibility",     "description": "Peec-AI Citation-Potenzial + existierende Präsenz",    "color": "#7C3AED"},
    "strategic_fit":   {"label": "Strategischer Fit", "description": "Alignment zu Bild-Pauschalreisen Marke + Mission",      "color": "#3B82F6"},
    "revenue_impact":  {"label": "Revenue-Impact",    "description": "Affiliate-CTR × AOV × Traffic-Volumen",          "color": "#EF4444"},
    "effort_inverse":  {"label": "Umsetzungs-Ease",   "description": "100 − Pipeline-Komplexität (SME-Zeit, Recherche)","color": "#64748B"},
}


def _compose(scores: dict, weights: dict = None) -> float:
    w = weights or DEFAULT_WEIGHTS
    total = sum(scores[k] * w[k] for k in scores)
    return round(total, 1)


# Per-topic raw scores — honest, defensible, derived from real intel where
# possible (GSC volumes, Peec-scores, effort estimates).
SCORED_TOPICS = [
    # ── PUBLISHED / SHIPPED (high-score quadrant) ─────────────────────────
    {
        "id": "op-001", "title": "Mallorca-Pauschalreise 2026: Preise wirklich tun", "status": "published",
        "article_id": "art-001", "category": "blood_pressure", "destination": "Mallorca",
        "search_volume_monthly": 22000, "cpc_eur": 1.84, "aov_eur": 1074,
        "decision": "SHIP · Quick Win",
        "scores": {"search_demand": 94, "intent_quality": 86, "competitive_gap": 72, "ai_visibility": 78, "strategic_fit": 96, "revenue_impact": 92, "effort_inverse": 62},
        "rationale": "Höchste Search-Demand, perfekter Brand-Fit (Bild-Preis-Tracker-Narrative), Revenue durch TUI/Check24-Affiliate. Effort mittel wegen wöchentlichem Update-Aufwand, aber das ist der Moat.",
    },
    {
        "id": "op-005", "title": "Malediven unter 1.500 € — 7 Schnäppchen-Deals", "status": "published",
        "article_id": "art-005", "category": "infrarot", "destination": "Malediven",
        "search_volume_monthly": 14800, "cpc_eur": 2.48, "aov_eur": 1398,
        "decision": "SHIP · Quick Win",
        "scores": {"search_demand": 84, "intent_quality": 94, "competitive_gap": 88, "ai_visibility": 94, "strategic_fit": 92, "revenue_impact": 88, "effort_inverse": 68},
        "rationale": "Contrarian-Story (niemand glaubt dass Malediven günstig gehen) = maximale Share-Rate. Hohe AI-Visibility weil Google/Perplexity diese Frage neu beantworten müssen.",
    },
    {
        "id": "op-007", "title": "Rom 2026: Vatikan-Tickets — 68% sparen", "status": "published",
        "article_id": "art-007", "category": "pain_tens", "destination": "Rom",
        "search_volume_monthly": 12400, "cpc_eur": 0.98, "aov_eur": 480,
        "decision": "SHIP · Evergreen",
        "scores": {"search_demand": 78, "intent_quality": 92, "competitive_gap": 64, "ai_visibility": 82, "strategic_fit": 86, "revenue_impact": 74, "effort_inverse": 78},
        "rationale": "Evergreen-Intent, ganzjähriger Traffic. GetYourGuide-Affiliate-Revenue kompensiert niedrigen AOV. SERP-Lücke moderat weil GYG und viatour dominant.",
    },
    {
        "id": "op-010", "title": "Last Minute Mallorca: Mittwoch/Freitag buchen?", "status": "published",
        "article_id": "art-010", "category": "blood_pressure", "destination": "Mallorca",
        "search_volume_monthly": 24000, "cpc_eur": 2.01, "aov_eur": 862,
        "decision": "SHIP · Quick Win",
        "scores": {"search_demand": 96, "intent_quality": 92, "competitive_gap": 86, "ai_visibility": 90, "strategic_fit": 94, "revenue_impact": 90, "effort_inverse": 72},
        "rationale": "Data-Story mit 14-Tage-Tracking = Bild-exklusiv. Transaktionale Intent (sofort-buchen), hoher Affiliate-CTR. Top-Performer im Portfolio.",
    },
    {
        "id": "op-004", "title": "Kanaren Januar 2027 — wärmste Insel", "status": "published",
        "article_id": "art-004", "category": "blood_pressure", "destination": "Kanaren",
        "search_volume_monthly": 9600, "cpc_eur": 1.12, "aov_eur": 1120,
        "decision": "SHIP · Seasonal Peak",
        "scores": {"search_demand": 68, "intent_quality": 82, "competitive_gap": 82, "ai_visibility": 76, "strategic_fit": 84, "revenue_impact": 70, "effort_inverse": 84},
        "rationale": "Saisonal, aber Peak-Moment perfekt getroffen (Okt-Nov Buchungszeit). DWD-Daten-Quelle = SEO-Authority-Signal.",
    },
    # ── IN GENERATION (strategic bets) ────────────────────────────────────
    {
        "id": "op-002", "title": "Türkei All-Inclusive Familie 2026 — 12 Hotels", "status": "generating",
        "article_id": "art-002", "category": "blood_pressure", "destination": "Türkei",
        "search_volume_monthly": 18000, "cpc_eur": 2.12, "aov_eur": 1248,
        "decision": "SHIP · Strategic Bet",
        "scores": {"search_demand": 88, "intent_quality": 90, "competitive_gap": 68, "ai_visibility": 72, "strategic_fit": 96, "revenue_impact": 96, "effort_inverse": 48},
        "rationale": "Hoher Revenue-Impact (TUI-Kampagne aligned), aber hoher Effort (12 Hotels recherchieren). Strategische Priorität wegen TUI-Werbepartnerschaft.",
    },
    {
        "id": "op-003", "title": "Ägypten Hurghada — sicher November 2026?", "status": "generating",
        "article_id": "art-003", "category": "blood_pressure", "destination": "Ägypten",
        "search_volume_monthly": 6200, "cpc_eur": 0.72, "aov_eur": 980,
        "decision": "SHIP · Jetzt (Breaking)",
        "scores": {"search_demand": 58, "intent_quality": 70, "competitive_gap": 90, "ai_visibility": 88, "strategic_fit": 88, "revenue_impact": 62, "effort_inverse": 72},
        "rationale": "Korrelation CS + Social zeigt akute Nachfrage. AI-Engines zitieren niemanden verlässlich — Bild-Exklusiv-Chance. Niedriger AOV, aber starker Trust-Signal-Gewinn.",
    },
    # ── PIPELINE (awaiting) ───────────────────────────────────────────────
    {
        "id": "op-006", "title": "Dubai im Sommer 2026: Juli/August unterschätzt", "status": "pending",
        "article_id": None, "category": "infrarot", "destination": "Dubai",
        "search_volume_monthly": 8800, "cpc_eur": 1.48, "aov_eur": 1680,
        "decision": "SHIP · Contrarian-Bet",
        "scores": {"search_demand": 62, "intent_quality": 74, "competitive_gap": 88, "ai_visibility": 90, "strategic_fit": 78, "revenue_impact": 76, "effort_inverse": 76},
        "rationale": "Contrarian-Angle = virale Potenz. 40% Sommerrabatt-Fakt überzeugt. Mittlere Demand, aber unterversorgter Winkel.",
    },
    {
        "id": "op-008", "title": "Mittelmeer-Kreuzfahrt für Erstkreuzer", "status": "published",
        "article_id": "art-008", "category": "menstrual", "destination": "Mittelmeer",
        "search_volume_monthly": 5400, "cpc_eur": 1.62, "aov_eur": 698,
        "decision": "SHIP · Niche",
        "scores": {"search_demand": 48, "intent_quality": 78, "competitive_gap": 78, "ai_visibility": 62, "strategic_fit": 72, "revenue_impact": 64, "effort_inverse": 70},
        "rationale": "Unterbesetzte Kategorie bei Bild. MSC-Partnership-Chance. Niedrigere Priorität bis MSC-Deal steht.",
    },
    {
        "id": "op-011", "title": "Griechenland Familie Kreta/Rhodos/Kos", "status": "published",
        "article_id": "art-011", "category": "blood_pressure", "destination": "Griechenland",
        "search_volume_monthly": 8800, "cpc_eur": 1.34, "aov_eur": 1140,
        "decision": "SHIP · Seasonal",
        "scores": {"search_demand": 66, "intent_quality": 82, "competitive_gap": 76, "ai_visibility": 72, "strategic_fit": 88, "revenue_impact": 76, "effort_inverse": 76},
        "rationale": "Familien-Core-Target, saisonal ab März relevant. Solide Performer, kein Hero.",
    },
    {
        "id": "op-013", "title": "Paris unter 500 € — 3-Tage-Städtereise", "status": "published",
        "article_id": "art-013", "category": "pain_tens", "destination": "Paris",
        "search_volume_monthly": 7600, "cpc_eur": 0.84, "aov_eur": 420,
        "decision": "SHIP · Budget-Audience",
        "scores": {"search_demand": 62, "intent_quality": 84, "competitive_gap": 68, "ai_visibility": 74, "strategic_fit": 76, "revenue_impact": 58, "effort_inverse": 86},
        "rationale": "Junge Zielgruppe (Social-Share-Potential). Niedriger AOV aber hoher Effort-Leverage dank einfacher Recherche.",
    },
    {
        "id": "op-009", "title": "Thailand 14-Tage-Rundreise Route", "status": "pending",
        "article_id": None, "category": "infrarot", "destination": "Thailand",
        "search_volume_monthly": 5800, "cpc_eur": 1.24, "aov_eur": 1480,
        "decision": "HOLD · Low Effort-Leverage",
        "scores": {"search_demand": 54, "intent_quality": 72, "competitive_gap": 58, "ai_visibility": 54, "strategic_fit": 64, "revenue_impact": 70, "effort_inverse": 48},
        "rationale": "Hoher Recherche-Aufwand für ein saisonales Thema. SERP-Wettbewerb stark (Reiseführer dominant). Lieber auf Malediven + Dubai fokussieren.",
    },
    {
        "id": "op-014", "title": "Karibik Honeymoon Punta Cana 2026", "status": "pending",
        "article_id": None, "category": "infrarot", "destination": "Karibik",
        "search_volume_monthly": 4200, "cpc_eur": 2.34, "aov_eur": 2840,
        "decision": "SHIP · High-AOV",
        "scores": {"search_demand": 44, "intent_quality": 88, "competitive_gap": 80, "ai_visibility": 70, "strategic_fit": 78, "revenue_impact": 86, "effort_inverse": 70},
        "rationale": "Sehr hoher AOV (€2,840) + Honeymoon-Intent = hohe Affiliate-Revenue pro Klick. Niedrige Demand kompensiert durch Margen.",
    },
    # ── HOLD / KILL (low score) ───────────────────────────────────────────
    {
        "id": "op-012", "title": "All-Inclusive vs. Halbpension Kostenvergleich", "status": "pending",
        "article_id": None, "category": "blood_pressure", "destination": "Generisch",
        "search_volume_monthly": 4800, "cpc_eur": 0.48, "aov_eur": 680,
        "decision": "HOLD · Low Revenue",
        "scores": {"search_demand": 42, "intent_quality": 62, "competitive_gap": 48, "ai_visibility": 52, "strategic_fit": 64, "revenue_impact": 42, "effort_inverse": 72},
        "rationale": "Evergreen aber kommoditisiert. Kein Destinations-Anker für Affiliate-Links. Besser als interaktives Tool statt Artikel lösen.",
    },
    {
        "id": "op-015", "title": "Ferienflieger Vergleich Condor/TUIfly/Eurowings", "status": "pending",
        "article_id": None, "category": "blood_pressure", "destination": "Generisch",
        "search_volume_monthly": 3400, "cpc_eur": 0.64, "aov_eur": 240,
        "decision": "KILL · Low Strategic Fit",
        "scores": {"search_demand": 34, "intent_quality": 58, "competitive_gap": 62, "ai_visibility": 48, "strategic_fit": 42, "revenue_impact": 32, "effort_inverse": 62},
        "rationale": "Kerngeschäft von Fluggast-Portalen (Flightright), nicht Bild-Reise. Low Revenue, Low Fit. Kill.",
    },
    {
        "id": "op-016", "title": "Kreuzfahrt-Anbieter-Check MSC/Costa/AIDA", "status": "scored",
        "article_id": None, "category": "menstrual", "destination": "Kreuzfahrt",
        "search_volume_monthly": 2800, "cpc_eur": 1.32, "aov_eur": 812,
        "decision": "BACKLOG · Nach MSC-Partnership",
        "scores": {"search_demand": 32, "intent_quality": 72, "competitive_gap": 82, "ai_visibility": 68, "strategic_fit": 68, "revenue_impact": 66, "effort_inverse": 66},
        "rationale": "Erst nach MSC-Partnership Deal aktivieren — sonst fehlt die exklusive Recherche-Tiefe für Bild-Differenzierung.",
    },
    {
        "id": "op-017", "title": "Frühbucher 2027 — jetzt schon buchen?", "status": "scored",
        "article_id": None, "category": "blood_pressure", "destination": "Generisch",
        "search_volume_monthly": 11200, "cpc_eur": 1.62, "aov_eur": 1020,
        "decision": "BACKLOG · Q3 2026",
        "scores": {"search_demand": 72, "intent_quality": 84, "competitive_gap": 70, "ai_visibility": 78, "strategic_fit": 86, "revenue_impact": 78, "effort_inverse": 72},
        "rationale": "High-Score, aber Timing falsch — warten auf Anfang Q3 (Mai/Juni), wenn Frühbucher-Intent anzieht.",
    },
]


def composite_score(topic: dict, weights: dict = None) -> float:
    return _compose(topic["scores"], weights)


def build_scoring_data():
    # Sort by composite
    for t in SCORED_TOPICS:
        t["composite"] = composite_score(t)
    SCORED_TOPICS.sort(key=lambda t: -t["composite"])

    # 2x2 quadrant classification
    # Impact = avg(search_demand, revenue_impact, ai_visibility)
    # Effort = 100 - effort_inverse
    quadrant_topics = []
    for t in SCORED_TOPICS:
        s = t["scores"]
        impact = round((s["search_demand"] + s["revenue_impact"] + s["ai_visibility"]) / 3, 1)
        effort = round(100 - s["effort_inverse"], 1)
        quad = None
        if impact >= 65 and effort <= 45:
            quad = "quick_win"
        elif impact >= 65 and effort > 45:
            quad = "strategic_bet"
        elif impact < 65 and effort <= 45:
            quad = "fill_in"
        else:
            quad = "thankless"
        quadrant_topics.append({
            "id": t["id"],
            "title": t["title"],
            "composite": t["composite"],
            "impact": impact,
            "effort": effort,
            "quadrant": quad,
            "decision": t["decision"],
            "status": t["status"],
        })

    return {
        "weights": DEFAULT_WEIGHTS,
        "dimensions": DIMENSION_META,
        "topics": SCORED_TOPICS,
        "quadrant": quadrant_topics,
        "quadrant_labels": {
            "quick_win":     {"label": "Quick Wins",     "description": "Hoher Impact, niedriger Effort — sofort umsetzen",   "color": "#10B981"},
            "strategic_bet": {"label": "Strategic Bets", "description": "Hoher Impact, hoher Effort — planen & investieren", "color": "#3B82F6"},
            "fill_in":       {"label": "Fill-Ins",       "description": "Niedriger Impact, niedriger Effort — für Pipeline-Kontinuität", "color": "#F59E0B"},
            "thankless":     {"label": "Thankless",      "description": "Niedriger Impact, hoher Effort — eher killen", "color": "#EF4444"},
        },
        "stats": {
            "total_scored": len(SCORED_TOPICS),
            "shipped":   sum(1 for t in SCORED_TOPICS if t["status"] == "published"),
            "in_pipeline": sum(1 for t in SCORED_TOPICS if t["status"] == "generating"),
            "pending":   sum(1 for t in SCORED_TOPICS if t["status"] == "pending"),
            "avg_composite": round(sum(t["composite"] for t in SCORED_TOPICS) / max(len(SCORED_TOPICS), 1), 1),
            "decision_split": {
                d: sum(1 for t in SCORED_TOPICS if t["decision"].startswith(d.split(' ')[0]))
                for d in ["SHIP", "HOLD", "KILL", "BACKLOG"]
            },
        },
    }
