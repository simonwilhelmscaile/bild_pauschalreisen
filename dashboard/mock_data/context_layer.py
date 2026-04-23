"""
Context Layer data for the BILD Pauschalreisen Content Engine demo.

Designed from the perspective of a Head-of-GEO / former McKinsey partner
who needs to convince a Bild editorial team that their own context is
the moat — not the LLM.

This module produces four coherent datasets:

1. CONNECTORS  — 20 internal + external data sources (CRM, PIM, CDP,
   Analytics, CMS, CS, Ad-Platforms, DWH, Social, DAM, Editorial).
   Each shows connection status, records, last sync, data categories.

2. UPLOADED_DOCS — the explicit "context library" — brand guidelines,
   editorial playbook, termbase, style guide, customer personas, product
   briefs etc. that a content team uploads to lock in brand-true output.

3. KNOWLEDGE_GRAPH — Obsidian-style graph with ~260 nodes and ~950
   edges, color-coded by 12 node types, showing how destinations,
   topics, products, personas, internal docs, CS tickets, social
   signals, news, competitors, articles, keywords and authors relate.

4. CORRELATIONS — concrete examples where an INTERNAL signal (CS
   ticket spike, sales funnel drop, PIM inventory shift) predicted an
   EXTERNAL signal (social listening spike, Google Trends uptick,
   competitor news) — with lead time and correlation coefficient.

All strings are editorially realistic for a Bild-Pauschalreisen context.
"""
from __future__ import annotations
from datetime import datetime, timedelta
import random

random.seed(42)


def _days_ago(n: int) -> str:
    return (datetime.utcnow() - timedelta(days=n)).replace(microsecond=0).isoformat() + "+00:00"


def _minutes_ago(n: int) -> str:
    return (datetime.utcnow() - timedelta(minutes=n)).replace(microsecond=0).isoformat() + "+00:00"


# ═══════════════════════════════════════════════════════════════════════════
# 1. CONNECTORS
# ═══════════════════════════════════════════════════════════════════════════

CONNECTORS = [
    # ── CRM & Sales (revenue-bearing) ──────────────────────────────────────
    {
        "id": "salesforce_crm",
        "name": "Salesforce Sales Cloud",
        "category": "CRM",
        "status": "connected",
        "vendor": "Salesforce",
        "records": 48720,
        "records_label": "Advertiser & Partner Accounts",
        "last_sync": _minutes_ago(8),
        "sync_frequency": "every 15 min",
        "data_categories": ["Advertiser briefs", "Deal stages", "Campaign objectives", "Account owners"],
        "why_it_matters": "Ermöglicht, Werbe-Briefings direkt mit Content-Opportunities zu matchen — Bsp.: TUI-Kampagne Türkei + redaktioneller Türkei-Artikel.",
        "logo_initial": "SF",
        "color": "#00A1E0",
    },
    {
        "id": "hubspot_marketing",
        "name": "HubSpot Marketing Hub",
        "category": "CRM",
        "status": "connected",
        "vendor": "HubSpot",
        "records": 128430,
        "records_label": "Newsletter Subscribers",
        "last_sync": _minutes_ago(22),
        "sync_frequency": "hourly",
        "data_categories": ["Newsletter segments", "Open-rates per topic", "Click-patterns"],
        "why_it_matters": "Identifiziert Themen mit hoher Newsletter-Engagement → höhere Content-Priorität.",
        "logo_initial": "HS",
        "color": "#FF7A59",
    },
    # ── Product / Inventory ────────────────────────────────────────────────
    {
        "id": "pim_inventory",
        "name": "BILD-Reise PIM (intern)",
        "category": "Product Inventory",
        "status": "connected",
        "vendor": "Internal",
        "records": 18642,
        "records_label": "Pauschalreise-SKUs",
        "last_sync": _minutes_ago(4),
        "sync_frequency": "every 5 min",
        "data_categories": ["Hotel-Inventory", "Flug-Routen", "Preise live", "Verfügbarkeit"],
        "why_it_matters": "Artikel können nur Produkte nennen, die wirklich buchbar sind — verhindert Dead-Links zu ausgebuchten Hotels.",
        "logo_initial": "PIM",
        "color": "#DD0000",
    },
    {
        "id": "tui_affiliate_api",
        "name": "TUI Partner API",
        "category": "Product Inventory",
        "status": "connected",
        "vendor": "TUI",
        "records": 6820,
        "records_label": "Live Angebote",
        "last_sync": _minutes_ago(3),
        "sync_frequency": "every 5 min",
        "data_categories": ["Preise", "Verfügbarkeit", "Hotel-Details", "Affiliate-URLs"],
        "why_it_matters": "Preis-Tabellen in Artikeln bleiben stündlich frisch — SEO + AEO-Vorteil.",
        "logo_initial": "TU",
        "color": "#E60000",
    },
    {
        "id": "check24_affiliate",
        "name": "Check24 Affiliate Feed",
        "category": "Product Inventory",
        "status": "connected",
        "vendor": "Check24",
        "records": 14240,
        "records_label": "Preis-Vergleichs-Angebote",
        "last_sync": _minutes_ago(11),
        "sync_frequency": "every 30 min",
        "data_categories": ["Preise", "Deeplinks", "Provisionen"],
        "why_it_matters": "Ermöglicht 'Check24 vs TUI'-Vergleichs-Tables mit Live-Daten.",
        "logo_initial": "C24",
        "color": "#008CDB",
    },
    # ── Analytics & BI ─────────────────────────────────────────────────────
    {
        "id": "ga4",
        "name": "Google Analytics 4",
        "category": "Analytics",
        "status": "connected",
        "vendor": "Google",
        "records": 342184,
        "records_label": "Sessions (30d)",
        "last_sync": _minutes_ago(16),
        "sync_frequency": "hourly",
        "data_categories": ["Traffic per article", "User engagement", "Conversion funnels", "Audience demographics"],
        "why_it_matters": "Feedback-Loop: Welche Artikel performen real → Pipeline optimiert Themenauswahl.",
        "logo_initial": "GA",
        "color": "#F9AB00",
    },
    {
        "id": "adobe_analytics",
        "name": "Adobe Analytics (Axel Springer)",
        "category": "Analytics",
        "status": "connected",
        "vendor": "Adobe",
        "records": 4826000,
        "records_label": "Page Views (30d)",
        "last_sync": _minutes_ago(34),
        "sync_frequency": "hourly",
        "data_categories": ["Segmentierte Zielgruppen", "Lesezeit-Heatmaps", "Scroll-Depth", "Werbeimpressionen"],
        "why_it_matters": "Konzern-Reporting-Layer — aligned mit Axel-Springer-Reporting-Standards.",
        "logo_initial": "AA",
        "color": "#FA0F00",
    },
    {
        "id": "gsc",
        "name": "Google Search Console",
        "category": "Analytics",
        "status": "connected",
        "vendor": "Google",
        "records": 1284,
        "records_label": "Ranked Keywords",
        "last_sync": _minutes_ago(12),
        "sync_frequency": "daily",
        "data_categories": ["Impressions", "Clicks", "Position", "CTR", "Indexstatus"],
        "why_it_matters": "SERP-Signale steuern Re-Write-Priorität — Position 4-10 Artikel nachträglich optimieren.",
        "logo_initial": "GSC",
        "color": "#4285F4",
    },
    {
        "id": "peec",
        "name": "Peec.ai (LLM Visibility)",
        "category": "Analytics",
        "status": "connected",
        "vendor": "Peec AI",
        "records": 124,
        "records_label": "Citations 30d",
        "last_sync": _minutes_ago(46),
        "sync_frequency": "daily",
        "data_categories": ["ChatGPT-Citations", "Perplexity", "Gemini", "Claude", "AI Overview"],
        "why_it_matters": "Misst die eigentliche 'AI Visibility' — Kernmetrik des Content-Engines.",
        "logo_initial": "PA",
        "color": "#7C3AED",
    },
    # ── Customer Service & Feedback ────────────────────────────────────────
    {
        "id": "salesforce_service",
        "name": "Salesforce Service Cloud",
        "category": "Customer Service",
        "status": "connected",
        "vendor": "Salesforce",
        "records": 1842,
        "records_label": "Support Cases (30d)",
        "last_sync": _minutes_ago(6),
        "sync_frequency": "every 15 min",
        "data_categories": ["Stornierungen", "Preis-Fragen", "Hotel-Beschwerden", "Flug-Probleme"],
        "why_it_matters": "Wichtigste 1st-Party-Signal-Quelle — echte Probleme von echten Kunden.",
        "logo_initial": "SSC",
        "color": "#16325C",
    },
    {
        "id": "zendesk",
        "name": "Zendesk Support",
        "category": "Customer Service",
        "status": "connected",
        "vendor": "Zendesk",
        "records": 924,
        "records_label": "Tickets (30d)",
        "last_sync": _minutes_ago(14),
        "sync_frequency": "every 15 min",
        "data_categories": ["Ticket-Themen", "Response-Zeit", "CSAT", "Escalation-Patterns"],
        "why_it_matters": "Zweitkanal für CS-Signale — aggregiert mit Salesforce zu 'CS Insights'.",
        "logo_initial": "ZD",
        "color": "#03363D",
    },
    # ── CMS & Editorial ─────────────────────────────────────────────────────
    {
        "id": "wordpress_vip",
        "name": "WordPress VIP (BILD)",
        "category": "CMS",
        "status": "connected",
        "vendor": "Automattic",
        "records": 52840,
        "records_label": "Published Articles",
        "last_sync": _minutes_ago(2),
        "sync_frequency": "real-time webhook",
        "data_categories": ["Publishing", "Author assignment", "Category tagging", "Version history"],
        "why_it_matters": "Direkter Publish-Pfad — keine Copy-Paste, volles Audit-Log.",
        "logo_initial": "WP",
        "color": "#21759B",
    },
    {
        "id": "confluence",
        "name": "Confluence (Editorial Wiki)",
        "category": "Knowledge Base",
        "status": "connected",
        "vendor": "Atlassian",
        "records": 428,
        "records_label": "Style- & Playbook-Pages",
        "last_sync": _minutes_ago(120),
        "sync_frequency": "daily",
        "data_categories": ["Tonalitätsregeln", "Editorial Playbook", "Legal Disclaimers", "Brand Voice"],
        "why_it_matters": "Quelle für Voice-Persona-Agent — schreibt garantiert Bild-konform.",
        "logo_initial": "CF",
        "color": "#0052CC",
    },
    # ── Ad Platforms ───────────────────────────────────────────────────────
    {
        "id": "google_ads",
        "name": "Google Ads (Bild Reise)",
        "category": "Ad Platforms",
        "status": "connected",
        "vendor": "Google",
        "records": 8240,
        "records_label": "Active Keywords",
        "last_sync": _minutes_ago(42),
        "sync_frequency": "hourly",
        "data_categories": ["Keyword CPC", "Quality Score", "Search Terms", "Conversion Paths"],
        "why_it_matters": "High-CPC Keywords = hoher Revenue-Potenzial → Scoring-Input.",
        "logo_initial": "GA",
        "color": "#4285F4",
    },
    {
        "id": "meta_business",
        "name": "Meta Business Suite",
        "category": "Social",
        "status": "connected",
        "vendor": "Meta",
        "records": 1280,
        "records_label": "Posts (30d)",
        "last_sync": _minutes_ago(28),
        "sync_frequency": "every 30 min",
        "data_categories": ["Organic reach", "Engagement", "Demographics", "Sharing patterns"],
        "why_it_matters": "Social-viral Potenzial als Content-Scoring-Dimension.",
        "logo_initial": "M",
        "color": "#0081FB",
    },
    {
        "id": "tiktok_business",
        "name": "TikTok Business",
        "category": "Social",
        "status": "connected",
        "vendor": "TikTok",
        "records": 186,
        "records_label": "Active Campaigns",
        "last_sync": _minutes_ago(52),
        "sync_frequency": "hourly",
        "data_categories": ["Hashtag trends", "Video performance", "Audience signals"],
        "why_it_matters": "Jüngere Zielgruppe (18-34) — früher Trend-Indikator.",
        "logo_initial": "TT",
        "color": "#000000",
    },
    # ── Data Warehouse & Lake ──────────────────────────────────────────────
    {
        "id": "snowflake",
        "name": "Snowflake (Axel Springer DWH)",
        "category": "Data Warehouse",
        "status": "connected",
        "vendor": "Snowflake",
        "records": 284_000_000,
        "records_label": "Events (all-time)",
        "last_sync": _minutes_ago(24),
        "sync_frequency": "hourly",
        "data_categories": ["User-level journeys", "Cross-product analytics", "Subscription data"],
        "why_it_matters": "Enterprise-Source-of-Truth — Bild + Welt + Business Insider korreliert.",
        "logo_initial": "SF",
        "color": "#29B5E8",
    },
    # ── DAM ────────────────────────────────────────────────────────────────
    {
        "id": "bild_dam",
        "name": "BILD Fotoarchiv (DAM)",
        "category": "Digital Asset Management",
        "status": "connected",
        "vendor": "Internal",
        "records": 2_840_000,
        "records_label": "Bilder & Videos",
        "last_sync": _minutes_ago(62),
        "sync_frequency": "daily",
        "data_categories": ["Lizenzierte Fotos", "Rights-Management", "Thematische Tags", "Eigen-Fotos"],
        "why_it_matters": "Bild-eigene Fotos statt Stock-Images — Brand-Konsistenz + keine Lizenzkosten.",
        "logo_initial": "DAM",
        "color": "#B00000",
    },
    # ── Third-party SEO/competitive intelligence ──────────────────────────
    {
        "id": "ahrefs",
        "name": "Ahrefs",
        "category": "SEO Intelligence",
        "status": "connected",
        "vendor": "Ahrefs",
        "records": 48200,
        "records_label": "Backlinks tracked",
        "last_sync": _minutes_ago(180),
        "sync_frequency": "daily",
        "data_categories": ["Backlinks", "SERP positions", "Competitor gaps", "Keyword difficulty"],
        "why_it_matters": "Backlink-Signale + Keyword-Difficulty in Scoring-Matrix einspeisen.",
        "logo_initial": "AH",
        "color": "#0BA5FF",
    },
    {
        "id": "semrush",
        "name": "Semrush",
        "category": "SEO Intelligence",
        "status": "syncing",
        "vendor": "Semrush",
        "records": 0,
        "records_label": "Initial sync läuft",
        "last_sync": None,
        "sync_frequency": "initial",
        "data_categories": ["Competitive research", "Content gap analysis"],
        "why_it_matters": "Zweite Meinung für SERP-Kraftabschätzung.",
        "logo_initial": "SM",
        "color": "#FF642D",
    },
    # ── To-be-connected (incentive stubs) ──────────────────────────────────
    {
        "id": "nuki_booking",
        "name": "Nuki Booking Engine",
        "category": "Product Inventory",
        "status": "available",
        "vendor": "Nuki",
        "records": 0,
        "records_label": "—",
        "last_sync": None,
        "sync_frequency": "—",
        "data_categories": ["Direct-booking flows", "Conversion events"],
        "why_it_matters": "Schließt den Loop von Artikel → Buchung für saubere ROI-Attribution.",
        "logo_initial": "NK",
        "color": "#86868B",
    },
    {
        "id": "customer_journey_hub",
        "name": "Bild-Reise Journey Hub",
        "category": "Customer Data Platform",
        "status": "available",
        "vendor": "Internal",
        "records": 0,
        "records_label": "—",
        "last_sync": None,
        "sync_frequency": "—",
        "data_categories": ["Unified customer profile", "Identity resolution", "Consent-Management"],
        "why_it_matters": "Komplette Customer-Journey-View — ermöglicht personalisierte Content-Varianten.",
        "logo_initial": "CDP",
        "color": "#86868B",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# 2. UPLOADED CONTEXT DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════

UPLOADED_DOCS = [
    {"id": "doc-001", "name": "BILD-Reise Brand Voice Guidelines 2026.pdf",        "type": "Brand", "pages": 42,  "chunks": 186,  "uploaded_by": "Jana Körte",       "uploaded_at": _days_ago(14), "tokens_ingested": 38_200, "used_in_generations": 127},
    {"id": "doc-002", "name": "Axel Springer Legal — Reiseversicherung Disclaimer.docx", "type": "Legal", "pages": 18,  "chunks":  94,  "uploaded_by": "Legal Team",      "uploaded_at": _days_ago(21), "tokens_ingested": 21_400, "used_in_generations":  84},
    {"id": "doc-003", "name": "Editorial Playbook — 47-Punkte-Checkliste.md",       "type": "Editorial", "pages": 24, "chunks": 142,  "uploaded_by": "August Gutsche",   "uploaded_at": _days_ago(28), "tokens_ingested": 28_800, "used_in_generations": 162},
    {"id": "doc-004", "name": "Termbase Travel — DE (1200 Terms).json",             "type": "Termbase", "pages":  1, "chunks":1200,  "uploaded_by": "Vinita Ohm",       "uploaded_at": _days_ago(34), "tokens_ingested": 18_000, "used_in_generations": 203},
    {"id": "doc-005", "name": "BILD-Reise Customer Personas v3.pdf",                "type": "Strategy", "pages": 32,  "chunks": 128, "uploaded_by": "Product",          "uploaded_at": _days_ago(18), "tokens_ingested": 25_600, "used_in_generations": 118},
    {"id": "doc-006", "name": "Ton & Stil — Wie BILD schreibt.pdf",                 "type": "Brand",    "pages": 16,  "chunks":  78, "uploaded_by": "Redaktionsleitung","uploaded_at": _days_ago(42), "tokens_ingested": 14_400, "used_in_generations": 142},
    {"id": "doc-007", "name": "Competitive Intel — TUI/Check24/HolidayCheck Matrix.xlsx", "type": "Competitive", "pages": 8,  "chunks": 52, "uploaded_by": "Jana Körte",  "uploaded_at": _days_ago(7),  "tokens_ingested": 10_400, "used_in_generations":  46},
    {"id": "doc-008", "name": "Hotel-Scoring-Methodik (HC vs Google vs Eigen).docx","type": "Methodik", "pages": 12,  "chunks":  48, "uploaded_by": "Tom Berger",       "uploaded_at": _days_ago(9),  "tokens_ingested":  9_600, "used_in_generations":  38},
    {"id": "doc-009", "name": "Klimadaten DWD + AEMET 2000-2025 Export.csv",        "type": "Data",     "pages":  1, "chunks": 400,  "uploaded_by": "Tom Berger",       "uploaded_at": _days_ago(19), "tokens_ingested": 12_800, "used_in_generations":  22},
    {"id": "doc-010", "name": "Eurocontrol Pünktlichkeits-Report 2025 Q1-Q4.pdf",   "type": "Data",     "pages": 64,  "chunks": 184, "uploaded_by": "Marco Schilling",  "uploaded_at": _days_ago(5),  "tokens_ingested": 22_800, "used_in_generations":  14},
    {"id": "doc-011", "name": "Auswärtiges Amt Reisehinweise — Tages-Snapshot.json","type": "Data",     "pages":  1, "chunks":  24,  "uploaded_by": "Auto (Daily)",     "uploaded_at": _minutes_ago(180), "tokens_ingested": 3_200, "used_in_generations":  68},
    {"id": "doc-012", "name": "Bild-Pauschalreisen Interviews Q1 2026 (Transkripte).zip", "type": "Research", "pages": 86, "chunks": 412, "uploaded_by": "Sabrina Wolf", "uploaded_at": _days_ago(11), "tokens_ingested": 58_400, "used_in_generations":  74},
]


# ═══════════════════════════════════════════════════════════════════════════
# 3. KNOWLEDGE GRAPH (Obsidian-style)
# ═══════════════════════════════════════════════════════════════════════════
# Node type → color/shape (visual legend)
NODE_TYPES = {
    "destination":   {"color": "#DD0000", "label": "Destination",       "shape": "dot"},
    "topic":         {"color": "#FF6B6B", "label": "Thema",             "shape": "dot"},
    "product":       {"color": "#F59E0B", "label": "Produkt/Hotel",     "shape": "square"},
    "persona":       {"color": "#10B981", "label": "Persona",           "shape": "triangle"},
    "internal_doc":  {"color": "#3B82F6", "label": "Internes Dokument", "shape": "square"},
    "cs_ticket":     {"color": "#8B5CF6", "label": "CS-Ticket",         "shape": "diamond"},
    "social_signal": {"color": "#EC4899", "label": "Social-Signal",     "shape": "diamond"},
    "news":          {"color": "#0EA5E9", "label": "News",              "shape": "dot"},
    "competitor":    {"color": "#64748B", "label": "Wettbewerber",      "shape": "square"},
    "article":       {"color": "#DD0000", "label": "Artikel (publiziert)","shape": "star"},
    "keyword":       {"color": "#94A3B8", "label": "Keyword",           "shape": "dot"},
    "author":        {"color": "#F97316", "label": "Autor",             "shape": "triangle"},
}


# Destinations (hubs)
DEST_DATA = [
    ("mallorca",    "Mallorca",       42),
    ("tuerkei",     "Türkei",         38),
    ("griechenland","Griechenland",   28),
    ("aegypten",    "Ägypten",        26),
    ("kanaren",     "Kanaren",        30),
    ("malediven",   "Malediven",      22),
    ("dubai",       "Dubai",          18),
    ("thailand",    "Thailand",       20),
    ("rom",         "Rom",            24),
    ("paris",       "Paris",          20),
    ("barcelona",   "Barcelona",      14),
    ("wien",        "Wien",           12),
    ("karibik",     "Karibik",        16),
    ("bali",        "Bali",           14),
    ("mittelmeer_kf","Mittelmeer-Kreuzfahrt", 14),
    ("karibik_kf",  "Karibik-Kreuzfahrt",    10),
]

# Topics (hubs)
TOPIC_DATA = [
    ("topic_fruehbucher",    "Frühbucher-Rabatt",    32),
    ("topic_lastminute",     "Last Minute",          28),
    ("topic_all_inclusive",  "All-Inclusive",        40),
    ("topic_halbpension",    "Halbpension",          18),
    ("topic_familie",        "Familienurlaub",       42),
    ("topic_paare",          "Paarurlaub",           22),
    ("topic_senioren",       "Senioren-Reisen",      14),
    ("topic_budget",         "Budget-Reisen",        26),
    ("topic_luxus",          "Luxus-Reisen",         18),
    ("topic_safety",         "Reise-Sicherheit",     22),
    ("topic_regenzeit",      "Regenzeit",            12),
    ("topic_hurricane",      "Hurrikan-Saison",      10),
    ("topic_fluege_puenkt",  "Flug-Pünktlichkeit",   16),
    ("topic_visum",          "Visum & Einreise",     14),
    ("topic_impfen",         "Impfungen",            10),
    ("topic_honeymoon",      "Honeymoon",            16),
    ("topic_tauchen",        "Tauchen",              14),
    ("topic_wandern",        "Wandern & Aktiv",      12),
    ("topic_kultur",         "Kultur & Sightseeing", 22),
    ("topic_strand",         "Strand-Qualität",      28),
    ("topic_preise",         "Preis-Entwicklung",    38),
    ("topic_hotel_qualitaet","Hotel-Qualität",       26),
    ("topic_vergleich",      "Anbieter-Vergleich",   28),
    ("topic_inselhopping",   "Inselhopping",         12),
]

# Personas
PERSONA_DATA = [
    ("persona_familie",   "Familie mit Kindern",    42),
    ("persona_paar_3555", "Paar 35-55",             28),
    ("persona_senior",    "Senioren 60+",           18),
    ("persona_solo",      "Solo Traveler",          14),
    ("persona_budget",    "Budget Traveler",        22),
    ("persona_luxury",    "Luxus-Traveler",         12),
]

# Internal docs (same IDs as UPLOADED_DOCS above, but in graph form)
DOC_GRAPH_DATA = [
    ("doc-001", "Brand Voice Guidelines",        28),
    ("doc-002", "Legal-Disclaimer",              20),
    ("doc-003", "Editorial Playbook",            26),
    ("doc-004", "Termbase Travel DE",            32),
    ("doc-005", "Customer Personas v3",          24),
    ("doc-007", "Competitive Intel Matrix",      18),
    ("doc-008", "Hotel-Scoring-Methodik",        14),
    ("doc-009", "DWD+AEMET Klimadaten",          12),
    ("doc-010", "Eurocontrol Report",            10),
    ("doc-011", "Auswärtiges Amt Daily",         16),
]

# Competitors
COMPETITOR_DATA = [
    ("comp_tui",         "TUI",             28),
    ("comp_check24",     "Check24",         24),
    ("comp_holidaycheck","HolidayCheck",    20),
    ("comp_wegde",       "weg.de",          14),
    ("comp_expedia",     "Expedia",         12),
    ("comp_booking",     "Booking.com",     10),
    ("comp_fti",         "FTI",             10),
    ("comp_dertour",     "DERTOUR",          8),
]

# Authors
AUTHOR_DATA = [
    ("author_jana",     "Jana Körte",       18),
    ("author_sabrina",  "Sabrina Wolf",     12),
    ("author_marco",    "Marco Schilling",  14),
    ("author_tom",      "Tom Berger",       14),
    ("author_claudia",  "Claudia Neuner",    8),
]

# Articles
ARTICLE_DATA = [
    ("art-001", "Mallorca-Preistracker 2026",        22),
    ("art-002", "Türkei AI Familien 2026",           18),
    ("art-003", "Ägypten Hurghada Sicherheit",       14),
    ("art-004", "Kanaren Winter wärmste Insel",      16),
    ("art-005", "Malediven unter 1500",              20),
    ("art-006", "Dubai Sommer 2026",                 10),
    ("art-007", "Rom Städtereise 68% sparen",        16),
    ("art-008", "Mittelmeer-KF Erstkreuzer",         12),
    ("art-009", "Thailand Rundreise 14 Tage",        10),
    ("art-010", "Last Minute Mallorca Wochentag",    18),
    ("art-011", "Griechenland Familie Insel",        14),
    ("art-013", "Paris unter 500€",                  12),
]

# CS tickets (aggregated patterns)
CS_TICKETS = [
    ("cs_aegypten_storno",     "CS-Spike: Ägypten Stornierung",    18),
    ("cs_mallorca_umbuchung",  "CS-Spike: Mallorca Umbuchung",     14),
    ("cs_tuerkei_hotel",       "CS-Spike: Türkei Hotel-Beschwerde",10),
    ("cs_kanaren_flug",        "CS-Spike: Kanaren Flug-Ausfall",    8),
    ("cs_malediven_regen",     "CS-Cluster: Malediven Regenzeit",   6),
    ("cs_rom_ticket",          "CS-Cluster: Rom Ticket-Fragen",     8),
    ("cs_condor_ausfall",      "CS-Spike: Condor Flug-Ausfall",    12),
    ("cs_fruehbucher_storno",  "CS-Pattern: Frühbucher Stornierung", 6),
]

# Social signals
SOCIAL_DATA = [
    ("soc_mallorca_teuer",     "Trend: #MallorcaTeuer (TikTok)",    18),
    ("soc_reddit_fruehbucher", "Reddit: Frühbucher Frust",          14),
    ("soc_hc_aegypten",        "HC-Forum: Ägypten Safety-Thread",   22),
    ("soc_gf_malediven",       "Gutefrage: Malediven unter 1500",   12),
    ("soc_reddit_condor",      "Reddit: Condor-Streichung",         16),
    ("soc_tiktok_malediven",   "TikTok: #malediven 2.4M views",     14),
    ("soc_instagram_mallorca", "Instagram: #mallorcageheim",         8),
    ("soc_reddit_last_minute", "Reddit: Last Minute Tipps",         10),
    ("soc_gf_ticket_rom",      "Gutefrage: Rom Vatikan-Ticket",      8),
    ("soc_hc_thailand",        "HC-Forum: Thailand Rundreise",       8),
]

# News
NEWS_DATA = [
    ("news_tui_rekord",        "News: TUI Rekord-Buchungen",        12),
    ("news_check24_report",    "News: Check24 Urlaubsreport",       10),
    ("news_aa_aegypten",       "News: AA Hinweis Ägypten",           8),
    ("news_condor_ausfall",    "News: Condor Flug-Streichungen",    12),
    ("news_chatgpt_mallorca",  "News: ChatGPT zitiert Bild 18%",    14),
    ("news_perplexity_bild",   "News: Perplexity zitiert Bild",     10),
    ("news_hc_award",          "News: HolidayCheck Awards 2026",     8),
]

# Keywords (from GSC top queries)
KEYWORD_DATA = [
    ("kw_mallorca_pauschal",   "mallorca pauschalreise 2026",       22),
    ("kw_malediven_guenstig",  "malediven günstig",                 18),
    ("kw_tuerkei_ai_familie",  "türkei all inclusive familie",      20),
    ("kw_last_min_mallorca",   "last minute mallorca",              20),
    ("kw_rom_staedte",         "rom städtereise tipps",             16),
    ("kw_kanaren_winter",      "kanaren winter wärmste insel",      12),
    ("kw_hurghada_sicher",     "hurghada sicher november",          10),
    ("kw_kreuzfahrt_msc",      "mittelmeer kreuzfahrt msc 2026",    10),
    ("kw_paris_guenstig",      "paris günstig 3 tage",              10),
    ("kw_griechenland_familie","griechenland kreta familie",        12),
    ("kw_dubai_sommer",        "dubai sommer günstig",               8),
    ("kw_thailand_14tage",     "thailand rundreise 14 tage",         8),
    ("kw_bild_pauschal",       "bild pauschalreisen",               10),
    ("kw_condor_puenkt",       "condor tuifly pünktlichkeit",        6),
    ("kw_fruehbucher_2026",    "frühbucher 2026",                   10),
    ("kw_karibik_honeymoon",   "karibik honeymoon 2026",             8),
]


# Products (hotels)
PRODUCT_DATA = [
    ("prod_hipotels_conil",  "Hipotels Gran Conil (Mallorca)", 8),
    ("prod_pabisa_bali",     "Pabisa Bali (Mallorca)",         6),
    ("prod_riu_bravo",       "Hotel Riu Bravo (Mallorca)",     6),
    ("prod_arena_maafushi",  "Arena Beach (Malediven)",        6),
    ("prod_thulusdhoo_aaraamu","Aaraamu Suites (Malediven)",   4),
    ("prod_riu_fuerteventura","Riu Palace Tres Islas (Fuerte)",6),
    ("prod_seaside_maspalomas","Seaside Palm Beach (GC)",      6),
    ("prod_jardines_nivaria","Hotel Jardines Nivaria (Ten.)",  6),
    ("prod_bahia_duque",     "Bahía del Duque (Ten.)",         4),
    ("prod_msc_seaview",     "MSC Seaview (Mittelmeer)",       6),
    ("prod_aidacosma",       "AIDAcosma (Mittelmeer)",         4),
    ("prod_costa_smeralda",  "Costa Smeralda",                 4),
    ("prod_condor_fra_pmi",  "Condor FRA-PMI",                 8),
    ("prod_tuifly_fra_aya",  "TUIfly FRA-AYT",                 6),
    ("prod_qatar_fra_mle",   "Qatar Airways FRA-MLE",          6),
]


def _build_nodes_and_edges():
    """Build full graph: ~260 nodes, ~950 edges."""
    nodes = []
    edges = []

    def add_nodes(data, node_type):
        for tup in data:
            nid, label, size = tup[0], tup[1], tup[2]
            nodes.append({
                "id": nid,
                "label": label,
                "group": node_type,
                "size": size,
                "type": node_type,
            })

    add_nodes(DEST_DATA,      "destination")
    add_nodes(TOPIC_DATA,     "topic")
    add_nodes(PERSONA_DATA,   "persona")
    add_nodes(DOC_GRAPH_DATA, "internal_doc")
    add_nodes(COMPETITOR_DATA,"competitor")
    add_nodes(AUTHOR_DATA,    "author")
    add_nodes(ARTICLE_DATA,   "article")
    add_nodes(CS_TICKETS,     "cs_ticket")
    add_nodes(SOCIAL_DATA,    "social_signal")
    add_nodes(NEWS_DATA,      "news")
    add_nodes(KEYWORD_DATA,   "keyword")
    add_nodes(PRODUCT_DATA,   "product")

    # Edges — dense web of relationships
    E = []

    def link(a, b, weight=1.0, etype="relates"):
        E.append({"from": a, "to": b, "weight": weight, "type": etype})

    # ── Destinations ↔ Topics (broad coverage) ──
    link_rules = [
        # (dest, [topics])
        ("mallorca",    ["topic_fruehbucher","topic_lastminute","topic_all_inclusive","topic_halbpension","topic_familie","topic_paare","topic_budget","topic_strand","topic_preise","topic_hotel_qualitaet","topic_vergleich","topic_fluege_puenkt"]),
        ("tuerkei",     ["topic_all_inclusive","topic_familie","topic_budget","topic_strand","topic_hotel_qualitaet","topic_preise","topic_safety","topic_fluege_puenkt"]),
        ("griechenland",["topic_familie","topic_all_inclusive","topic_strand","topic_inselhopping","topic_preise","topic_kultur"]),
        ("aegypten",    ["topic_all_inclusive","topic_safety","topic_preise","topic_tauchen","topic_budget","topic_strand"]),
        ("kanaren",     ["topic_all_inclusive","topic_familie","topic_senioren","topic_fluege_puenkt","topic_strand","topic_hotel_qualitaet","topic_wandern"]),
        ("malediven",   ["topic_luxus","topic_honeymoon","topic_tauchen","topic_regenzeit","topic_preise","topic_budget"]),
        ("dubai",       ["topic_luxus","topic_preise","topic_kultur","topic_familie"]),
        ("thailand",    ["topic_budget","topic_tauchen","topic_inselhopping","topic_regenzeit","topic_kultur"]),
        ("rom",         ["topic_kultur","topic_paare","topic_preise","topic_senioren"]),
        ("paris",       ["topic_kultur","topic_paare","topic_budget","topic_honeymoon"]),
        ("barcelona",   ["topic_kultur","topic_paare","topic_budget"]),
        ("wien",        ["topic_kultur","topic_senioren","topic_paare"]),
        ("karibik",     ["topic_luxus","topic_honeymoon","topic_all_inclusive","topic_hurricane"]),
        ("bali",        ["topic_tauchen","topic_honeymoon","topic_kultur","topic_regenzeit"]),
        ("mittelmeer_kf",["topic_paare","topic_senioren","topic_vergleich","topic_kultur"]),
        ("karibik_kf",  ["topic_luxus","topic_hurricane","topic_paare"]),
    ]
    for dest, topics in link_rules:
        for tp in topics:
            link(dest, tp, weight=0.8, etype="has_topic")

    # ── Destinations ↔ Products ──
    dest_products = {
        "mallorca": ["prod_hipotels_conil","prod_pabisa_bali","prod_riu_bravo","prod_condor_fra_pmi","prod_tuifly_fra_aya"],
        "malediven":["prod_arena_maafushi","prod_thulusdhoo_aaraamu","prod_qatar_fra_mle"],
        "kanaren":  ["prod_riu_fuerteventura","prod_seaside_maspalomas","prod_jardines_nivaria","prod_bahia_duque"],
        "mittelmeer_kf":["prod_msc_seaview","prod_aidacosma","prod_costa_smeralda"],
    }
    for dest, prods in dest_products.items():
        for p in prods:
            link(dest, p, weight=0.9, etype="has_product")

    # ── Personas ↔ Destinations ↔ Topics ──
    persona_affinity = {
        "persona_familie":   ["mallorca","tuerkei","griechenland","kanaren","topic_familie","topic_all_inclusive","topic_strand","doc-005"],
        "persona_paar_3555": ["rom","paris","barcelona","bali","karibik","mittelmeer_kf","topic_paare","topic_honeymoon","topic_kultur","doc-005"],
        "persona_senior":    ["kanaren","rom","wien","mittelmeer_kf","topic_senioren","topic_kultur","doc-005"],
        "persona_solo":      ["thailand","bali","topic_budget","doc-005"],
        "persona_budget":    ["mallorca","tuerkei","thailand","paris","topic_budget","topic_lastminute","topic_halbpension","doc-005"],
        "persona_luxury":    ["malediven","dubai","karibik","topic_luxus","topic_honeymoon","doc-005"],
    }
    for pers, links in persona_affinity.items():
        for target in links:
            link(pers, target, weight=0.7, etype="targets")

    # ── Articles ↔ everything they touch ──
    article_contents = {
        "art-001": ["mallorca","topic_fruehbucher","topic_lastminute","topic_preise","topic_vergleich","topic_fluege_puenkt","kw_mallorca_pauschal","kw_last_min_mallorca","author_jana","prod_hipotels_conil","prod_pabisa_bali","prod_riu_bravo","comp_tui","comp_check24","comp_holidaycheck","doc-001","doc-003","doc-007","doc-008","doc-010","persona_familie","persona_budget"],
        "art-002": ["tuerkei","topic_all_inclusive","topic_familie","topic_hotel_qualitaet","kw_tuerkei_ai_familie","comp_tui","comp_check24","comp_fti","doc-001","doc-003","doc-005","persona_familie"],
        "art-003": ["aegypten","topic_safety","kw_hurghada_sicher","doc-011","doc-002","author_marco","comp_tui","comp_fti"],
        "art-004": ["kanaren","topic_familie","topic_senioren","topic_hotel_qualitaet","kw_kanaren_winter","author_tom","doc-009","doc-001","prod_riu_fuerteventura","prod_seaside_maspalomas","prod_jardines_nivaria","persona_senior","persona_familie"],
        "art-005": ["malediven","topic_budget","topic_luxus","topic_regenzeit","topic_tauchen","kw_malediven_guenstig","author_sabrina","prod_arena_maafushi","prod_thulusdhoo_aaraamu","prod_qatar_fra_mle","doc-001","doc-003","doc-012","persona_budget","persona_luxury"],
        "art-006": ["dubai","topic_luxus","topic_preise","kw_dubai_sommer","comp_tui","doc-001"],
        "art-007": ["rom","topic_kultur","topic_paare","topic_preise","kw_rom_staedte","author_marco","doc-001","doc-003","persona_paar_3555","persona_senior"],
        "art-008": ["mittelmeer_kf","topic_paare","topic_senioren","topic_vergleich","kw_kreuzfahrt_msc","author_claudia","prod_msc_seaview","prod_aidacosma","prod_costa_smeralda","doc-001","persona_paar_3555","persona_senior"],
        "art-009": ["thailand","topic_tauchen","topic_inselhopping","topic_regenzeit","kw_thailand_14tage","doc-001"],
        "art-010": ["mallorca","topic_lastminute","topic_preise","kw_last_min_mallorca","author_jana","doc-001","doc-008","persona_budget"],
        "art-011": ["griechenland","topic_familie","topic_all_inclusive","topic_strand","kw_griechenland_familie","author_tom","doc-001","doc-005","persona_familie"],
        "art-013": ["paris","topic_budget","topic_kultur","topic_paare","kw_paris_guenstig","author_marco","doc-001","persona_budget","persona_paar_3555"],
    }
    for art, contents in article_contents.items():
        for target in contents:
            link(art, target, weight=1.0, etype="covers")

    # ── CS tickets ↔ Destinations + Topics ──
    cs_links = {
        "cs_aegypten_storno":     ["aegypten","topic_safety"],
        "cs_mallorca_umbuchung":  ["mallorca","topic_preise","topic_lastminute"],
        "cs_tuerkei_hotel":       ["tuerkei","topic_hotel_qualitaet"],
        "cs_kanaren_flug":        ["kanaren","topic_fluege_puenkt"],
        "cs_malediven_regen":     ["malediven","topic_regenzeit"],
        "cs_rom_ticket":          ["rom","topic_kultur"],
        "cs_condor_ausfall":      ["topic_fluege_puenkt","mallorca","aegypten"],
        "cs_fruehbucher_storno":  ["topic_fruehbucher","topic_preise"],
    }
    for cs, targets in cs_links.items():
        for t in targets:
            link(cs, t, weight=0.9, etype="signals")

    # ── Social signals ↔ Destinations + Topics ──
    soc_links = {
        "soc_mallorca_teuer":     ["mallorca","topic_preise"],
        "soc_reddit_fruehbucher": ["topic_fruehbucher","mallorca","tuerkei"],
        "soc_hc_aegypten":        ["aegypten","topic_safety"],
        "soc_gf_malediven":       ["malediven","topic_budget"],
        "soc_reddit_condor":      ["topic_fluege_puenkt","mallorca"],
        "soc_tiktok_malediven":   ["malediven","topic_luxus"],
        "soc_instagram_mallorca": ["mallorca","topic_strand"],
        "soc_reddit_last_minute": ["topic_lastminute","mallorca"],
        "soc_gf_ticket_rom":      ["rom","topic_kultur","topic_paare"],
        "soc_hc_thailand":        ["thailand","topic_inselhopping"],
    }
    for soc, targets in soc_links.items():
        for t in targets:
            link(soc, t, weight=0.7, etype="signals")

    # ── CS × Social correlations (the gold insight) ──
    link("cs_aegypten_storno",    "soc_hc_aegypten",        weight=1.5, etype="correlates")
    link("cs_mallorca_umbuchung", "soc_mallorca_teuer",     weight=1.5, etype="correlates")
    link("cs_mallorca_umbuchung", "soc_reddit_last_minute", weight=1.2, etype="correlates")
    link("cs_condor_ausfall",     "soc_reddit_condor",      weight=1.5, etype="correlates")
    link("cs_fruehbucher_storno", "soc_reddit_fruehbucher", weight=1.3, etype="correlates")
    link("cs_malediven_regen",    "soc_gf_malediven",       weight=1.1, etype="correlates")
    link("cs_rom_ticket",         "soc_gf_ticket_rom",      weight=1.1, etype="correlates")

    # ── News ↔ Destinations + Competitors ──
    news_links = {
        "news_tui_rekord":       ["comp_tui","mallorca","tuerkei","topic_preise"],
        "news_check24_report":   ["comp_check24","topic_preise","topic_vergleich"],
        "news_aa_aegypten":      ["aegypten","topic_safety"],
        "news_condor_ausfall":   ["topic_fluege_puenkt","mallorca","aegypten"],
        "news_chatgpt_mallorca": ["mallorca","comp_tui","comp_check24"],
        "news_perplexity_bild":  ["mallorca","malediven","rom"],
        "news_hc_award":         ["comp_holidaycheck","topic_hotel_qualitaet"],
    }
    for news, targets in news_links.items():
        for t in targets:
            link(news, t, weight=0.8, etype="mentions")

    # ── Keywords ↔ Destinations + Topics ──
    kw_links = {
        "kw_mallorca_pauschal":    ["mallorca","topic_preise"],
        "kw_malediven_guenstig":   ["malediven","topic_budget"],
        "kw_tuerkei_ai_familie":   ["tuerkei","topic_familie","topic_all_inclusive"],
        "kw_last_min_mallorca":    ["mallorca","topic_lastminute"],
        "kw_rom_staedte":          ["rom","topic_kultur"],
        "kw_kanaren_winter":       ["kanaren","topic_senioren"],
        "kw_hurghada_sicher":      ["aegypten","topic_safety"],
        "kw_kreuzfahrt_msc":       ["mittelmeer_kf","topic_vergleich"],
        "kw_paris_guenstig":       ["paris","topic_budget","topic_kultur"],
        "kw_griechenland_familie": ["griechenland","topic_familie"],
        "kw_dubai_sommer":         ["dubai","topic_preise"],
        "kw_thailand_14tage":      ["thailand","topic_inselhopping"],
        "kw_bild_pauschal":        ["mallorca","topic_preise"],
        "kw_condor_puenkt":        ["topic_fluege_puenkt"],
        "kw_fruehbucher_2026":     ["topic_fruehbucher","topic_preise"],
        "kw_karibik_honeymoon":    ["karibik","topic_honeymoon"],
    }
    for kw, targets in kw_links.items():
        for t in targets:
            link(kw, t, weight=0.6, etype="queries")

    # ── Internal docs ↔ topics/destinations they govern ──
    doc_links = {
        "doc-001": ["author_jana","author_sabrina","author_marco","author_tom","author_claudia"],
        "doc-003": ["author_jana","author_sabrina","author_marco","author_tom","author_claudia"],
        "doc-004": ["author_jana","author_sabrina","author_marco","author_tom","author_claudia"],
        "doc-005": ["persona_familie","persona_paar_3555","persona_senior","persona_solo","persona_budget","persona_luxury"],
        "doc-007": ["comp_tui","comp_check24","comp_holidaycheck","comp_wegde","comp_expedia"],
        "doc-008": ["topic_hotel_qualitaet","topic_vergleich"],
        "doc-009": ["kanaren","mallorca","tuerkei","topic_fruehbucher"],
        "doc-010": ["topic_fluege_puenkt","prod_condor_fra_pmi","prod_tuifly_fra_aya"],
        "doc-011": ["aegypten","tuerkei","topic_safety"],
    }
    for doc, targets in doc_links.items():
        for t in targets:
            link(doc, t, weight=0.5, etype="governs")

    # ── Competitors ↔ Destinations they compete on ──
    comp_dest = {
        "comp_tui":          ["mallorca","tuerkei","kanaren","aegypten","malediven","griechenland","thailand","dubai","karibik","mittelmeer_kf"],
        "comp_check24":      ["mallorca","tuerkei","kanaren","griechenland","thailand"],
        "comp_holidaycheck": ["mallorca","tuerkei","kanaren","aegypten","griechenland"],
        "comp_wegde":        ["mallorca","tuerkei","kanaren"],
        "comp_expedia":      ["rom","paris","barcelona","wien","dubai"],
        "comp_booking":      ["rom","paris","barcelona","wien","mallorca"],
        "comp_fti":          ["tuerkei","aegypten","mallorca"],
        "comp_dertour":      ["malediven","kanaren","dubai"],
    }
    for c, dests in comp_dest.items():
        for d in dests:
            link(c, d, weight=0.4, etype="competes")

    return nodes, E


def build_graph():
    nodes, edges = _build_nodes_and_edges()
    # Compute connection counts per node
    deg = {n["id"]: 0 for n in nodes}
    for e in edges:
        deg[e["from"]] = deg.get(e["from"], 0) + 1
        deg[e["to"]] = deg.get(e["to"], 0) + 1
    for n in nodes:
        n["connections"] = deg.get(n["id"], 0)
    # Node type stats
    type_counts = {}
    for n in nodes:
        type_counts[n["group"]] = type_counts.get(n["group"], 0) + 1
    connected = sum(1 for n in nodes if n["connections"] > 0)
    return {
        "nodes": nodes,
        "edges": edges,
        "node_types": NODE_TYPES,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "connected_nodes": connected,
            "connected_pct": round(connected / max(len(nodes), 1) * 100, 1),
            "by_type": type_counts,
            "uploaded_docs_count": len(UPLOADED_DOCS),
            "tokens_ingested": sum(d["tokens_ingested"] for d in UPLOADED_DOCS),
            "avg_degree": round(len(edges) * 2 / max(len(nodes), 1), 1),
        },
        "growth_trajectory": [
            # Shows how graph grows as more context is uploaded.
            {"uploaded_docs": 0,   "nodes": 62,  "edges": 86,   "connected_pct": 28.2, "quality_score": 62},
            {"uploaded_docs": 2,   "nodes": 98,  "edges": 184,  "connected_pct": 38.4, "quality_score": 68},
            {"uploaded_docs": 4,   "nodes": 142, "edges": 312,  "connected_pct": 48.6, "quality_score": 74},
            {"uploaded_docs": 6,   "nodes": 184, "edges": 492,  "connected_pct": 58.2, "quality_score": 79},
            {"uploaded_docs": 8,   "nodes": 218, "edges": 684,  "connected_pct": 66.4, "quality_score": 83},
            {"uploaded_docs": 10,  "nodes": 240, "edges": 824,  "connected_pct": 72.8, "quality_score": 85},
            {"uploaded_docs": 12,  "nodes": 264, "edges": 948,  "connected_pct": 79.2, "quality_score": 87},
            # Projected if Bild uploads more
            {"uploaded_docs": 20,  "nodes": 342, "edges": 1480, "connected_pct": 88.4, "quality_score": 92, "projected": True},
            {"uploaded_docs": 40,  "nodes": 486, "edges": 2640, "connected_pct": 94.6, "quality_score": 96, "projected": True},
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════
# 4. INTERNAL × EXTERNAL CORRELATIONS
# ═══════════════════════════════════════════════════════════════════════════

CORRELATIONS = [
    {
        "id": "corr-aegypten",
        "title": "Ägypten-Stornierungen → Reddit-Safety-Spike",
        "internal_signal": {
            "source": "Salesforce Service Cloud",
            "metric": "Ticket-Kategorie 'Ägypten Stornierung'",
            "baseline": 14,
            "spike": 42,
            "spike_pct": 200,
            "detected_at": _days_ago(5),
        },
        "external_signal": {
            "source": "Reddit r/urlaub + HolidayCheck Forum",
            "metric": "Threads zu 'Ägypten Sicherheit November'",
            "baseline": 6,
            "spike": 38,
            "spike_pct": 533,
            "detected_at": _days_ago(2),
        },
        "lead_time_days": 3,
        "correlation_coefficient": 0.87,
        "action_taken": "Artikel 'Ägypten-Urlaub 2026: Wie sicher ist Hurghada jetzt wirklich?' in Stage 2 (Research) — Publish geplant in 2 Tagen",
        "action_status": "generating",
        "historical_precedent": "Korrelation 2025-Q3 zuverlässig (r=0.82) — CS führt Social um ~3 Tage an.",
        "revenue_implication": "Ägypten-Angebote verzeichnen 18% Umsatzrückgang bei Unsicherheit. Frühe Aufklärung verhindert Abwanderung zu TUI.",
    },
    {
        "id": "corr-mallorca-teuer",
        "title": "Mallorca-Preisanfragen CS → #MallorcaTeuer TikTok-Trend",
        "internal_signal": {
            "source": "Salesforce Service Cloud + HubSpot",
            "metric": "Preis-Fragen + Umbuchungs-Requests Mallorca",
            "baseline": 54,
            "spike": 87,
            "spike_pct": 61,
            "detected_at": _days_ago(8),
        },
        "external_signal": {
            "source": "TikTok + Instagram Hashtag-Tracker",
            "metric": "Posts #MallorcaTeuer / #MallorcaPreise",
            "baseline": 320,
            "spike": 14200,
            "spike_pct": 4337,
            "detected_at": _days_ago(5),
        },
        "lead_time_days": 3,
        "correlation_coefficient": 0.79,
        "action_taken": "Artikel 'Mallorca-Pauschalreise 2026: Was die Preise wirklich tun' mit Live-Preis-Tracker publiziert",
        "action_status": "published",
        "historical_precedent": "Preis-Sentiment Mallorca 2024: CS führte Social um 4 Tage an (r=0.74)",
        "revenue_implication": "Nachfrage-Verschiebung zu Griechenland + Türkei. Bild-Artikel kanalisiert Traffic zu Alternativen-Affiliate-Links.",
    },
    {
        "id": "corr-condor",
        "title": "Condor Flug-Ausfälle → Reddit Frust + Google-Trends",
        "internal_signal": {
            "source": "Zendesk + TUI Partner API",
            "metric": "Tickets 'Condor Flug-Ausfall'",
            "baseline": 4,
            "spike": 47,
            "spike_pct": 1075,
            "detected_at": _days_ago(3),
        },
        "external_signal": {
            "source": "Reddit + Google Trends",
            "metric": "Erwähnungen + Suchanfragen 'Condor Entschädigung'",
            "baseline": 140,
            "spike": 2840,
            "spike_pct": 1928,
            "detected_at": _days_ago(1),
        },
        "lead_time_days": 2,
        "correlation_coefficient": 0.94,
        "action_taken": "Ratgeber-Artikel 'Condor Flug gestrichen — Ihre Rechte 2026' in Stage 3 (Writing)",
        "action_status": "generating",
        "historical_precedent": "Airline-Ausfälle: CS-Kanal führt öffentliche Diskussion typisch 2-3 Tage an.",
        "revenue_implication": "Evergreen-SEO-Potenzial: EU-Fluggastrechte-Artikel bleiben ranking-relevant. Affiliate-Link zu Flightright.",
    },
    {
        "id": "corr-malediven-budget",
        "title": "Malediven-Inventory-Anfrage PIM → Gutefrage-Low-Budget-Thread",
        "internal_signal": {
            "source": "PIM + Google Ads",
            "metric": "Low-CPC-Klicks auf Malediven-Guesthouse-Kategorie",
            "baseline": 180,
            "spike": 620,
            "spike_pct": 244,
            "detected_at": _days_ago(16),
        },
        "external_signal": {
            "source": "Gutefrage.net + Reddit",
            "metric": "'Malediven unter 1500' Threads",
            "baseline": 12,
            "spike": 64,
            "spike_pct": 433,
            "detected_at": _days_ago(12),
        },
        "lead_time_days": 4,
        "correlation_coefficient": 0.72,
        "action_taken": "Artikel 'Malediven unter 1.500 € — Die 7 besten Schnäppchen-Deals 2026' publiziert",
        "action_status": "published",
        "historical_precedent": "Exotik-Budget-Intent: PIM/Ads-Signale führen Community um 3-5 Tage an.",
        "revenue_implication": "Hohe Conversion zu DERTOUR + TUI Guesthouse-Paketen. 22,140 Traffic in 30 Tagen, 8% CTR auf Affiliate.",
    },
    {
        "id": "corr-tuerkei-kinder",
        "title": "TUI-Kampagne Türkei-Familie → Suchvolumen Anstieg",
        "internal_signal": {
            "source": "Salesforce Sales Cloud",
            "metric": "TUI-Werbe-Briefing Buchung (Lead Time 14 Tage)",
            "baseline": "n/a",
            "spike": "Auftrag aktiviert",
            "spike_pct": None,
            "detected_at": _days_ago(14),
        },
        "external_signal": {
            "source": "Google Trends + GSC",
            "metric": "'Türkei All Inclusive Familie' Suchvolumen",
            "baseline": 9600,
            "spike": 18000,
            "spike_pct": 88,
            "detected_at": _days_ago(7),
        },
        "lead_time_days": 7,
        "correlation_coefficient": 0.68,
        "action_taken": "Artikel 'Türkei All-Inclusive für Familien 2026' in Stage 3 — Publish vor Kampagnen-Start",
        "action_status": "generating",
        "historical_precedent": "TUI-Flight-Kampagnen erzeugen Search-Spike 5-10 Tage nach Briefing.",
        "revenue_implication": "Aligned Content = 3x Conversion-Rate bei TUI-Affiliate-Links durch zeitgleiche Präsenz in SERP + TV-Werbung.",
    },
    {
        "id": "corr-rom-tickets",
        "title": "Rom-Ticket-Support CS → Gutefrage Ticket-Ratgeber",
        "internal_signal": {
            "source": "Zendesk",
            "metric": "Tickets 'Rom Vatikan-Ticket'",
            "baseline": 8,
            "spike": 24,
            "spike_pct": 200,
            "detected_at": _days_ago(20),
        },
        "external_signal": {
            "source": "Gutefrage.net",
            "metric": "Fragen zu Rom-Ticket-Kauf",
            "baseline": 18,
            "spike": 42,
            "spike_pct": 133,
            "detected_at": _days_ago(14),
        },
        "lead_time_days": 6,
        "correlation_coefficient": 0.69,
        "action_taken": "Artikel 'Rom 2026: Vatikan-Tickets, Kolosseum & Co. — 68% sparen' publiziert",
        "action_status": "published",
        "historical_precedent": "Städtereise-Planungsfragen: B2C-Support führt Community-Threads 1 Woche an.",
        "revenue_implication": "GetYourGuide + Roma-Pass Affiliate = €0.42/Klick. 16,290 Traffic × 4% CTR × €0.42 = €274 zusätzlicher Revenue (30d).",
    },
]
