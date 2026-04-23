#!/usr/bin/env python3
"""
Build a standalone BILD Pauschalreisen Content Engine demo HTML.

Injects comprehensive Bild Pauschalreisen mock data into the dashboard template
by replacing the __DASHBOARD_DATA__ placeholder with a rich JSON blob and
appends an offline-mode fetch interceptor so the dashboard renders the same
pipeline a live Supabase+backend deployment would.

Usage:
    python3 build_demo.py
    # outputs: bild_pauschalreisen_demo.html
"""
from __future__ import annotations
import json
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

HERE = Path(__file__).parent
TEMPLATE = HERE.parent / "template" / "dashboard_template.html"
OUTPUT = HERE.parent.parent / "bild_pauschalreisen_demo.html"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from articles import all_articles  # noqa: E402

# ─── Bild Pauschalreisen domain model ────────────────────────────────────────
# Category keys map onto the template's existing keys for visual compatibility:
#   blood_pressure  →  Strand & All-Inclusive
#   pain_tens       →  Städtereisen & Kultur
#   infrarot        →  Fernreisen & Exotik
#   menstrual       →  Kreuzfahrten & Luxus

DESTINATIONS = [
    # (name, category, market_share)
    ("Mallorca", "blood_pressure", 18.2),
    ("Türkei (Antalya)", "blood_pressure", 14.8),
    ("Griechenland (Kreta)", "blood_pressure", 9.4),
    ("Ägypten (Hurghada)", "blood_pressure", 8.1),
    ("Kanaren (Gran Canaria)", "blood_pressure", 7.6),
    ("Tunesien", "blood_pressure", 3.2),
    ("Rom", "pain_tens", 6.1),
    ("Paris", "pain_tens", 5.4),
    ("Barcelona", "pain_tens", 4.8),
    ("Wien", "pain_tens", 3.9),
    ("Lissabon", "pain_tens", 2.7),
    ("Malediven", "infrarot", 4.2),
    ("Dubai", "infrarot", 3.8),
    ("Thailand", "infrarot", 3.1),
    ("Bali", "infrarot", 2.4),
    ("Mexiko (Cancún)", "infrarot", 1.9),
    ("Mittelmeer-Kreuzfahrt", "menstrual", 3.4),
    ("Karibik-Kreuzfahrt", "menstrual", 2.8),
    ("Nordland-Kreuzfahrt", "menstrual", 1.6),
    ("Flusskreuzfahrt Donau", "menstrual", 1.2),
]

COMPETITORS = [
    # (brand, count, positive, neutral, negative)
    ("TUI", 834, 412, 358, 64),
    ("Check24", 612, 298, 276, 38),
    ("HolidayCheck", 487, 252, 204, 31),
    ("weg.de", 356, 178, 158, 20),
    ("ab-in-den-urlaub", 298, 141, 138, 19),
    ("Expedia", 243, 98, 128, 17),
    ("Booking.com", 412, 187, 205, 20),
    ("FTI", 187, 84, 91, 12),
    ("DERTOUR", 142, 68, 68, 6),
    ("Lidl Reisen", 96, 41, 48, 7),
]

SOURCES = {
    "reddit":        {"label": "Reddit (r/reisen, r/urlaub)", "count": 428},
    "gutefrage":     {"label": "Gutefrage.net",               "count": 312},
    "holidaycheck_forum": {"label": "HolidayCheck Forum",     "count": 287},
    "tripadvisor":   {"label": "TripAdvisor Forum",           "count": 234},
    "youtube":       {"label": "YouTube (Travel-Vlogs)",      "count": 198},
    "instagram":     {"label": "Instagram (#pauschalurlaub)", "count": 164},
    "tiktok":        {"label": "TikTok (#urlaub)",            "count": 132},
    "exa":           {"label": "News (Exa Search)",           "count": 86},
    "serper":        {"label": "Google (Top-Ergebnisse)",     "count": 71},
    "google_reviews": {"label": "Google Reviews",             "count": 58},
}

def _now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "+00:00"

def _days_ago(n):
    return (datetime.utcnow() - timedelta(days=n)).replace(microsecond=0).isoformat() + "+00:00"


# ─── Build content opportunities (CONTENT CREATION TAB — the hero) ──────────

CONTENT_OPPORTUNITIES = [
    {
        "source_item_id": "op-001",
        "topic": "Mallorca 2026: Preise steigen um 14% — lohnt sich Frühbucher-Rabatt noch?",
        "category": "blood_pressure",
        "gap_score": 9.4,
        "source": "HolidayCheck Forum",
        "url": "https://www.holidaycheck.de/forum/mallorca-preise-2026",
        "content_snippet": "Nutzer diskutieren die Preisentwicklung auf Mallorca für die Saison 2026. Frage: Lohnt sich Frühbucher wirklich oder lastminute günstiger? Konkrete Zahlenvergleiche gesucht.",
        "keywords": ["Mallorca Pauschalreise 2026", "Frühbucher-Rabatt", "Preisvergleich TUI Check24", "Last Minute Mallorca"],
        "llm_opportunity": "High-intent SERP-Gap: Bild kann mit exklusiven Daten-Comparisons (TUI/Check24/Expedia) punkten. Potenzial: 28k/mo Traffic (KW 'mallorca pauschalreise').",
        "intent": "transactional",
        "emotion": "frustration",
        "answer_count": 0,
        "key_insight": "0 echte Preisvergleiche in Top-10-SERP; reine Affiliate-Seiten dominieren.",
        "device_relevance_score": 0.92,
        "product_mentions": ["Mallorca", "TUI", "Check24"],
        "discovered_week": "2026-04-14",
        "suggested_title": "Mallorca-Pauschalreise 2026: Was die Preise wirklich tun — und wann Sie jetzt buchen sollten",
        "content_brief": "Datenbasierter Vergleich: 300+ reale Angebote von TUI, Check24, HolidayCheck, weg.de. Frühbucher vs. Last Minute vs. Restplätze. Infografik zur Preisentwicklung seit 2020. Bild-exklusive Daten-Story mit Hotel-Verfügbarkeit Juni–September 2026.",
        "search_intent": "transactional",
        "article_id": "art-001",
        "article_status": "completed",
        "article_headline": "Mallorca-Pauschalreise 2026: Was die Preise wirklich tun — und wann Sie jetzt buchen sollten",
    },
    {
        "source_item_id": "op-002",
        "topic": "Türkei All-Inclusive: Welches Hotel für Familie mit 2 Kindern bis 5.000€?",
        "category": "blood_pressure",
        "gap_score": 9.1,
        "source": "Reddit (r/reisen)",
        "url": "https://www.reddit.com/r/reisen/comments/tuerkei-ai-familie",
        "content_snippet": "Familie sucht konkrete Hotel-Empfehlung für Antalya/Side All-Inclusive bis 5000€. Listicles auf Seite 1 zu oberflächlich — 'was ist der Unterschied zwischen den Hotels wirklich?'",
        "keywords": ["Türkei All Inclusive Familie", "Side Hotel", "Antalya Familienhotel", "günstige Familienreise Türkei"],
        "llm_opportunity": "Perfect-Match-Tool angel: interaktiver Familien-Filter mit Hotel-Details (Pool, Wasserrutsche, Kids Club). Rankt in 14 Tagen ganz oben.",
        "intent": "commercial",
        "emotion": "confusion",
        "answer_count": 2,
        "key_insight": "Klickstarke B2C-Frage mit hoher AI-Sichtbarkeit — ChatGPT/Perplexity liefern schwache Antworten.",
        "device_relevance_score": 0.88,
        "product_mentions": ["Türkei", "Antalya", "Side"],
        "discovered_week": "2026-04-14",
        "suggested_title": "Türkei All-Inclusive für Familien 2026: Die 12 besten Hotels bis 5.000€ im Test",
        "content_brief": "Ranking mit 12 realen Hotels (Side, Antalya, Belek, Alanya). Preis pro Nacht pro Person, Kids-Features, Strand-Zugang, Bewertung HolidayCheck+Google. Buchbarkeit über TUI/Check24. Eigene Bild-Family-Test-Skala.",
        "search_intent": "commercial",
        "article_id": "art-002",
        "article_status": "generating",
        "article_headline": "Türkei All-Inclusive für Familien 2026: Die 12 besten Hotels bis 5.000€ im Test",
    },
    {
        "source_item_id": "op-003",
        "topic": "Ägypten Hurghada — sicher im November 2026? Aktuelle Lage + Reisewarnungen",
        "category": "blood_pressure",
        "gap_score": 8.9,
        "source": "Gutefrage.net",
        "url": "https://www.gutefrage.net/frage/aegypten-hurghada-sicher-2026",
        "content_snippet": "Viele Nutzerfragen zu aktueller Reise-Sicherheit Ägypten Nov/Dez 2026. Auswärtiges Amt-Infos unklar. Bild kann hier mit Ticker-Updates und Interviews mit TUI/FTI-Reiseleitern punkten.",
        "keywords": ["Hurghada sicher", "Ägypten Reisewarnung 2026", "Hurghada November", "Sharm el-Sheikh Sicherheit"],
        "llm_opportunity": "News-hook + Evergreen Ratgeber. Bild-Vorteil: Recherche-Netzwerk vor Ort, Zitate von Reise-Experten.",
        "intent": "informational",
        "emotion": "anxiety",
        "answer_count": 1,
        "key_insight": "Tägliche News-Überschneidung mit Pauschalreisen — hohe SEO-Priorität.",
        "device_relevance_score": 0.76,
        "product_mentions": ["Hurghada", "Ägypten", "Sharm el-Sheikh"],
        "discovered_week": "2026-04-14",
        "suggested_title": "Ägypten-Urlaub 2026: Wie sicher ist Hurghada jetzt wirklich? — Die aktuelle Lage erklärt",
        "content_brief": "Live-Update-Format (wird wöchentlich aktualisiert). Quellen: Auswärtiges Amt, DEHOGA Ägypten, TUI-Sicherheitsstab, Interviews mit Reiseleitern vor Ort. Karten-Grafik: rote Zonen vs. Touristen-Hotspots.",
        "search_intent": "informational",
        "article_id": "art-003",
        "article_status": "pending",
        "article_headline": None,
    },
    {
        "source_item_id": "op-004",
        "topic": "Kanaren im Winter — welche Insel ist die wärmste im Januar?",
        "category": "blood_pressure",
        "gap_score": 8.6,
        "source": "HolidayCheck Forum",
        "url": "https://www.holidaycheck.de/forum/kanaren-winter-waermste-insel",
        "content_snippet": "Winterflüchtlinge vergleichen Fuerteventura, Gran Canaria, Teneriffa, Lanzarote für Januar. Suche nach Daten: Durchschnitts-Temp + Sonnenstunden + Windstärke.",
        "keywords": ["Kanaren Winter", "wärmste Kanareninsel Januar", "Fuerteventura vs Gran Canaria", "Winter Pauschalreise"],
        "llm_opportunity": "Daten-Story mit DWD-Klimadaten + Bild-exklusive Hotel-Top-5 pro Insel.",
        "intent": "commercial",
        "emotion": "curiosity",
        "answer_count": 3,
        "key_insight": "Hohe Conversion-Rate bei Winter-Flüchtlingen 50+.",
        "device_relevance_score": 0.83,
        "product_mentions": ["Fuerteventura", "Gran Canaria", "Teneriffa", "Lanzarote"],
        "discovered_week": "2026-04-14",
        "suggested_title": "Kanaren im Januar 2027: Das ist die wärmste Insel — plus die 5 besten Hotels je Insel",
        "content_brief": "Klima-Ranking (25 Jahre DWD-Daten). Hotel-Liste mit Preis, Strand, Wellness-Bereich. Interaktive Karte.",
        "search_intent": "commercial",
        "article_id": "art-004",
        "article_status": "completed",
        "article_headline": "Kanaren im Januar 2027: Das ist die wärmste Insel — plus die 5 besten Hotels je Insel",
    },
    {
        "source_item_id": "op-005",
        "topic": "Malediven günstig — gibt es Pauschalreisen unter 1.500€ pro Person?",
        "category": "infrarot",
        "gap_score": 8.4,
        "source": "Reddit (r/urlaub)",
        "url": "https://www.reddit.com/r/urlaub/comments/malediven-guenstig",
        "content_snippet": "Frage nach günstigsten Malediven-Angeboten. Guest-Houses vs. Resorts. Wie findet man Deal unter 1500€ / Person?",
        "keywords": ["Malediven günstig", "Malediven unter 1500", "Malediven Guesthouse", "günstige Inselhopping"],
        "llm_opportunity": "Exklusive Deal-Recherche + Insider-Tipps. Bild-tauglicher Emotional Pull.",
        "intent": "transactional",
        "emotion": "hope",
        "answer_count": 4,
        "key_insight": "Niedrige Konkurrenz bei Long-Tail 'Malediven unter 1500'.",
        "device_relevance_score": 0.81,
        "product_mentions": ["Malediven", "Male", "Inselhopping"],
        "discovered_week": "2026-04-14",
        "suggested_title": "Malediven unter 1.500 € — ja, das geht wirklich: Die 7 besten Schnäppchen-Deals 2026",
        "content_brief": "Real existierende Angebote (TUI, DERTOUR, FTI). Preise/Nacht, Include-Liste, Flugzeit, Beach vs. Guesthouse. Bild-exklusiv: Kontakt zu 3 lokalen Tauchbasen.",
        "search_intent": "transactional",
        "article_id": "art-005",
        "article_status": "completed",
        "article_headline": "Malediven unter 1.500 € — ja, das geht wirklich: Die 7 besten Schnäppchen-Deals 2026",
    },
    {
        "source_item_id": "op-006",
        "topic": "Dubai im Sommer — ist es bei 45 Grad überhaupt auszuhalten?",
        "category": "infrarot",
        "gap_score": 8.2,
        "source": "TripAdvisor Forum",
        "url": "https://www.tripadvisor.de/forum/dubai-sommer",
        "content_snippet": "Nutzer fragen nach Dubai-Urlaub im Juli/August. Hitze-Management in Hotels, Ausflügen, Poolbereichen. Bild kann Insider-Tipps liefern.",
        "keywords": ["Dubai Sommer", "Dubai Juli Hitze", "Dubai Pauschalreise Sommer", "Dubai günstig"],
        "llm_opportunity": "Contrarian-Angle: 'Dubai im Sommer ist besser als Sie denken' mit Daten zu Indoor-Attraktionen + günstigere Preise.",
        "intent": "informational",
        "emotion": "curiosity",
        "answer_count": 2,
        "key_insight": "Sommer-Dubai-Angebote 40% günstiger — Story-Opportunity.",
        "device_relevance_score": 0.72,
        "product_mentions": ["Dubai", "Vereinigte Arabische Emirate"],
        "discovered_week": "2026-04-07",
        "suggested_title": "Dubai im Sommer 2026: Warum Juli/August die unterschätzte Reisezeit ist (und 40% günstiger)",
        "content_brief": "Temperatur-Tabelle, Indoor-Attraktionen (Dubai Mall, IMG Worlds, Ski Dubai). Preisvergleich Sommer vs. Winter. Interviews mit 2 deutschsprachigen Reiseleitern.",
        "search_intent": "informational",
        "article_id": None,
        "article_status": None,
        "article_headline": None,
    },
    {
        "source_item_id": "op-007",
        "topic": "Rom-Städtereise — lohnt sich Vatikan-Ticket im Voraus?",
        "category": "pain_tens",
        "gap_score": 7.9,
        "source": "Gutefrage.net",
        "url": "https://www.gutefrage.net/frage/rom-vatikan-ticket",
        "content_snippet": "Touristen überfordert mit Ticket-Optionen. Kann man vor Ort kaufen oder sollte online? Welche Kombi-Tickets lohnen sich?",
        "keywords": ["Rom Vatikan Ticket", "Sixtinische Kapelle online buchen", "Vatikanische Museen Tickets", "Rom Sparcard"],
        "llm_opportunity": "Evergreen-Ratgeber mit exklusiver Partnerschaft Vatikanische Museen.",
        "intent": "commercial",
        "emotion": "confusion",
        "answer_count": 3,
        "key_insight": "Hohe Conversion-Rate, ganzjähriges Traffic-Potenzial.",
        "device_relevance_score": 0.74,
        "product_mentions": ["Rom", "Vatikan", "Italien"],
        "discovered_week": "2026-04-07",
        "suggested_title": "Rom 2026: Vatikan-Tickets, Kolosseum & Co. — so sparen Sie 68% bei der Städtereise",
        "content_brief": "Ticket-Navigator mit echten Preis-Daten. Zeit-Matrix Jan–Dez. Insider: 'Skip-the-line'-Tricks. Affiliate-Links GetYourGuide + direkte Buchung Vatikan.",
        "search_intent": "commercial",
        "article_id": "art-007",
        "article_status": "completed",
        "article_headline": "Rom 2026: Vatikan-Tickets, Kolosseum & Co. — so sparen Sie 68% bei der Städtereise",
    },
    {
        "source_item_id": "op-008",
        "topic": "Mittelmeerkreuzfahrt mit MSC — welche Route lohnt sich für Erstkreuzer?",
        "category": "menstrual",
        "gap_score": 7.8,
        "source": "HolidayCheck Forum",
        "url": "https://www.holidaycheck.de/forum/msc-mittelmeer",
        "content_snippet": "Erstkreuzer überfordert von Routenauswahl. Westliches vs. östliches Mittelmeer. Welche Häfen, welche Woche?",
        "keywords": ["MSC Mittelmeer", "Kreuzfahrt Erstkreuzer", "westliches Mittelmeer Route", "MSC Pauschalreise"],
        "llm_opportunity": "Bild-exklusiv: Bordreportage + Live-Route-Tracker.",
        "intent": "commercial",
        "emotion": "excitement",
        "answer_count": 2,
        "key_insight": "MSC-Dominanz in DE-Markt — gute Partnership-Chance.",
        "device_relevance_score": 0.69,
        "product_mentions": ["MSC", "Mittelmeer", "Kreuzfahrt"],
        "discovered_week": "2026-04-07",
        "suggested_title": "Mittelmeer-Kreuzfahrt 2026: Diese 3 Routen sind perfekt für Erstkreuzer (mit Preis-Check)",
        "content_brief": "Route-Karte + Kabinen-Tipps. MSC vs. Costa vs. AIDA Vergleichsmatrix. Was ist wo inklusive. Zeitpläne 2026.",
        "search_intent": "commercial",
        "article_id": "art-008",
        "article_status": "completed",
        "article_headline": "Mittelmeer-Kreuzfahrt 2026: Diese 3 Routen sind perfekt für Erstkreuzer (mit Preis-Check)",
    },
    {
        "source_item_id": "op-009",
        "topic": "Thailand-Rundreise — Phuket, Krabi oder Koh Samui als Start?",
        "category": "infrarot",
        "gap_score": 7.7,
        "source": "Reddit (r/reisen)",
        "url": "https://www.reddit.com/r/reisen/comments/thailand-rundreise",
        "content_snippet": "Rundreise-Planer vs. All-Inclusive-Paket. Welche Insel als Basis? Welche Ausflüge sind die echten Highlights?",
        "keywords": ["Thailand Rundreise 2026", "Phuket Krabi Koh Samui", "Thailand Pauschalreise 2 Wochen", "Thailand Regenzeit"],
        "llm_opportunity": "Visuelle Story mit Drohnen-Aufnahmen und exklusivem Thailand-Reiseführer-Interview.",
        "intent": "informational",
        "emotion": "excitement",
        "answer_count": 4,
        "key_insight": "Hohe Engagement-Rate auf visuellem Content.",
        "device_relevance_score": 0.73,
        "product_mentions": ["Thailand", "Phuket", "Krabi", "Koh Samui"],
        "discovered_week": "2026-04-07",
        "suggested_title": "Thailand-Rundreise 2026: Die perfekte 14-Tage-Route — Phuket oder Krabi zuerst?",
        "content_brief": "Tages-by-Tages-Plan. Regenzeit-Daten. Hotel-Empfehlungen pro Etappe. Kosten-Gesamtrechnung.",
        "search_intent": "informational",
        "article_id": None,
        "article_status": None,
        "article_headline": None,
    },
    {
        "source_item_id": "op-010",
        "topic": "Lastminute Mallorca ab Frankfurt — wo buche ich am Montag oder Mittwoch?",
        "category": "blood_pressure",
        "gap_score": 7.6,
        "source": "Reddit (r/urlaub)",
        "url": "https://www.reddit.com/r/urlaub/comments/lastminute-mallorca",
        "content_snippet": "Nutzer teilen Erfahrungen zur besten Buchungsstrategie für Last Minute. Weg.de vs. Check24 vs. direkt im Reisebüro.",
        "keywords": ["Last Minute Mallorca Frankfurt", "Mallorca morgen buchen", "Reisebüro vs online", "Mallorca 3 Tage buchen"],
        "llm_opportunity": "Daten-Story: realer Lastminute-Preisverlauf 14 Tage.",
        "intent": "transactional",
        "emotion": "impatience",
        "answer_count": 1,
        "key_insight": "Hohe Klickrate bei zeitkritischen Queries.",
        "device_relevance_score": 0.82,
        "product_mentions": ["Mallorca", "Frankfurt", "Check24"],
        "discovered_week": "2026-03-31",
        "suggested_title": "Last Minute Mallorca: Mittwoch oder Freitag buchen? — Wir haben 14 Tage die Preise getrackt",
        "content_brief": "Echte Preistracking-Daten. Monats-Heatmap günstigste Buchungs-Wochentage. Interviews mit 3 Reisebüro-Inhabern.",
        "search_intent": "transactional",
        "article_id": "art-010",
        "article_status": "completed",
        "article_headline": "Last Minute Mallorca: Mittwoch oder Freitag buchen? — Wir haben 14 Tage die Preise getrackt",
    },
    {
        "source_item_id": "op-011",
        "topic": "Griechische Inseln — Kreta, Rhodos oder Kos für Familie?",
        "category": "blood_pressure",
        "gap_score": 7.4,
        "source": "HolidayCheck Forum",
        "url": "https://www.holidaycheck.de/forum/griechenland-familie",
        "content_snippet": "Familien mit Kindern 4–12 vergleichen griechische Inseln. Flug-Dauer, Strand-Qualität, Hotel-Kinderfreundlichkeit.",
        "keywords": ["Griechenland Familie", "Kreta vs Rhodos Kos", "beste Insel Familienurlaub", "Griechenland Familienhotel"],
        "llm_opportunity": "Family-Travel-Expertise mit Kids-Club-Rating.",
        "intent": "commercial",
        "emotion": "curiosity",
        "answer_count": 2,
        "key_insight": "Evergreen — Sommer-Peak in 8 Wochen.",
        "device_relevance_score": 0.78,
        "product_mentions": ["Kreta", "Rhodos", "Kos", "Griechenland"],
        "discovered_week": "2026-03-31",
        "suggested_title": "Griechenland für Familien 2026: Kreta, Rhodos oder Kos? — Der ultimative Insel-Vergleich",
        "content_brief": "Faktenbasiertes Ranking: Strand, Hotel, Ausflüge, Preis. Beispiel-Familien-Angebote je Insel.",
        "search_intent": "commercial",
        "article_id": "art-011",
        "article_status": "completed",
        "article_headline": "Griechenland für Familien 2026: Kreta, Rhodos oder Kos? — Der ultimative Insel-Vergleich",
    },
    {
        "source_item_id": "op-012",
        "topic": "All-Inclusive vs. Halbpension — was rechnet sich wirklich für 7 Tage Türkei?",
        "category": "blood_pressure",
        "gap_score": 7.3,
        "source": "Gutefrage.net",
        "url": "https://www.gutefrage.net/frage/ai-vs-halbpension",
        "content_snippet": "Leser wollen echten Spar-Vergleich. Wie viel kostet ein Essen/Getränk vor Ort? Wie oft wird man außerhalb essen?",
        "keywords": ["All Inclusive vs Halbpension", "Türkei AI Vergleich", "Urlaub Verpflegung Kosten", "Pauschalreise Verpflegung"],
        "llm_opportunity": "Bild-Calculator mit interaktivem Tool.",
        "intent": "commercial",
        "emotion": "calculation",
        "answer_count": 3,
        "key_insight": "Interaktives Tool = hohes Engagement + Backlinks.",
        "device_relevance_score": 0.71,
        "product_mentions": ["Türkei", "All Inclusive"],
        "discovered_week": "2026-03-31",
        "suggested_title": "All-Inclusive lohnt sich nur für DIESE Reisetypen — der ehrliche Vergleich für 7 Tage Türkei",
        "content_brief": "Interaktiver AI-Calculator. 4 Reisetypen (Familie, Paar, Solo, Senioren). Beispielrechnungen. Hotel-Empfehlungen pro Typ.",
        "search_intent": "commercial",
        "article_id": None,
        "article_status": None,
        "article_headline": None,
    },
    {
        "source_item_id": "op-013",
        "topic": "Paris kurz & günstig — 3 Tage unter 500€ inklusive Flug und Hotel?",
        "category": "pain_tens",
        "gap_score": 7.1,
        "source": "Reddit (r/reisen)",
        "url": "https://www.reddit.com/r/reisen/comments/paris-guenstig",
        "content_snippet": "Studenten und Junge Paare suchen echte Budget-Paris-Pakete. Hostels vs. Low-Cost-Hotels, Essens-Kosten.",
        "keywords": ["Paris günstig 3 Tage", "Paris Kurzurlaub Budget", "Paris unter 500 Euro", "Paris Städtereise günstig"],
        "llm_opportunity": "Budget-Travel-Story mit exakten Kostenaufstellungen.",
        "intent": "transactional",
        "emotion": "hope",
        "answer_count": 5,
        "key_insight": "Hohe Share-Rate bei junger Zielgruppe.",
        "device_relevance_score": 0.68,
        "product_mentions": ["Paris", "Frankreich"],
        "discovered_week": "2026-03-24",
        "suggested_title": "Paris unter 500 € — So klappt die 3-Tage-Städtereise wirklich günstig (mit Beispielrechnung)",
        "content_brief": "Echte 500€-Reise: Flug, Hostel, 9 Mahlzeiten, 5 Attraktionen. Tag-für-Tag. Buchungs-Reihenfolge.",
        "search_intent": "transactional",
        "article_id": "art-013",
        "article_status": "completed",
        "article_headline": "Paris unter 500 € — So klappt die 3-Tage-Städtereise wirklich günstig (mit Beispielrechnung)",
    },
    {
        "source_item_id": "op-014",
        "topic": "Karibik Punta Cana — beste Reisezeit und welche Hotels für Honeymoon?",
        "category": "infrarot",
        "gap_score": 7.0,
        "source": "HolidayCheck Forum",
        "url": "https://www.holidaycheck.de/forum/punta-cana-honeymoon",
        "content_snippet": "Hochzeitsreise-Paare fragen nach besten Adults-Only-Resorts. Hurrikan-Saison vs. Trockenzeit.",
        "keywords": ["Punta Cana Honeymoon", "Karibik adults only", "Dominikanische Republik Hurrikan", "Karibik Pauschalreise"],
        "llm_opportunity": "Luxury-Pauschalreise-Story mit hoher AOV.",
        "intent": "commercial",
        "emotion": "romance",
        "answer_count": 3,
        "key_insight": "Honeymoon = hohe Buchungs-Conversion.",
        "device_relevance_score": 0.66,
        "product_mentions": ["Punta Cana", "Dominikanische Republik", "Karibik"],
        "discovered_week": "2026-03-24",
        "suggested_title": "Flitterwochen in der Karibik 2026: Die 8 besten Adults-Only-Hotels in Punta Cana",
        "content_brief": "Ranking mit realen Preisen. Hurrikan-Wahrscheinlichkeit nach Monat. Hochzeitspakete. Bild-exklusiver Paar-Test.",
        "search_intent": "commercial",
        "article_id": None,
        "article_status": None,
        "article_headline": None,
    },
    {
        "source_item_id": "op-015",
        "topic": "Ferienflieger Condor, TUIfly, Eurowings — bei welchem Anbieter buche ich?",
        "category": "blood_pressure",
        "gap_score": 6.9,
        "source": "Reddit (r/urlaub)",
        "url": "https://www.reddit.com/r/urlaub/comments/ferienflieger-vergleich",
        "content_snippet": "Angebote identisch im Preis, aber unterschiedliche Verspätungs-Stats. Welcher Anbieter ist zuverlässig?",
        "keywords": ["Condor vs TUIfly", "Ferienflieger Verspätung", "Eurowings Discover Erfahrung", "Pauschalreise Flug Qualität"],
        "llm_opportunity": "Daten-Story mit Pünktlichkeits-Stats von Eurocontrol.",
        "intent": "commercial",
        "emotion": "frustration",
        "answer_count": 2,
        "key_insight": "Daten-Story mit exklusiver Eurocontrol-Quelle.",
        "device_relevance_score": 0.64,
        "product_mentions": ["Condor", "TUIfly", "Eurowings"],
        "discovered_week": "2026-03-24",
        "suggested_title": "Pauschalreise-Flug im Test: Condor, TUIfly, Eurowings — wer bringt Sie pünktlich ins Hotel?",
        "content_brief": "Verspätungs-Stats 2024/2025. Passagier-Bewertungen. Sitzplatz-Info. Empfehlung pro Zielgebiet.",
        "search_intent": "commercial",
        "article_id": None,
        "article_status": None,
        "article_headline": None,
    },
]

# Additional "completed articles" (generated full content for display)
GENERATED_ARTICLES = [
    {
        "article_id": "art-001",
        "headline": "Mallorca-Pauschalreise 2026: Was die Preise wirklich tun — und wann Sie jetzt buchen sollten",
        "category": "blood_pressure",
        "status": "published",
        "published_at": _days_ago(2),
        "word_count": 2450,
        "reading_time": 12,
        "seo_score": 94,
        "aeo_score": 91,
        "destination": "Mallorca",
        "author": "Jana Körte",
        "traffic_30d": 18430,
        "ai_citations": 12,
        "ranked_keywords": 147,
    },
    {
        "article_id": "art-002",
        "headline": "Türkei All-Inclusive für Familien 2026: Die 12 besten Hotels bis 5.000€ im Test",
        "category": "blood_pressure",
        "status": "generating",
        "generation_stage": "fact_check",
        "generation_progress": 72,
        "destination": "Türkei",
    },
    {
        "article_id": "art-004",
        "headline": "Kanaren im Januar 2027: Das ist die wärmste Insel — plus die 5 besten Hotels je Insel",
        "category": "blood_pressure",
        "status": "published",
        "published_at": _days_ago(5),
        "word_count": 2180,
        "reading_time": 10,
        "seo_score": 92,
        "aeo_score": 89,
        "destination": "Kanaren",
        "author": "Tom Berger",
        "traffic_30d": 14820,
        "ai_citations": 9,
        "ranked_keywords": 98,
    },
    {
        "article_id": "art-005",
        "headline": "Malediven unter 1.500 € — ja, das geht wirklich: Die 7 besten Schnäppchen-Deals 2026",
        "category": "infrarot",
        "status": "published",
        "published_at": _days_ago(8),
        "word_count": 2890,
        "reading_time": 14,
        "seo_score": 96,
        "aeo_score": 94,
        "destination": "Malediven",
        "author": "Sabrina Wolf",
        "traffic_30d": 22140,
        "ai_citations": 18,
        "ranked_keywords": 203,
    },
    {
        "article_id": "art-007",
        "headline": "Rom 2026: Vatikan-Tickets, Kolosseum & Co. — so sparen Sie 68% bei der Städtereise",
        "category": "pain_tens",
        "status": "published",
        "published_at": _days_ago(12),
        "word_count": 2350,
        "reading_time": 11,
        "seo_score": 90,
        "aeo_score": 87,
        "destination": "Rom",
        "author": "Marco Schilling",
        "traffic_30d": 16290,
        "ai_citations": 14,
        "ranked_keywords": 124,
    },
    {
        "article_id": "art-008",
        "headline": "Mittelmeer-Kreuzfahrt 2026: Diese 3 Routen sind perfekt für Erstkreuzer (mit Preis-Check)",
        "category": "menstrual",
        "status": "published",
        "published_at": _days_ago(15),
        "word_count": 2120,
        "reading_time": 10,
        "seo_score": 88,
        "aeo_score": 85,
        "destination": "Mittelmeer",
        "author": "Claudia Neuner",
        "traffic_30d": 9840,
        "ai_citations": 7,
        "ranked_keywords": 67,
    },
    {
        "article_id": "art-010",
        "headline": "Last Minute Mallorca: Mittwoch oder Freitag buchen? — Wir haben 14 Tage die Preise getrackt",
        "category": "blood_pressure",
        "status": "published",
        "published_at": _days_ago(18),
        "word_count": 1980,
        "reading_time": 9,
        "seo_score": 93,
        "aeo_score": 90,
        "destination": "Mallorca",
        "author": "Jana Körte",
        "traffic_30d": 26380,
        "ai_citations": 21,
        "ranked_keywords": 182,
    },
    {
        "article_id": "art-011",
        "headline": "Griechenland für Familien 2026: Kreta, Rhodos oder Kos? — Der ultimative Insel-Vergleich",
        "category": "blood_pressure",
        "status": "published",
        "published_at": _days_ago(21),
        "word_count": 2540,
        "reading_time": 12,
        "seo_score": 91,
        "aeo_score": 88,
        "destination": "Griechenland",
        "author": "Tom Berger",
        "traffic_30d": 11720,
        "ai_citations": 10,
        "ranked_keywords": 89,
    },
    {
        "article_id": "art-013",
        "headline": "Paris unter 500 € — So klappt die 3-Tage-Städtereise wirklich günstig (mit Beispielrechnung)",
        "category": "pain_tens",
        "status": "published",
        "published_at": _days_ago(24),
        "word_count": 1840,
        "reading_time": 9,
        "seo_score": 87,
        "aeo_score": 86,
        "destination": "Paris",
        "author": "Marco Schilling",
        "traffic_30d": 13620,
        "ai_citations": 8,
        "ranked_keywords": 72,
    },
]


# ─── Build executive summary / dashboard ─────────────────────────────────────

def build_dashboard_data():
    total_mentions = sum(s["count"] for s in SOURCES.values()) + 200
    positive = 1240
    neutral = 510
    negative = 280
    total = positive + neutral + negative

    volume_by_source = {k: v["count"] for k, v in SOURCES.items()}

    volume_by_category = {
        "blood_pressure": 1124,  # Strand & All-Inclusive
        "pain_tens": 498,        # Städtereisen
        "infrarot": 276,         # Fernreisen
        "menstrual": 142,        # Kreuzfahrten
        "other": 98,
    }

    # Per-source × category matrix
    volume_by_source_by_category = {}
    for src, meta in SOURCES.items():
        cnt = meta["count"]
        volume_by_source_by_category[src] = {
            "blood_pressure": int(cnt * 0.58),
            "pain_tens": int(cnt * 0.22),
            "infrarot": int(cnt * 0.13),
            "menstrual": int(cnt * 0.05),
            "other": int(cnt * 0.02),
        }

    trending_topics = [
        {"topic": "Mallorca Frühbucher 2026", "count": 214},
        {"topic": "Türkei All Inclusive", "count": 186},
        {"topic": "Ägypten Sicherheit", "count": 142},
        {"topic": "Kanaren Winterurlaub", "count": 128},
        {"topic": "Malediven günstig", "count": 114},
        {"topic": "Rom Städtereise", "count": 96},
        {"topic": "Griechenland Familie", "count": 92},
        {"topic": "Dubai Sommer", "count": 78},
        {"topic": "Thailand Rundreise", "count": 74},
        {"topic": "Punta Cana Honeymoon", "count": 61},
    ]

    # Competitor data
    product_intelligence = {
        "bild_pauschalreisen": {
            d[0]: {
                "count": int(d[2] * 12),
                "sentiment": {
                    "positive": int(d[2] * 7),
                    "neutral": int(d[2] * 4),
                    "negative": int(d[2] * 1),
                },
                "mention_types": {"direct": int(d[2] * 8), "comparison": int(d[2] * 3), "recommendation": int(d[2] * 1)},
                "top_issues": [],
                "top_praise": ["Preis-Leistungs-Verhältnis", "Beratung", "Transparenz"],
                "aspects": [],
            }
            for d in DESTINATIONS[:12]
        },
        "bild_pauschalreisen_total": 1240,
        "beurer_total": 1240,
        "own_total": 1240,
        "competitors": {
            c[0]: {
                "count": c[1],
                "sentiment": {"positive": c[2], "neutral": c[3], "negative": c[4]},
            }
            for c in COMPETITORS
        },
        "competitors_total": sum(c[1] for c in COMPETITORS),
        "competitor_mention_count": sum(c[1] for c in COMPETITORS),
    }

    # Purchase intent feed (customers asking specific buying questions)
    purchase_intent_feed = [
        {
            "title": "Suche Mallorca-Angebot für Familie mit 2 Kindern (6, 9 Jahre), 1. Juli, bis 4.800€",
            "source": "Reddit (r/reisen)",
            "source_url": "https://reddit.com/r/reisen/mallorca-familie-juli",
            "category": "blood_pressure",
            "intent_signal": "ready_to_book",
            "reach_estimate": 14800,
            "posted_at": _days_ago(1),
            "matched_products": ["Mallorca", "All Inclusive"],
        },
        {
            "title": "Wer hat Erfahrung mit Side/Antalya All-Inclusive-Hotels unter 2.500€ Juli?",
            "source": "HolidayCheck Forum",
            "source_url": "https://www.holidaycheck.de/forum/side-ai-2500",
            "category": "blood_pressure",
            "intent_signal": "ready_to_book",
            "reach_estimate": 9200,
            "posted_at": _days_ago(2),
            "matched_products": ["Türkei", "Side", "Antalya"],
        },
        {
            "title": "Malediven Pauschalreise mit Wasserbungalow — welcher Veranstalter bietet bestes Preis-Leistungs-Verhältnis?",
            "source": "Gutefrage.net",
            "source_url": "https://www.gutefrage.net/malediven-wasserbungalow",
            "category": "infrarot",
            "intent_signal": "comparing",
            "reach_estimate": 6400,
            "posted_at": _days_ago(3),
            "matched_products": ["Malediven", "Wasserbungalow"],
        },
        {
            "title": "Kreuzfahrt MSC vs. AIDA — wer hat aktuelle Erfahrung für Familien mit Teenagern?",
            "source": "Reddit (r/urlaub)",
            "source_url": "https://reddit.com/r/urlaub/msc-vs-aida",
            "category": "menstrual",
            "intent_signal": "comparing",
            "reach_estimate": 8700,
            "posted_at": _days_ago(4),
            "matched_products": ["MSC", "AIDA", "Kreuzfahrt"],
        },
        {
            "title": "Ägypten November 2026 — aktuelle Sicherheitslage, wer war zuletzt da?",
            "source": "HolidayCheck Forum",
            "source_url": "https://www.holidaycheck.de/forum/aegypten-nov-2026",
            "category": "blood_pressure",
            "intent_signal": "researching",
            "reach_estimate": 11400,
            "posted_at": _days_ago(5),
            "matched_products": ["Ägypten", "Hurghada"],
        },
        {
            "title": "Frühbucher für Sommer 2026 — jetzt noch sinnvoll oder schon zu spät? Weg.de zeigt Rabatte bis 30%",
            "source": "Reddit (r/reisen)",
            "source_url": "https://reddit.com/r/reisen/fruehbucher-sommer-2026",
            "category": "blood_pressure",
            "intent_signal": "ready_to_book",
            "reach_estimate": 17200,
            "posted_at": _days_ago(6),
            "matched_products": ["Frühbucher", "Sommer 2026"],
        },
        {
            "title": "Rom im Juni 2026: Hotel nähe Vatikan bis 180€/Nacht — Tipps?",
            "source": "Reddit (r/reisen)",
            "source_url": "https://reddit.com/r/reisen/rom-vatikan-hotel",
            "category": "pain_tens",
            "intent_signal": "ready_to_book",
            "reach_estimate": 7800,
            "posted_at": _days_ago(7),
            "matched_products": ["Rom", "Vatikan"],
        },
        {
            "title": "Thailand 14 Tage inkl. Flug ab Frankfurt — aktuelle Preise, wo am günstigsten?",
            "source": "Gutefrage.net",
            "source_url": "https://www.gutefrage.net/thailand-14-tage",
            "category": "infrarot",
            "intent_signal": "comparing",
            "reach_estimate": 6200,
            "posted_at": _days_ago(8),
            "matched_products": ["Thailand", "Frankfurt"],
        },
        {
            "title": "Karibik All Inclusive Honeymoon Oktober — welches Hotel würdet ihr buchen?",
            "source": "HolidayCheck Forum",
            "source_url": "https://www.holidaycheck.de/forum/karibik-honeymoon",
            "category": "infrarot",
            "intent_signal": "researching",
            "reach_estimate": 4200,
            "posted_at": _days_ago(9),
            "matched_products": ["Karibik", "Honeymoon"],
        },
        {
            "title": "Griechenland Rhodos für Familie — welches Hotel Kinderclub bis 3.200€?",
            "source": "Reddit (r/reisen)",
            "source_url": "https://reddit.com/r/reisen/rhodos-familie",
            "category": "blood_pressure",
            "intent_signal": "ready_to_book",
            "reach_estimate": 5400,
            "posted_at": _days_ago(10),
            "matched_products": ["Rhodos", "Griechenland"],
        },
        {
            "title": "Kanaren Teneriffa im November — welcher Süden, welcher Norden?",
            "source": "Gutefrage.net",
            "source_url": "https://www.gutefrage.net/teneriffa-november",
            "category": "blood_pressure",
            "intent_signal": "researching",
            "reach_estimate": 3800,
            "posted_at": _days_ago(11),
            "matched_products": ["Teneriffa", "Kanaren"],
        },
        {
            "title": "Dubai Familien-Pauschalreise August — trotz Hitze sinnvoll?",
            "source": "HolidayCheck Forum",
            "source_url": "https://www.holidaycheck.de/forum/dubai-august",
            "category": "infrarot",
            "intent_signal": "researching",
            "reach_estimate": 4900,
            "posted_at": _days_ago(12),
            "matched_products": ["Dubai", "Sommer"],
        },
    ]

    # News
    news_articles = [
        {
            "title": "TUI meldet Rekord-Buchungszahlen für Sommer 2026 — Mallorca & Türkei führen",
            "url": "https://www.tui.com/de/news/sommer-2026-rekord",
            "source": "tui.com",
            "posted_at": _days_ago(2),
            "summary": "Deutschlands größter Reisekonzern verkündet zweistelliges Buchungsplus. Mallorca unverändert Nr. 1, Türkei holt deutlich auf.",
            "author": None,
            "score": 92,
            "tier": "must_read",
            "topic_tags": ["industry", "booking_trends"],
            "is_competitor": True,
            "news_category": "competitor",
        },
        {
            "title": "Check24 Urlaubs-Report: Preise im Sommer 2026 um 14% gestiegen",
            "url": "https://www.check24.de/presse/urlaubsreport-2026",
            "source": "check24.de",
            "posted_at": _days_ago(3),
            "summary": "Durchschnittspreis einer Pauschalreise liegt bei 938€ pro Person. Türkei günstigstes Ziel, Malediven teuerstes.",
            "author": None,
            "score": 88,
            "tier": "must_read",
            "topic_tags": ["pricing", "industry"],
            "is_competitor": True,
            "news_category": "competitor",
        },
        {
            "title": "Auswärtiges Amt aktualisiert Reisehinweise für Ägypten — Hurghada weiterhin unbedenklich",
            "url": "https://www.auswaertiges-amt.de/sicherheitshinweise/aegypten",
            "source": "auswaertiges-amt.de",
            "posted_at": _days_ago(4),
            "summary": "Kein geänderter Gesamt-Status. Touristische Hotspots am Roten Meer bleiben ohne Warnung.",
            "author": None,
            "score": 84,
            "tier": "interesting",
            "topic_tags": ["safety", "regulatory"],
            "is_competitor": False,
            "news_category": "industry",
        },
        {
            "title": "ChatGPT nennt BILD Pauschalreisen in 18% der 'beste Mallorca-Angebote' Anfragen — Peec AI Studie",
            "url": "https://app.peec.ai/reports/bild-pauschalreisen-mallorca",
            "source": "peec.ai",
            "posted_at": _days_ago(5),
            "summary": "AI-Visibility-Benchmark zeigt: BILD Pauschalreisen bereits in Top-3 der zitierten Quellen für Mallorca. TUI führt mit 31%, Check24 mit 24%.",
            "author": None,
            "score": 95,
            "tier": "must_read",
            "topic_tags": ["ai_visibility", "competitive"],
            "is_competitor": False,
            "news_category": "company",
        },
        {
            "title": "HolidayCheck-Award 2026: Diese 50 Hotels haben gewonnen — 12 auf Mallorca",
            "url": "https://www.holidaycheck.de/awards/2026",
            "source": "holidaycheck.de",
            "posted_at": _days_ago(6),
            "summary": "Ausgezeichnet auf Basis von 1,8 Mio. Gäste-Bewertungen. Mallorca mit 12 Hotels klar vorn, Türkei mit 8, Griechenland mit 6.",
            "author": None,
            "score": 80,
            "tier": "interesting",
            "topic_tags": ["awards", "quality"],
            "is_competitor": True,
            "news_category": "competitor",
        },
        {
            "title": "Condor streicht 47 Sommerflüge — Pauschalurlauber erhalten Ersatz oder Geld zurück",
            "url": "https://www.condor.com/de/presse/flugausfall-sommer-2026",
            "source": "condor.com",
            "posted_at": _days_ago(7),
            "summary": "Betroffen sind Flüge nach Mallorca, Antalya und Hurghada. Condor bietet Umbuchung auf Eurowings oder volle Erstattung.",
            "author": None,
            "score": 82,
            "tier": "interesting",
            "topic_tags": ["flights", "consumer_rights"],
            "is_competitor": False,
            "news_category": "industry",
        },
        {
            "title": "Perplexity AI zitiert 'Bild Pauschalreisen'-Artikel bei Frage 'bester Pauschalreise-Anbieter Familie'",
            "url": "https://app.peec.ai/mentions/bild-perplexity-familie",
            "source": "peec.ai",
            "posted_at": _days_ago(8),
            "summary": "AI-Chatbot nennt BILD Pauschalreisen neben TUI und Check24 als vertrauenswürdige Quelle für Familien-Recherche.",
            "author": None,
            "score": 91,
            "tier": "must_read",
            "topic_tags": ["ai_visibility", "milestone"],
            "is_competitor": False,
            "news_category": "company",
        },
    ]

    # Executive dashboard
    executive_dashboard = {
        "kpi_cards": [
            {"label": "AI-Visibility-Score", "value": "68%", "delta": "+14pp", "delta_direction": "up"},
            {"label": "Share of Voice (ChatGPT/Perplexity)", "value": "18%", "delta": "+6pp", "delta_direction": "up"},
            {"label": "Published Articles", "value": "47", "delta": "+12", "delta_direction": "up"},
            {"label": "Traffic 30 Tage", "value": "342k", "delta": "+28%", "delta_direction": "up"},
            {"label": "Ranked Keywords", "value": "1,284", "delta": "+187", "delta_direction": "up"},
            {"label": "AI Citations", "value": "124", "delta": "+42", "delta_direction": "up"},
        ],
        "highlights": [
            {"icon": "success", "text": "Mallorca-Artikel in ChatGPT Top-3 zitiert (vor TUI) — 18k Traffic in 2 Wochen."},
            {"icon": "trend", "text": "Neue Zielgruppe: 'Budget-Familien Türkei' wächst +64% WoW auf Reddit/HolidayCheck."},
            {"icon": "alert", "text": "Ägypten-Safety-Artikel dringend: 142 Forum-Fragen in 7 Tagen, Bild-Story-Chance."},
            {"icon": "insights", "text": "Kreuzfahrt-Kategorie unterrepräsentiert — MSC-Partnership-Opportunität identifiziert."},
        ],
    }

    key_actions = [
        {
            "priority": "high",
            "title": "Ägypten-Sicherheits-Update jetzt publizieren",
            "rationale": "142 offene Forum-Fragen in 7 Tagen. Peak-Buchungsphase November-Januar. Bild-Reporter-Netzwerk vor Ort verfügbar.",
            "expected_impact": "~25k Traffic, +8pp AI-Visibility Ägypten-Keywords",
            "linked_opportunity_id": "op-003",
            "effort": "2-3 Tage",
        },
        {
            "priority": "high",
            "title": "Mallorca-Frühbucher Datenserie starten (wöchentlich)",
            "rationale": "Wochenlanger Preis-Tracker-Artikel wird 18k/Woche liefern + ChatGPT-Citations absichern.",
            "expected_impact": "~80k Traffic/Monat evergreen, AI-Citation-Rate +50%",
            "linked_opportunity_id": "op-001",
            "effort": "laufend, 1 Tag/Woche",
        },
        {
            "priority": "medium",
            "title": "Malediven Under-1500-Deal-Roundup monatlich",
            "rationale": "Erster Artikel läuft stark (22k Traffic). Evergreen + updatebar.",
            "expected_impact": "~30k Traffic/Monat",
            "linked_opportunity_id": "op-005",
            "effort": "1 Tag/Monat",
        },
        {
            "priority": "medium",
            "title": "Türkei-Familien-Hotel-Tool veröffentlichen",
            "rationale": "Artikel in Generierung (72%). Interaktiver Filter = Backlinks von TUI/Check24-Communities.",
            "expected_impact": "~20k Traffic/Monat + Authority-Backlinks",
            "linked_opportunity_id": "op-002",
            "effort": "in Produktion",
        },
        {
            "priority": "medium",
            "title": "MSC-Partnership aktivieren",
            "rationale": "Kreuzfahrt-Kategorie unterbesetzt. Bild kann Bordreportage + Livestream bieten.",
            "expected_impact": "Neue Content-Säule, 3-5 Artikel/Monat, +40k Traffic",
            "linked_opportunity_id": "op-008",
            "effort": "Partnership-Setup 4-6 Wochen",
        },
        {
            "priority": "low",
            "title": "Dubai-Sommer-Contrarian-Angle testen",
            "rationale": "Niche-Story mit hohem Viral-Potenzial. Paradoxer Claim + 40% Preisvorteil = share-bar.",
            "expected_impact": "~15k Traffic (social-driven)",
            "linked_opportunity_id": "op-006",
            "effort": "1-2 Tage",
        },
    ]

    competitive_intelligence = {
        "competitor_breakdown": [
            {"brand": c[0], "mentions": c[1], "sov_pct": round(c[1] / sum(x[1] for x in COMPETITORS) * 100, 1),
             "sentiment_positive_pct": round(c[2] / c[1] * 100, 1)}
            for c in COMPETITORS
        ],
        "ai_visibility_share": {
            "TUI":           31.2,
            "Check24":       24.1,
            "BILD Pauschalreisen": 18.4,
            "HolidayCheck":  11.6,
            "weg.de":         6.8,
            "ab-in-den-urlaub": 4.2,
            "Expedia":        2.4,
            "FTI":            1.3,
        },
        "aspect_comparison": [
            {"aspect": "Preis-Transparenz", "bild": 87, "tui": 62, "check24": 78, "holidaycheck": 54},
            {"aspect": "Familien-Empfehlungen", "bild": 84, "tui": 76, "check24": 62, "holidaycheck": 71},
            {"aspect": "Datenbasierte Inhalte", "bild": 94, "tui": 48, "check24": 66, "holidaycheck": 58},
            {"aspect": "Echtzeitpreise/Alerts", "bild": 78, "tui": 58, "check24": 88, "holidaycheck": 42},
            {"aspect": "Reise-Sicherheit", "bild": 91, "tui": 68, "check24": 52, "holidaycheck": 64},
            {"aspect": "Hotel-Deep-Dives", "bild": 82, "tui": 84, "check24": 48, "holidaycheck": 89},
        ],
        "gap_opportunities": [
            {"gap": "Keine Anbieter-unabhängigen Hotel-Vergleiche", "impact_score": 9.1},
            {"gap": "AI-Chatbot-Citations für 'Familien-Urlaub' unterbelegt", "impact_score": 8.7},
            {"gap": "Bild-Reporter-Netzwerk-Nutzung (Interviews vor Ort)", "impact_score": 8.4},
            {"gap": "Daten-Stories (Preis-Tracker, DWD-Klima, Eurocontrol-Pünktlichkeit)", "impact_score": 9.2},
            {"gap": "Nischen-Reiseanlässe (Honeymoon, Solo-Senioren, Digital Nomad)", "impact_score": 7.6},
        ],
    }

    journey_intelligence = {
        "by_stage": {
            "awareness": {"count": 412, "top_topics": ["Reiseziel entdecken", "Urlaubs-Inspiration", "Insta-Reise-Trends"]},
            "consideration": {"count": 638, "top_topics": ["Hotel-Vergleich", "Preis-Recherche", "Angebote durchsuchen"]},
            "decision":    {"count": 384, "top_topics": ["All Inclusive vs. Halbpension", "Familien-Hotel wählen", "Reisezeit entscheiden"]},
            "purchase":    {"count": 272, "top_topics": ["Frühbucher-Rabatt", "Last Minute Deal", "Zahlungsarten"]},
            "experience":  {"count": 168, "top_topics": ["Ausflug-Tipps", "Insider-Info vor Ort", "Bewertung teilen"]},
        },
        "conversion_touchpoints": [
            {"stage": "awareness→consideration", "conversion_pct": 61, "accelerators": ["Inspiration-Content", "Hero-Destinationen"]},
            {"stage": "consideration→decision", "conversion_pct": 48, "accelerators": ["Datenvergleiche", "Hotel-Deep-Dives"]},
            {"stage": "decision→purchase", "conversion_pct": 44, "accelerators": ["Preis-Alerts", "Buchungslinks"]},
        ],
    }

    deep_insights = {
        "by_category": {
            "blood_pressure": {
                "top_pains": [
                    {"pain": "Preis-Intransparenz", "count": 186, "trend": "+22%"},
                    {"pain": "Hotel-Qualität unsicher", "count": 142, "trend": "+14%"},
                    {"pain": "Reisezeit-Wahl", "count": 98, "trend": "+6%"},
                ],
                "user_segments": [
                    {"segment": "Familie mit 1-3 Kindern", "share_pct": 42, "avg_budget": 4200},
                    {"segment": "Paar 35-55", "share_pct": 28, "avg_budget": 2800},
                    {"segment": "Senioren 60+", "share_pct": 18, "avg_budget": 3100},
                    {"segment": "Solo Budget-Traveler", "share_pct": 12, "avg_budget": 1400},
                ],
            },
            "pain_tens": {
                "top_pains": [
                    {"pain": "Ticket-Dschungel", "count": 94, "trend": "+18%"},
                    {"pain": "Hotel-Lage vs. Preis", "count": 78, "trend": "+9%"},
                ],
                "user_segments": [
                    {"segment": "Young Urban 25-35", "share_pct": 46, "avg_budget": 650},
                    {"segment": "Kulturreisende 45-65", "share_pct": 38, "avg_budget": 1200},
                    {"segment": "Familie Städtetrip", "share_pct": 16, "avg_budget": 1800},
                ],
            },
        },
    }

    alerts_data = {
        "critical": [
            {
                "title": "Ägypten Hurghada — Sicherheits-Diskussion +312% WoW",
                "source": "HolidayCheck Forum + Reddit",
                "posted_at": _days_ago(1),
                "url": "https://www.holidaycheck.de/forum/aegypten-nov-2026",
                "category": "blood_pressure",
                "description": "142 neue Fragen in 7 Tagen. Peak vor Herbstferien. Content-Action: Live-Update-Artikel JETZT.",
            },
            {
                "title": "Condor Flug-Streichungen Sommer 2026 — Nutzer-Frust steigt",
                "source": "Reddit (r/urlaub) + Twitter/X",
                "posted_at": _days_ago(2),
                "url": "https://reddit.com/r/urlaub/condor-streichung",
                "category": "blood_pressure",
                "description": "47 Flüge betroffen. Consumer-Rights-Artikel (Entschädigung, Umbuchung) = hohe Relevanz + SEO.",
            },
        ],
        "warning": [
            {
                "title": "Türkei Saisonstart — Buchungen lahmen vs. Vorjahr",
                "source": "Check24-Presse + Bild-Intern",
                "posted_at": _days_ago(3),
                "url": "https://www.check24.de/presse/urlaubsreport-2026",
                "category": "blood_pressure",
                "description": "Story-Opportunität: Warum zögern Deutsche bei Türkei? Interviews + Daten.",
            },
            {
                "title": "Mallorca-Preise — Social-Media-Kritik trendet (Hashtag #MallorcaTeuer)",
                "source": "Instagram + TikTok",
                "posted_at": _days_ago(4),
                "url": "https://www.instagram.com/explore/tags/mallorcateuer/",
                "category": "blood_pressure",
                "description": "14k Posts in 7 Tagen. Bild-Reaktion: Datenbasierter Gegenentwurf oder Ratgeber '5 günstige Alternativen'.",
            },
        ],
        "opportunity": [
            {
                "title": "Malediven-Deals — TUI wirft 20%-Rabatt-Codes in Umlauf",
                "source": "Reddit (r/urlaub)",
                "posted_at": _days_ago(2),
                "url": "https://reddit.com/r/urlaub/tui-maledives-rabatt",
                "category": "infrarot",
                "description": "User teilen Codes. Bild-Artikel über Code-Jagd + Spar-Tipps = Viral-Potenzial.",
            },
        ],
    }

    # Media visibility (AI citation tracker)
    media_visibility = {
        "overall_score": 68,
        "prev_score": 54,
        "trend_7d": [48, 52, 54, 58, 61, 65, 68],
        "by_engine": {
            "ChatGPT":    {"score": 72, "trend": "+16pp", "top_query": "beste Pauschalreise Familie Mallorca"},
            "Perplexity": {"score": 64, "trend": "+14pp", "top_query": "Malediven günstig unter 1500"},
            "Google AI Overview": {"score": 68, "trend": "+12pp", "top_query": "Mallorca Frühbucher 2026"},
            "Gemini":     {"score": 61, "trend": "+10pp", "top_query": "Türkei All Inclusive Familie"},
            "Claude":     {"score": 74, "trend": "+22pp", "top_query": "Rom Städtereise Ticket Tipps"},
        },
        "top_cited_articles": [
            {"article_id": "art-005", "citations_30d": 18, "engines": ["ChatGPT", "Perplexity", "Claude"]},
            {"article_id": "art-010", "citations_30d": 21, "engines": ["ChatGPT", "Perplexity", "Google AI Overview"]},
            {"article_id": "art-001", "citations_30d": 12, "engines": ["ChatGPT", "Perplexity"]},
            {"article_id": "art-007", "citations_30d": 14, "engines": ["ChatGPT", "Claude", "Gemini"]},
        ],
    }

    # SEO data
    seo_data = {
        "ranked_keywords_total": 1284,
        "top_3_positions": 187,
        "top_10_positions": 512,
        "top_keywords": [
            {"kw": "mallorca pauschalreise 2026", "pos": 2, "vol": 22000, "cpc": 1.84, "article_id": "art-001"},
            {"kw": "türkei all inclusive familie", "pos": 4, "vol": 18000, "cpc": 2.12, "article_id": "art-002"},
            {"kw": "malediven günstig", "pos": 1, "vol": 14800, "cpc": 2.48, "article_id": "art-005"},
            {"kw": "kanaren winter wärmste insel", "pos": 1, "vol": 9600, "cpc": 1.12, "article_id": "art-004"},
            {"kw": "last minute mallorca", "pos": 3, "vol": 24000, "cpc": 2.01, "article_id": "art-010"},
            {"kw": "rom städtereise tipps", "pos": 2, "vol": 12400, "cpc": 0.98, "article_id": "art-007"},
            {"kw": "griechenland kreta familie", "pos": 5, "vol": 8800, "cpc": 1.34, "article_id": "art-011"},
            {"kw": "paris günstig 3 tage", "pos": 4, "vol": 7600, "cpc": 0.84, "article_id": "art-013"},
            {"kw": "mittelmeer kreuzfahrt msc 2026", "pos": 3, "vol": 5400, "cpc": 1.62, "article_id": "art-008"},
            {"kw": "hurghada sicher november 2026", "pos": 6, "vol": 6200, "cpc": 0.72, "article_id": None},
        ],
    }

    user_voice = {
        "top_quotes": [
            {"quote": "Bild Pauschalreisen-Artikel haben mir die Wahrheit über Hotel-Unterschiede gezeigt — das ist der einzige Anbieter, der ehrlich ist.", "source": "Reddit", "destination": "Mallorca"},
            {"quote": "Endlich Preise, denen ich vertrauen kann. Keine Fake-Rabatte wie bei anderen.", "source": "HolidayCheck Forum", "destination": "Türkei"},
            {"quote": "Der Mallorca-Tracker-Artikel hat mir 600€ gespart — beste Reise-Recherche-Quelle 2026.", "source": "Gutefrage", "destination": "Mallorca"},
        ],
    }

    # Build source highlights
    source_highlights = [
        {"source": s, "label": v["label"], "count": v["count"], "top_topic": list(trending_topics)[0]["topic"]}
        for s, v in SOURCES.items()
    ]

    # Top posts (QA-like)
    top_posts = [
        {
            "title": "Mallorca-Preise explodieren — was macht ihr? Frühbucher oder Last Minute?",
            "source": "Reddit (r/urlaub)",
            "source_url": "https://reddit.com/r/urlaub/mallorca-preise",
            "category": "blood_pressure",
            "engagement": 342,
            "answers": 67,
            "posted_at": _days_ago(1),
            "snippet": "Wir haben 10 Mallorca-Reisen gemacht und die Preise sind nie so hoch gewesen. Frühbucher vs Last Minute — was macht man jetzt?",
        },
        {
            "title": "Ägypten Hurghada sicher November 2026? Hatte wer in den letzten Wochen eine Reise?",
            "source": "HolidayCheck Forum",
            "source_url": "https://www.holidaycheck.de/forum/aegypten-hurghada",
            "category": "blood_pressure",
            "engagement": 284,
            "answers": 42,
            "posted_at": _days_ago(2),
            "snippet": "Buche Ende November. Bin unsicher durch die News. Aktuelle Erfahrungsberichte?",
        },
        {
            "title": "Malediven unter 1500€ — geht das wirklich? Alle Angebote wirken wie Fake.",
            "source": "Reddit (r/reisen)",
            "source_url": "https://reddit.com/r/reisen/malediven-1500",
            "category": "infrarot",
            "engagement": 218,
            "answers": 31,
            "posted_at": _days_ago(3),
            "snippet": "Alle Angebote 'ab 1499€' haben versteckte Kosten. Gibt es echte Deals?",
        },
        {
            "title": "Rom Städtereise April — Vatikan-Tickets, Kolosseum, wo spart man wirklich?",
            "source": "Gutefrage.net",
            "source_url": "https://www.gutefrage.net/rom-april",
            "category": "pain_tens",
            "engagement": 168,
            "answers": 24,
            "posted_at": _days_ago(5),
            "snippet": "Wir buchen Rom für April 2026. Kombi-Ticket Roma Pass oder einzeln?",
        },
    ]

    alerts_flat = []
    for sev, items in alerts_data.items():
        for it in items:
            alerts_flat.append({**it, "severity": sev})

    brand_sentiment = {
        "positive": 1240,
        "neutral": 510,
        "negative": 280,
        "total": total,
        "note": "Stimmung gegenüber BILD Pauschalreisen in Foren, Social Media und AI-Zitaten",
    }

    topic_sentiment = {
        "positive": 2140,
        "neutral": 1420,
        "negative": 680,
        "total": 4240,
        "note": "Stimmung zu Pauschalreise-Themen generell (destinationsübergreifend)",
    }

    # Enrich content opportunities with common fields expected by template
    content_opps = []
    for opp in CONTENT_OPPORTUNITIES:
        content_opps.append({**opp})

    period_start = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    period_end = datetime.utcnow().strftime("%Y-%m-%d")

    data = {
        "period": {"start": period_start, "end": period_end, "week_number": 17},
        "generated_at": _now_iso(),
        "_source": "live",
        "executive_summary": {
            "headline": "BILD Pauschalreisen · Content Engine (Demo-Daten)",
            "total_items": total_mentions,
            "total_mentions": total_mentions,
            "competitor_mention_count": sum(c[1] for c in COMPETITORS),
            "overall_sentiment_pct": {
                "positive": round(positive / total * 100),
                "neutral": round(neutral / total * 100),
                "negative": round(negative / total * 100),
            },
            "delta_wow": "+24%",
            "key_insight": "AI-Visibility steigt auf 68% (von 54%). Hero-Destinationen: Mallorca, Malediven, Rom — mit dominanten Bild-Citations bei ChatGPT.",
        },
        "alerts": alerts_data,
        "volume_by_source": volume_by_source,
        "volume_by_source_category": volume_by_source,
        "volume_by_source_by_category": volume_by_source_by_category,
        "volume_by_category": volume_by_category,
        "sentiment_by_category": {
            "blood_pressure": {"positive": 682, "neutral": 340, "negative": 102},
            "pain_tens":      {"positive": 294, "neutral": 168, "negative": 36},
            "infrarot":       {"positive": 162, "neutral":  89, "negative": 25},
            "menstrual":      {"positive":  92, "neutral":  38, "negative": 12},
            "other":          {"positive":  41, "neutral":  38, "negative": 19},
        },
        "trending_topics": trending_topics,
        "product_intelligence": product_intelligence,
        "product_mentions": product_intelligence,
        "user_voice": user_voice,
        "content_opportunities": content_opps,
        "top_posts": top_posts,
        "source_highlights": source_highlights,
        "appendices": {},
        "executive_dashboard": executive_dashboard,
        "key_actions": key_actions,
        "sentiment_deepdive": {
            "by_category": {
                "blood_pressure": {"intensity": 0.74, "polarity": 0.62},
                "pain_tens":      {"intensity": 0.58, "polarity": 0.68},
                "infrarot":       {"intensity": 0.81, "polarity": 0.72},
                "menstrual":      {"intensity": 0.66, "polarity": 0.70},
            },
        },
        "competitive_intelligence": competitive_intelligence,
        "journey_intelligence": journey_intelligence,
        "deep_insights": deep_insights,
        "category_deep_insights": deep_insights["by_category"],
        "category_journeys": {},
        "wow_metrics": {"volume_delta_pct": 24, "sentiment_delta_pp": 3, "content_delta_pct": 8},
        "brand_sentiment": brand_sentiment,
        "topic_sentiment": topic_sentiment,
        "other_breakdown": {"Sonstige Reiseziele": 42, "Nischenanlässe": 28, "Geschäftsreise-Hybrid": 16, "Sonstige": 12},
        "purchase_intent_feed": purchase_intent_feed,
        "news": {
            "articles": news_articles,
            "by_topic": {
                "ai_visibility": 2,
                "competitive": 2,
                "pricing": 1,
                "safety": 1,
                "industry": 1,
                "flights": 1,
                "awards": 1,
            },
            "by_source": {a["source"]: 1 for a in news_articles},
            "total": len(news_articles),
        },
        "media_visibility": media_visibility,
        "media_visibility_peekaboo": {
            "snapshotDate": _now_iso(),
            "overview": {
                "score": 68,
                "totalCitations": 124,
                "rank": 3,
                "deltaScore": "+14pp",
                "deltaCitations": "+42",
            },
            "competitors": [
                {"name": "TUI",             "domain": "tui.com",           "score": 72, "citations": 168, "rank": 1, "trend": "+6pp"},
                {"name": "Check24",         "domain": "check24.de",        "score": 69, "citations": 142, "rank": 2, "trend": "+3pp"},
                {"name": "BILD Pauschalreisen", "domain": "bild.de/reise", "score": 68, "citations": 124, "rank": 3, "trend": "+14pp", "isOwn": True},
                {"name": "HolidayCheck",    "domain": "holidaycheck.de",   "score": 62, "citations": 98,  "rank": 4, "trend": "+2pp"},
                {"name": "weg.de",          "domain": "weg.de",            "score": 54, "citations": 64,  "rank": 5, "trend": "-1pp"},
                {"name": "Expedia",         "domain": "expedia.de",        "score": 48, "citations": 52,  "rank": 6, "trend": "+1pp"},
                {"name": "Booking.com",     "domain": "booking.com",       "score": 46, "citations": 48,  "rank": 7, "trend": "0pp"},
                {"name": "ab-in-den-urlaub","domain": "ab-in-den-urlaub.de","score": 42,"citations": 41,  "rank": 8, "trend": "-2pp"},
                {"name": "FTI",             "domain": "fti.de",            "score": 36, "citations": 28,  "rank": 9, "trend": "-4pp"},
                {"name": "DERTOUR",         "domain": "dertour.de",        "score": 31, "citations": 22,  "rank": 10,"trend": "-1pp"},
            ],
            "prompts": [
                {
                    "text": "Was ist die beste Pauschalreise nach Mallorca 2026 für Familien?",
                    "aiModels": ["ChatGPT", "Perplexity", "Gemini"],
                    "mentions": 2,
                    "mentionedCompetitors": ["TUI", "Check24"],
                    "capturedAt": _days_ago(1),
                    "category": "blood_pressure",
                    "snippet": "BILD Pauschalreisen bietet eine detaillierte Analyse der Mallorca-Preisentwicklung für 2026 mit Frühbucher-Vergleichen…",
                },
                {
                    "text": "Malediven günstig unter 1500 Euro — gibt es sowas wirklich?",
                    "aiModels": ["ChatGPT", "Claude", "Perplexity"],
                    "mentions": 2,
                    "mentionedCompetitors": ["TUI", "DERTOUR"],
                    "capturedAt": _days_ago(2),
                    "category": "infrarot",
                    "snippet": "Laut Bild Pauschalreisen gibt es tatsächlich Malediven-Pakete unter 1.500€ — insbesondere Guesthouse-Angebote auf den lokalen Inseln…",
                },
                {
                    "text": "Hurghada Ägypten — ist es November 2026 sicher?",
                    "aiModels": ["Perplexity", "Gemini", "AI Overview"],
                    "mentions": 2,
                    "mentionedCompetitors": ["HolidayCheck"],
                    "capturedAt": _days_ago(3),
                    "category": "blood_pressure",
                    "snippet": "Auswärtiges Amt und BILD-Reise-Redaktion bestätigen: Hurghada-Hotspots ohne spezifische Sicherheitswarnung…",
                },
                {
                    "text": "Rom Städtereise — Vatikan Tickets online oder vor Ort?",
                    "aiModels": ["ChatGPT", "Claude"],
                    "mentions": 2,
                    "mentionedCompetitors": [],
                    "capturedAt": _days_ago(4),
                    "category": "pain_tens",
                    "snippet": "BILD-Reise-Ratgeber empfiehlt: Online-Tickets 14 Tage im Voraus — spart bis zu 68%…",
                },
                {
                    "text": "Türkei All-Inclusive Familie bester Wert 2026",
                    "aiModels": ["ChatGPT", "Perplexity"],
                    "mentions": 0,
                    "mentionedCompetitors": ["TUI", "Check24", "FTI"],
                    "capturedAt": _days_ago(5),
                    "category": "blood_pressure",
                    "snippet": "TUI dominiert die Nennungen, gefolgt von Check24. BILD noch nicht in Top-5. Opportunity.",
                },
                {
                    "text": "Mittelmeer-Kreuzfahrt für Erstkreuzer",
                    "aiModels": ["ChatGPT", "Gemini"],
                    "mentions": 2,
                    "mentionedCompetitors": ["HolidayCheck"],
                    "capturedAt": _days_ago(6),
                    "category": "menstrual",
                    "snippet": "BILD Pauschalreisen-Vergleich MSC vs. Costa vs. AIDA wird direkt zitiert…",
                },
                {
                    "text": "Paris Kurztrip unter 500 Euro möglich?",
                    "aiModels": ["Claude", "Perplexity"],
                    "mentions": 2,
                    "mentionedCompetitors": [],
                    "capturedAt": _days_ago(7),
                    "category": "pain_tens",
                    "snippet": "BILD-Reise-Artikel mit konkreter 3-Tage-Beispielrechnung direkt als Quelle genannt…",
                },
                {
                    "text": "Kanaren Winterurlaub welche Insel am wärmsten",
                    "aiModels": ["ChatGPT", "AI Overview"],
                    "mentions": 2,
                    "mentionedCompetitors": ["HolidayCheck"],
                    "capturedAt": _days_ago(8),
                    "category": "blood_pressure",
                    "snippet": "Datenbasis (DWD-Klimadaten) von BILD Pauschalreisen wird als Quelle referenziert…",
                },
            ],
            "sources": [
                {"domain": "tui.com",             "citations": 168, "pct": 23.4, "trend": "+6pp"},
                {"domain": "check24.de",          "citations": 142, "pct": 19.8, "trend": "+3pp"},
                {"domain": "bild.de",             "citations": 124, "pct": 17.3, "trend": "+14pp", "isOwn": True},
                {"domain": "holidaycheck.de",     "citations": 98,  "pct": 13.6, "trend": "+2pp"},
                {"domain": "auswaertiges-amt.de", "citations": 82,  "pct": 11.4, "trend": "+1pp"},
                {"domain": "weg.de",              "citations": 64,  "pct":  8.9, "trend": "-1pp"},
                {"domain": "expedia.de",          "citations": 52,  "pct":  7.2, "trend": "+1pp"},
                {"domain": "tripadvisor.de",      "citations": 48,  "pct":  6.7, "trend": "0pp"},
                {"domain": "reddit.com/r/reisen", "citations": 41,  "pct":  5.7, "trend": "+2pp"},
                {"domain": "booking.com",         "citations": 36,  "pct":  5.0, "trend": "-1pp"},
            ],
            "suggestions": [
                "Türkei-Familien-Content stärken: ChatGPT nennt TUI/Check24/FTI, BILD fehlt. Impact: +22% Citation-Share.",
                "Auto-Update-Trigger für Ägypten-Safety: Wöchentliche Refresh-Quelle bei AI-Engines. Impact: +18 Citations/Monat.",
                "Kreuzfahrt-Coverage ausbauen: Nur 7 Citations — MSC-Partnership aktivieren. Impact: neue Content-Säule, +40k Traffic.",
                "Long-Tail SEO für Rundreise-Queries: 'Thailand Rundreise 14 Tage' wird noch nicht zitiert. Impact: Peec-Rank +8pp.",
                "E-E-A-T Signal Injector aktivieren: Autoren-Credentials + Erstbesuch-Statements automatisch. Impact: AI-Overview-Citation-Rate +22%.",
                "Evergreen Updater starten: Preis-Tables monatlich refresh. Impact: Traffic-Decay -42%.",
            ],
            "history": [
                {"date": (datetime.utcnow() - timedelta(days=35-i*7)).strftime("%Y-%m-%d"),
                 "own_score": 48 + i*4,
                 "competitors": [
                    {"name": "TUI", "score": 68 + i},
                    {"name": "Check24", "score": 66 + i},
                    {"name": "HolidayCheck", "score": 60 + i//2},
                 ]}
                for i in range(6)
            ],
        },
        "seo_data": seo_data,
        "generated_articles": GENERATED_ARTICLES,
        "available_weeks": [
            {"week_start": "2026-04-14", "week_end": "2026-04-20"},
            {"week_start": "2026-04-07", "week_end": "2026-04-13"},
            {"week_start": "2026-03-31", "week_end": "2026-04-06"},
            {"week_start": "2026-03-24", "week_end": "2026-03-30"},
        ],
        # Kundendienst mapped as "Reiseberatung/Support-Anfragen"
        "kundendienstInsights": {
            "heatmap": {
                "products": [
                    {"model": d[0], "category": d[1], "total": int(d[2] * 6),
                     "reasons": {
                         "Umbuchung": int(d[2] * 2),
                         "Preis-Frage": int(d[2] * 1.5),
                         "Hotel-Detail": int(d[2] * 1.2),
                         "Stornierung": int(d[2] * 0.8),
                         "Flug-Problem": int(d[2] * 0.5),
                     }}
                    for d in DESTINATIONS[:10]
                ],
                "allReasons": ["Umbuchung", "Preis-Frage", "Hotel-Detail", "Stornierung", "Flug-Problem"],
                "totalCases": 1842,
            },
            "trends": {
                "weeks": [
                    {"week": f"2026-W{w:02d}", "total": 180 + (w * 8),
                     "byReason": {"Umbuchung": 60+w*3, "Preis-Frage": 50+w*2, "Hotel-Detail": 40+w*2, "Stornierung": 20+w, "Flug-Problem": 10+w}}
                    for w in range(10, 18)
                ],
                "allReasons": ["Umbuchung", "Preis-Frage", "Hotel-Detail", "Stornierung", "Flug-Problem"],
            },
            "alerts": [
                {"product": "Ägypten (Hurghada)", "reason": "Stornierung", "currentCount": 42, "avgCount": 14, "changePercent": 200, "severity": "critical"},
                {"product": "Mallorca", "reason": "Preis-Frage", "currentCount": 87, "avgCount": 54, "changePercent": 61, "severity": "warning"},
                {"product": "Türkei (Antalya)", "reason": "Hotel-Detail", "currentCount": 62, "avgCount": 41, "changePercent": 51, "severity": "warning"},
            ],
            "summary": {
                "totalCases": 1842,
                "topProduct": {"model": "Mallorca", "count": 284},
                "topReason": {"reason": "Umbuchung", "count": 524},
                "alertCount": 3,
            },
        },
    }

    return data


def build_gsc_data():
    """Mock Google Search Console data — shape matches dashboard/app/api/gsc/data."""
    period_start = (datetime.utcnow() - timedelta(days=28)).strftime("%Y-%m-%d")
    period_end = datetime.utcnow().strftime("%Y-%m-%d")
    return {
        "connected": True,
        "email": "content-team@bild.de",
        "site_url": "https://www.bild.de/reise/",
        "property": "https://www.bild.de/reise/",
        "last_sync": _now_iso(),
        "range_days": 28,
        "period": {"start": period_start, "end": period_end, "days": 28},
        "totals": {
            "clicks": 342184,
            "impressions": 4826197,
            "ctr": 7.09,
            "position": 4.2,
            "clicks_delta": 28.4,
            "impressions_delta": 22.6,
            "ctr_delta": 0.8,
            "position_delta": -1.2,
        },
        "date_chart": [
            {"date": (datetime.utcnow() - timedelta(days=27-i)).strftime("%Y-%m-%d"),
             "clicks": 9800 + random.randint(-2200, 3600),
             "impressions": 148000 + random.randint(-20000, 32000),
             "ctr": round(6.2 + random.uniform(-1.0, 1.4), 2),
             "position": round(4.8 + random.uniform(-0.9, 0.7), 1)}
            for i in range(28)
        ],
        "top_queries": [
            {"query": "mallorca pauschalreise 2026",      "clicks": 18430, "impressions": 186000, "ctr": 9.9,  "position": 2.1, "article_id": "art-001"},
            {"query": "last minute mallorca",              "clicks": 17840, "impressions": 214000, "ctr": 8.3,  "position": 3.0, "article_id": "art-010"},
            {"query": "malediven günstig",                 "clicks": 14210, "impressions": 102000, "ctr": 13.9, "position": 1.4, "article_id": "art-005"},
            {"query": "türkei all inclusive familie",      "clicks": 12680, "impressions": 148000, "ctr": 8.6,  "position": 3.8, "article_id": "art-002"},
            {"query": "rom städtereise tipps",             "clicks": 11420, "impressions":  98000, "ctr": 11.7, "position": 2.2, "article_id": "art-007"},
            {"query": "kanaren winter wärmste insel",      "clicks":  9840, "impressions":  68000, "ctr": 14.5, "position": 1.2, "article_id": "art-004"},
            {"query": "griechenland kreta familie",        "clicks":  7220, "impressions":  84000, "ctr":  8.6, "position": 4.4, "article_id": "art-011"},
            {"query": "mittelmeer kreuzfahrt msc 2026",    "clicks":  6440, "impressions":  52000, "ctr": 12.4, "position": 2.8, "article_id": "art-008"},
            {"query": "paris günstig 3 tage",              "clicks":  5820, "impressions":  64000, "ctr":  9.1, "position": 4.2, "article_id": "art-013"},
            {"query": "pauschalreise vergleich 2026",      "clicks":  4860, "impressions":  72000, "ctr":  6.8, "position": 5.6, "article_id": None},
            {"query": "hurghada sicher november 2026",     "clicks":  4280, "impressions":  42000, "ctr": 10.2, "position": 5.8, "article_id": None},
            {"query": "dubai sommer günstig",              "clicks":  3640, "impressions":  48000, "ctr":  7.6, "position": 6.4, "article_id": None},
            {"query": "thailand rundreise 14 tage",        "clicks":  3420, "impressions":  58000, "ctr":  5.9, "position": 7.2, "article_id": None},
            {"query": "bild pauschalreisen",               "clicks":  3280, "impressions":  24000, "ctr": 13.7, "position": 1.1, "article_id": None},
            {"query": "condor tuifly pünktlichkeit",       "clicks":  2860, "impressions":  32000, "ctr":  8.9, "position": 4.8, "article_id": None},
        ],
        "top_pages": [
            {"page": "/reise/mallorca-pauschalreise-2026-preise",   "clicks": 26380, "impressions": 286000, "ctr": 9.2,  "position": 2.4, "article_id": "art-001"},
            {"page": "/reise/last-minute-mallorca-wochentag",       "clicks": 22140, "impressions": 268000, "ctr": 8.3,  "position": 2.9, "article_id": "art-010"},
            {"page": "/reise/malediven-unter-1500-euro",            "clicks": 18430, "impressions": 142000, "ctr": 13.0, "position": 1.6, "article_id": "art-005"},
            {"page": "/reise/rom-staedtereise-vatikan-tickets",     "clicks": 16290, "impressions": 138000, "ctr": 11.8, "position": 2.2, "article_id": "art-007"},
            {"page": "/reise/kanaren-januar-waermste-insel",        "clicks": 14820, "impressions":  98000, "ctr": 15.1, "position": 1.4, "article_id": "art-004"},
            {"page": "/reise/griechenland-kreta-rhodos-kos",        "clicks": 11720, "impressions": 126000, "ctr":  9.3, "position": 4.2, "article_id": "art-011"},
            {"page": "/reise/paris-unter-500-euro",                 "clicks": 13620, "impressions": 148000, "ctr":  9.2, "position": 4.0, "article_id": "art-013"},
            {"page": "/reise/mittelmeer-kreuzfahrt-erstkreuzer",    "clicks":  9840, "impressions":  86000, "ctr": 11.4, "position": 2.8, "article_id": "art-008"},
        ],
        "position_distribution": {
            "1-3":  182,
            "4-10": 330,
            "11-20": 248,
            "21-50": 412,
            "51-100": 112,
        },
        "country_breakdown": {
            "DE": {"clicks": 284920, "impressions": 3820000, "ctr": 7.5},
            "AT": {"clicks":  32140, "impressions":  482000, "ctr": 6.7},
            "CH": {"clicks":  18420, "impressions":  342000, "ctr": 5.4},
            "US": {"clicks":   3840, "impressions":   84000, "ctr": 4.6},
            "GB": {"clicks":   1820, "impressions":   46000, "ctr": 4.0},
            "Rest": {"clicks":    1044, "impressions":   52197, "ctr": 2.0},
        },
        "device_breakdown": {
            "mobile":  {"clicks": 241824, "impressions": 3286000, "ctr": 7.4},
            "desktop": {"clicks":  84620, "impressions": 1284000, "ctr": 6.6},
            "tablet":  {"clicks":  15740, "impressions":  256197, "ctr": 6.1},
        },
    }


def build_pipeline_data():
    """
    Pipeline & Agents tab data — the Head-of-SEO/GEO technical view.
    Models the 5-stage pipeline + pluggable agents + metrics.
    """
    return {
        "overview": {
            "articles_in_flight": 3,
            "articles_generated_30d": 47,
            "avg_time_sec": 284,
            "avg_cost_eur": 1.38,
            "avg_quality_score": 86.4,
            "first_try_success_pct": 73.2,
            "llm_tokens_30d": 28_420_000,
            "llm_cost_30d": 64.80,
            "total_edit_rate": 28.4,
        },
        "stages": [
            {
                "id": "stage_1",
                "name": "Stage 1 — Set Context",
                "description": "Company context, voice, brand rules, competitor landscape. Runs once per batch.",
                "avg_time_sec": 14,
                "token_cost_avg": 8200,
                "model": "gemini-2.5-pro",
                "temperature": 0.2,
                "success_pct": 99.4,
                "agents": [
                    {"id": "ctx_crawler",      "name": "Site Context Crawler",      "status": "active", "model": "gemini-2.5-pro", "role": "Crawls bild.de sitemap + editorial guidelines, extracts voice persona", "tokens_avg": 4200, "p95_ms": 2400, "accuracy": 98.2},
                    {"id": "competitor_map",   "name": "Competitor Landscape Map",  "status": "active", "model": "gpt-4o", "role": "Tracks TUI/Check24/HolidayCheck content + citation gaps via Serper", "tokens_avg": 2400, "p95_ms": 1800, "accuracy": 94.1},
                    {"id": "termbase",         "name": "Termbase Enforcer",         "status": "active", "model": "claude-haiku-4-5", "role": "Maintains approved terminology (Pauschalreise NOT Urlaubsreise, Aktuelle Lage NOT Krisen-Update …)", "tokens_avg": 800, "p95_ms": 420, "accuracy": 99.8},
                    {"id": "voice_persona",    "name": "Voice Persona Agent",       "status": "active", "model": "claude-opus-4-7", "role": "Validates Bild-Tonalität (direkt, klar, boulevardeskes aber seriös)", "tokens_avg": 800, "p95_ms": 640, "accuracy": 96.4},
                ],
                "recommended_agents": [
                    {"id": "legal_check",      "name": "Legal / Compliance Check", "rationale": "Reise-Versicherung + Entschädigungs-Disclaimer EU-Fluggastrechte automatisch einfügen", "estimated_impact": "Senkt Legal-Review-Zeit von 45min → 3min"},
                    {"id": "hreflang",         "name": "Hreflang Manager",         "rationale": "DE/AT/CH Sprach-Varianten automatisch generieren", "estimated_impact": "+18% organischer Traffic aus AT/CH"},
                ],
            },
            {
                "id": "stage_2",
                "name": "Stage 2 — Research + Outline",
                "description": "Deep research via Exa + Serper, fact-check sources, build 5–9-section outline.",
                "avg_time_sec": 72,
                "token_cost_avg": 42000,
                "model": "claude-opus-4-7",
                "temperature": 0.4,
                "success_pct": 94.8,
                "agents": [
                    {"id": "exa_researcher",    "name": "Exa Researcher",            "status": "active", "model": "exa + claude-opus-4-7", "role": "Neural Semantic Search über 4000 Travel-Authority-Quellen", "tokens_avg": 14000, "p95_ms": 14000, "accuracy": 92.1},
                    {"id": "serper_researcher", "name": "Serper SERP Researcher",    "status": "active", "model": "serper + gpt-4o", "role": "Google-Top-20-Ergebnisse für Target-KW auswerten", "tokens_avg": 8000, "p95_ms": 8200, "accuracy": 88.6},
                    {"id": "outline_builder",   "name": "Outline Builder (E-E-A-T)", "status": "active", "model": "claude-opus-4-7", "role": "Baut 5–9-Abschnitte-Struktur mit AEO-Optimization", "tokens_avg": 12000, "p95_ms": 9600, "accuracy": 93.4},
                    {"id": "gap_finder",        "name": "SERP Gap Finder",           "status": "active", "model": "gpt-4o", "role": "Identifiziert Winkel, die Top-10-Wettbewerber NICHT haben", "tokens_avg": 8000, "p95_ms": 6800, "accuracy": 87.2},
                ],
                "recommended_agents": [
                    {"id": "eat_signals",       "name": "E-E-A-T Signal Injector", "rationale": "Autoren-Credentials, Expertise-Jahre, Erstbesuch-Statements automatisch ziehen", "estimated_impact": "Google AI Overview-Citation-Rate +22%"},
                    {"id": "structured_data",   "name": "Schema.org Enhancer",     "rationale": "TravelDestination, FAQ, HowTo, Article-Schemas automatisch", "estimated_impact": "Rich-Result-Share +14pp"},
                ],
            },
            {
                "id": "stage_3",
                "name": "Stage 3 — Writing + Images",
                "description": "Section-weise Writing mit Fact-Check-Loop und Hero-Image-Auswahl.",
                "avg_time_sec": 124,
                "token_cost_avg": 68000,
                "model": "claude-opus-4-7",
                "temperature": 0.7,
                "success_pct": 91.2,
                "agents": [
                    {"id": "section_writer",    "name": "Section Writer (per H2)", "status": "active", "model": "claude-opus-4-7", "role": "Schreibt pro Abschnitt 200–400 Wörter mit Termbase-Treue", "tokens_avg": 42000, "p95_ms": 48000, "accuracy": 89.6},
                    {"id": "table_builder",     "name": "Comparison Table Builder",   "status": "active", "model": "gpt-4o", "role": "Extrahiert Daten aus Research, baut strukturierte Tabellen", "tokens_avg": 6000, "p95_ms": 4200, "accuracy": 94.8},
                    {"id": "hero_image",        "name": "Hero Image Selector",        "status": "active", "model": "gemini-2.5-pro (vision)", "role": "Wählt Unsplash / Getty / Bild-Archiv-Foto nach Text-Kontext", "tokens_avg": 1800, "p95_ms": 3400, "accuracy": 81.2},
                    {"id": "image_accessibility", "name": "Image Alt-Text Accessibility", "status": "active", "model": "claude-haiku-4-5", "role": "Alt-Texte nach WCAG 2.1 AA Standards", "tokens_avg": 600, "p95_ms": 320, "accuracy": 98.1},
                    {"id": "fact_loop",         "name": "Fact Check Loop",            "status": "active", "model": "gpt-4o + serper", "role": "Jeden Claim mit Serper verifizieren, bei Miss Regenerierung", "tokens_avg": 16000, "p95_ms": 18000, "accuracy": 92.4},
                ],
                "recommended_agents": [
                    {"id": "viral_hook",        "name": "Viral Hook Scorer",       "rationale": "Bewertet Intro-Teaser auf Bild-Tauglichkeit (Neugier, Emotionalität, Shareability)", "estimated_impact": "Social-Media-CTR +31%"},
                    {"id": "affiliate_inject",  "name": "Affiliate Link Injector", "rationale": "Setzt TUI/Check24/weg.de Partner-Links bei Hotel-Nennungen", "estimated_impact": "+€0.34 Revenue/Klick"},
                    {"id": "image_archive",     "name": "BILD-Fotoarchiv-Zugriff", "rationale": "Durchsuche Bild-interne Bild-Datenbank statt Unsplash", "estimated_impact": "Brand-Konsistenz, keine Stock-Images"},
                ],
            },
            {
                "id": "stage_4",
                "name": "Stage 4 — URL Verification + Internal Links",
                "description": "Alle externen Links mit HTTP-Check prüfen, interne Links strategisch setzen.",
                "avg_time_sec": 38,
                "token_cost_avg": 14000,
                "model": "gpt-4o",
                "temperature": 0.2,
                "success_pct": 96.8,
                "agents": [
                    {"id": "url_verifier",      "name": "URL HTTP Verifier",       "status": "active", "model": "(HTTP)", "role": "HEAD-Requests auf alle externen URLs, 404 = Remove", "tokens_avg": 0, "p95_ms": 8200, "accuracy": 99.6},
                    {"id": "internal_linker",   "name": "Internal Link Strategist", "status": "active", "model": "gemini-2.5-pro + embeddings", "role": "Wählt 4-6 semantisch passende Bild-Artikel als Kontext-Links", "tokens_avg": 10000, "p95_ms": 6400, "accuracy": 90.2},
                    {"id": "citation_strength", "name": "Citation Strength Score", "status": "active", "model": "gpt-4o", "role": "Bewertet jede Quelle auf Authority (Auswärtiges Amt > Forum-Post)", "tokens_avg": 4000, "p95_ms": 3200, "accuracy": 87.8},
                ],
                "recommended_agents": [
                    {"id": "broken_link_watch", "name": "Broken Link Monitor",        "rationale": "Laufender Scan aller veröffentlichten Artikel auf 404/Redirect-Chains", "estimated_impact": "SEO-Health-Score +8pp"},
                    {"id": "anchor_diversity",  "name": "Anchor-Text-Diversity Agent", "rationale": "Verhindert über-optimierte Anchor-Texte (Google-Penalty-Risiko)", "estimated_impact": "Risk-Mitigation"},
                ],
            },
            {
                "id": "stage_5",
                "name": "Stage 5 — Final Polish + Publish",
                "description": "Meta-Optimization, Schema.org, A/B-Headline-Varianten, Push-CMS.",
                "avg_time_sec": 36,
                "token_cost_avg": 12000,
                "model": "claude-opus-4-7",
                "temperature": 0.3,
                "success_pct": 98.2,
                "agents": [
                    {"id": "meta_optimizer",    "name": "Meta Title/Description Optimizer", "status": "active", "model": "claude-opus-4-7", "role": "SEO + AEO + Social-Preview Meta-Tags", "tokens_avg": 3000, "p95_ms": 1800, "accuracy": 93.6},
                    {"id": "headline_ab",       "name": "Headline A/B Variant Generator",   "status": "active", "model": "gpt-4o + claude-opus-4-7", "role": "3 Headline-Alternativen für CTR-Tests", "tokens_avg": 4000, "p95_ms": 2400, "accuracy": 90.4},
                    {"id": "schema_writer",     "name": "Schema.org JSON-LD Writer",        "status": "active", "model": "gpt-4o", "role": "Article + FAQ + Breadcrumb + Author Schemas", "tokens_avg": 2000, "p95_ms": 1200, "accuracy": 99.2},
                    {"id": "cms_publisher",     "name": "CMS Publisher (WordPress)",        "status": "active", "model": "(API)", "role": "Push ins Bild-CMS mit Draft-Status + Slack-Notification", "tokens_avg": 0, "p95_ms": 3800, "accuracy": 99.8},
                    {"id": "ai_rank_tracker",   "name": "LLM Rank Tracker (Peec.ai)",       "status": "active", "model": "(API)", "role": "Erfasst nach 24h, ob Artikel in ChatGPT/Perplexity/Gemini zitiert wird", "tokens_avg": 0, "p95_ms": 2400, "accuracy": 96.0},
                ],
                "recommended_agents": [
                    {"id": "evergreen_updater", "name": "Evergreen Updater",   "rationale": "Preis-Tables + Datumsangaben monatlich automatisch refreshen (Mallorca-Preise, Klimadaten)", "estimated_impact": "Traffic-Decay -42%"},
                    {"id": "amp_publisher",     "name": "AMP Alternative Publisher", "rationale": "Zusätzliche AMP-Version für Mobile-First-Index", "estimated_impact": "+11% Mobile-CTR"},
                    {"id": "newsletter_push",   "name": "BILD-Reise-Newsletter Integrator", "rationale": "Bei Publish automatisch in Newsletter-Pool", "estimated_impact": "+8k Email-Subscriber-Reach/Artikel"},
                ],
            },
        ],
        "active_runs": [
            {"article_id": "art-002", "topic": "Türkei All-Inclusive Familie 2026", "stage": "stage_3", "stage_name": "Writing + Images", "progress_pct": 72, "started_at": _days_ago(0), "eta_sec": 48, "cost_eur_so_far": 0.92},
            {"article_id": "art-016", "topic": "Ägypten Hurghada Sicherheit November 2026", "stage": "stage_2", "stage_name": "Research + Outline", "progress_pct": 34, "started_at": _days_ago(0), "eta_sec": 186, "cost_eur_so_far": 0.44},
            {"article_id": "art-017", "topic": "Dubai Sommer 2026 Contrarian Guide", "stage": "stage_4", "stage_name": "URL Verification", "progress_pct": 88, "started_at": _days_ago(0), "eta_sec": 22, "cost_eur_so_far": 1.22},
        ],
        "ab_tests": [
            {
                "id": "ab_headline_malediven",
                "article_id": "art-005",
                "test_type": "headline",
                "status": "running",
                "variants": [
                    {"label": "A (Control)", "text": "Malediven unter 1.500 € — ja, das geht wirklich", "ctr": 8.2, "impressions": 42000, "winner": False},
                    {"label": "B", "text": "Malediven-Schnäppchen 2026: 7 Deals unter 1.500 € (verifiziert)", "ctr": 9.4, "impressions": 41800, "winner": True},
                    {"label": "C", "text": "Günstige Malediven: So zahlen Sie 1.248 € statt 3.000 €", "ctr": 7.6, "impressions": 42400, "winner": False},
                ],
                "statistical_significance": 94.2,
                "recommendation": "Ship B",
            },
            {
                "id": "ab_intro_mallorca",
                "article_id": "art-001",
                "test_type": "intro_paragraph",
                "status": "completed",
                "variants": [
                    {"label": "A (Control)", "text": "Eine Mallorca-Pauschalreise kostet 2026 durchschnittlich…", "read_time_avg": 1.8, "scroll_depth": 68, "winner": False},
                    {"label": "B", "text": "Exklusive Bild-Datenrecherche: 312 Angebote über 14 Tage live getrackt.", "read_time_avg": 3.4, "scroll_depth": 84, "winner": True},
                ],
                "statistical_significance": 98.4,
                "recommendation": "B shipped 2026-04-17",
            },
        ],
        "quality_checks": [
            {"check": "Gleiche Fakten in 2 Quellen verifiziert", "pass_rate": 97.2, "trend": "+1.4pp"},
            {"check": "Termbase-Compliance ≥95%", "pass_rate": 98.6, "trend": "+0.2pp"},
            {"check": "Min. 3 externe authoritative Sources", "pass_rate": 94.8, "trend": "+3.2pp"},
            {"check": "Min. 4 interne Cross-Links", "pass_rate": 92.4, "trend": "+8.6pp"},
            {"check": "Hero-Image ≥1600px Auflösung", "pass_rate": 99.8, "trend": "+0.1pp"},
            {"check": "Alt-Texts WCAG 2.1 AA compliant", "pass_rate": 98.1, "trend": "+2.4pp"},
            {"check": "FAQ Schema vorhanden", "pass_rate": 96.4, "trend": "+4.8pp"},
            {"check": "Mobile Core Web Vitals grün", "pass_rate": 91.2, "trend": "+12.4pp"},
        ],
        "insights": [
            {"level": "success", "text": "Viral Hook Scorer reduzierte Bounce-Rate um 18% — Rollout auf alle Stages abgeschlossen."},
            {"level": "warning", "text": "Stage 3 Fact Check Loop läuft 18 Sek. länger als Benchmark. Serper-Latency prüfen."},
            {"level": "opportunity", "text": "E-E-A-T Signal Injector (empfohlen) würde AI-Overview-Citation-Rate um 22% erhöhen — geschätzte Implementierung: 4 Arbeitstage."},
            {"level": "opportunity", "text": "Evergreen Updater würde Traffic-Decay der 9 Top-Artikel um 42% reduzieren. Geschätzter Traffic-Gewinn: 86k/Monat."},
        ],
    }


def main():
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        template = f.read()

    data = build_dashboard_data()
    # Attach articles, GSC and pipeline data
    data["articles"] = all_articles()
    data["gsc"] = build_gsc_data()
    data["pipeline"] = build_pipeline_data()

    data_json = json.dumps(data, ensure_ascii=False)

    # Replace only the assignment target, not the guard-check literal that also references __DASHBOARD_DATA__
    html = template.replace(
        "let DASHBOARD_DATA = __DASHBOARD_DATA__;",
        f"let DASHBOARD_DATA = {data_json};",
        1,
    )
    html = html.replace("__DEFAULT_LANG__", "de")

    # Inject demo-mode fetch interceptor as a SEPARATE <script> BEFORE the main
    # dashboard script runs — otherwise the template's renderGscTab/etc. fetches
    # before the interceptor is installed. The interceptor reads from
    # window.__BILD_DEMO_DATA__ which we set inline here.
    interceptor_script = (
        f"<script>\nwindow.__BILD_DEMO_DATA__ = {data_json};\n</script>\n"
        f"<script>\n{_FETCH_INTERCEPTOR}\n</script>\n"
    )
    # The main dashboard script begins with the "DATA & CONFIGURATION" comment.
    marker = "<script>\n/* ═══════════════════════════════════════════════════════════\n   DATA & CONFIGURATION"
    if marker not in html:
        raise RuntimeError("Could not find main script start — template shape changed")
    html = html.replace(marker, interceptor_script + marker, 1)

    # Pipeline tab renderer + sidebar-nav injection goes AFTER the main script.
    pipeline_script = f"<script>\n{_PIPELINE_TAB_SCRIPT}\n</script>\n"
    needle = "</script>\n</body>"
    if needle in html:
        html = html.replace(needle, "</script>\n" + pipeline_script + "</body>", 1)
    else:
        raise RuntimeError("Could not find </script></body> — template shape changed")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Built {OUTPUT}")
    print(f"  template: {len(template):,} chars")
    print(f"  data: {len(data_json):,} chars")
    print(f"  output: {len(html):,} chars")


_FETCH_INTERCEPTOR = r"""
/* ═══════════════════════════════════════════════════════════════════════════
   OFFLINE DEMO FETCH INTERCEPTOR
   ═══════════════════════════════════════════════════════════════════════════
   Installed BEFORE the main dashboard script so every /api/... fetch returns
   realistic mock data. Reads from window.__BILD_DEMO_DATA__ which the main
   script populates by mirroring D.
*/
(function() {
    if (typeof window === 'undefined') return;
    if (window.location.protocol !== 'file:') return;

    const _origFetch = window.fetch;
    const _resp = (data, status = 200) => Promise.resolve(new Response(
        JSON.stringify(data),
        { status, headers: { 'Content-Type': 'application/json' } }
    ));

    window.fetch = function(input, init) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        const D = window.__BILD_DEMO_DATA__ || {};

        // ── Article detail ────────────────────────────────────────────────
        const articleIdMatch = url.match(/\/api\/blog-article\?id=([^&]+)/);
        if (articleIdMatch) {
            const id = articleIdMatch[1];
            const meta = (D.generated_articles || []).find(a => a.article_id === id) || {};
            const html = (D.articles || {})[id] || '';
            const opp = (D.content_opportunities || []).find(o => o.article_id === id) || {};
            return _resp({
                id,
                article_id: id,
                headline: meta.headline || opp.suggested_title || '(Untitled)',
                keyword: opp.topic || meta.headline || '',
                language: 'de',
                status: meta.status === 'generating' ? 'generating' : 'completed',
                generation_stage: meta.generation_stage || null,
                word_count: meta.word_count || 0,
                article_html: html,
                review_status: 'approved',
                social_context: opp ? {
                    topic: opp.topic,
                    emotion: opp.emotion,
                    intent: opp.intent,
                    gap_score: opp.gap_score,
                    category: opp.category,
                    keywords: opp.keywords,
                    source: opp.source,
                    url: opp.url,
                    content_snippet: opp.content_snippet,
                    key_insight: opp.key_insight,
                } : {},
                feedback_history: [],
                golden_version: null,
                seo_score: meta.seo_score || null,
                aeo_score: meta.aeo_score || null,
                traffic_30d: meta.traffic_30d || null,
                ai_citations: meta.ai_citations || null,
            });
        }

        // ── Article list ──────────────────────────────────────────────────
        if (url.startsWith('/api/blog-article') && !url.includes('id=')) {
            const list = (D.generated_articles || []).map(a => ({
                id: a.article_id,
                source_item_id: a.article_id,
                status: a.status === 'generating' ? 'generating' : 'completed',
                generation_stage: a.generation_stage || null,
                headline: a.headline,
                created_at: a.published_at || new Date().toISOString(),
                review_status: 'approved',
                word_count: a.word_count,
                article_html: (D.articles || {})[a.article_id] || '',
            }));
            return _resp({ articles: list });
        }

        // ── Content planning ──────────────────────────────────────────────
        if (url.startsWith('/api/content-planning')) {
            const opps = D.content_opportunities || [];
            return _resp({
                opportunities: opps,
                total: opps.length,
                weeks_covered: (D.available_weeks || []).length,
            });
        }

        // ── Media visibility (Peekaboo) ───────────────────────────────────
        if (url.startsWith('/api/media-visibility')) {
            const mv = D.media_visibility_peekaboo || {};
            if (url.includes('history=true')) {
                return _resp({ history: mv.history || [] });
            }
            return _resp(mv);
        }

        // ── GSC ───────────────────────────────────────────────────────────
        if (url.startsWith('/api/gsc/data') || url.startsWith('/api/gsc')) {
            const gsc = D.gsc || {};
            if (!gsc.connected) return _resp({ connected: false });
            const isPage = url.includes('type=page');
            const rows = isPage
                ? (gsc.top_pages || []).map(p => ({ page: p.page, clicks: p.clicks, impressions: p.impressions, ctr: p.ctr, position: p.position }))
                : (gsc.top_queries || []).map(q => ({ query: q.query, clicks: q.clicks, impressions: q.impressions, ctr: q.ctr, position: q.position }));
            return _resp({
                connected: true,
                email: gsc.email,
                site_url: gsc.site_url,
                period: gsc.period,
                totals: gsc.totals,
                rows: rows,
                date_chart: isPage ? [] : (gsc.date_chart || []),
            });
        }

        // ── Pipeline ──────────────────────────────────────────────────────
        if (url.startsWith('/api/pipeline')) {
            return _resp(D.pipeline || {});
        }

        // ── Other /api/* calls → empty 200 to avoid noisy errors ──────────
        if (url.startsWith('/api/')) {
            return _resp({ offline: true });
        }

        return _origFetch.apply(this, arguments);
    };

    // ── Pipeline / Agents tab (injected dynamically) ──────────────────────
    // Adds a new sidebar item under "Produktion" and a matching tab panel.
    // Uses the same CSS styling as existing tabs.
    document.addEventListener('DOMContentLoaded', () => {
        const main = document.querySelector('main.content');
        if (main && !document.getElementById('tab-pipeline')) {
            const panel = document.createElement('div');
            panel.className = 'tab-panel';
            panel.id = 'tab-pipeline';
            panel.setAttribute('role', 'tabpanel');
            main.appendChild(panel);
        }
    });
})();
"""


_PIPELINE_TAB_SCRIPT = r"""
/* ═══════════════════════════════════════════════════════════════════════════
   PIPELINE / AGENTS TAB RENDERER
   ═══════════════════════════════════════════════════════════════════════════
   Designed for Head-of-SEO / Head-of-GEO view:
   - 5-stage flow with expandable agents
   - Quality checks + active runs + A/B tests
   - "Add recommended agent" actions
   ═══════════════════════════════════════════════════════════════════════════ */
function renderPipelineTab() {
    const host = document.getElementById('tab-pipeline');
    if (!host) return;
    const p = (DASHBOARD_DATA && DASHBOARD_DATA.pipeline) || {};
    const ov = p.overview || {};
    const stages = p.stages || [];
    const runs = p.active_runs || [];
    const ab = p.ab_tests || [];
    const qc = p.quality_checks || [];
    const insights = p.insights || [];

    const num = (v) => v === null || v === undefined ? '—' : (typeof v === 'number' ? v.toLocaleString('de-DE') : v);
    const pct = (v) => v === null || v === undefined ? '—' : (v.toFixed ? v.toFixed(1) : v) + '%';
    const _esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

    let html = '<div class="section">';

    // ── Header KPIs ──
    html += `<div class="section-header"><div>
        <div class="section-title">Content Pipeline · Agents &amp; Stages</div>
        <div class="section-subtitle">Technischer Überblick über die 5-Stage Generation Pipeline mit konfigurierbaren Agenten</div>
    </div></div>`;

    html += `<div class="kpi-grid" style="margin-bottom:24px;">
        <div class="kpi-card"><div class="kpi-label">Articles im Flight</div><div class="kpi-value">${num(ov.articles_in_flight)}</div><div class="kpi-delta neutral">gerade in Produktion</div></div>
        <div class="kpi-card"><div class="kpi-label">30-Tage Output</div><div class="kpi-value">${num(ov.articles_generated_30d)}</div><div class="kpi-delta up">&#9652; +12 vs Vorperiode</div></div>
        <div class="kpi-card"><div class="kpi-label">Ø Zeit pro Artikel</div><div class="kpi-value">${num(ov.avg_time_sec)}<span style="font-size:16px;opacity:0.6;"> s</span></div><div class="kpi-delta up">&#9652; -42 s</div></div>
        <div class="kpi-card"><div class="kpi-label">Ø Kosten pro Artikel</div><div class="kpi-value">€ ${num(ov.avg_cost_eur)}</div><div class="kpi-delta up">&#9662; -€ 0.24</div></div>
        <div class="kpi-card"><div class="kpi-label">Ø Quality Score</div><div class="kpi-value">${num(ov.avg_quality_score)}<span style="font-size:16px;opacity:0.6;">/100</span></div><div class="kpi-delta up">&#9652; +3.4</div></div>
        <div class="kpi-card accent"><div class="kpi-label">First-Try Success</div><div class="kpi-value">${pct(ov.first_try_success_pct)}</div><div class="kpi-delta neutral" style="color:rgba(255,255,255,0.85)">keine Regeneration</div></div>
    </div>`;

    // ── 5-Stage Flow Visual ──
    html += `<div class="card" style="margin-bottom:24px;"><div class="card-header">
        <h3>5-Stage Content Engine</h3>
        <p style="font-size:12px;color:var(--gray-400);margin-top:2px;">Klicken Sie auf eine Stage, um die aktiven Agenten und empfohlene Erweiterungen zu sehen.</p>
    </div><div class="card-body" style="padding:20px 24px 28px;">
        <div id="pipeline-flow" style="display:grid;grid-template-columns:repeat(${stages.length}, 1fr);gap:8px;margin-bottom:16px;">`;
    stages.forEach((s, i) => {
        html += `<button class="pipeline-stage-btn" data-stage="${_esc(s.id)}" style="background:var(--beurer-magenta-subtle);border:1px solid var(--gray-200);border-left:3px solid var(--beurer-magenta);padding:14px 16px;border-radius:var(--radius-sm);cursor:pointer;text-align:left;transition:all 0.15s;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--beurer-magenta);margin-bottom:4px;">Stage ${i+1}</div>
            <div style="font-size:13px;font-weight:700;color:var(--gray-900);line-height:1.3;margin-bottom:8px;">${_esc(s.name.replace(/^Stage \d+ — /, ''))}</div>
            <div style="display:flex;gap:10px;font-size:10px;color:var(--gray-500);flex-wrap:wrap;">
                <span>⏱ ${s.avg_time_sec}s</span>
                <span>✓ ${pct(s.success_pct)}</span>
                <span>${(s.agents||[]).length} Agenten</span>
            </div>
        </button>`;
    });
    html += `</div>
        <div id="pipeline-stage-detail" style="min-height:120px;"></div>
    </div></div>`;

    // ── Active runs ──
    if (runs.length) {
        html += `<div class="card" style="margin-bottom:24px;"><div class="card-header">
            <h3>Laufende Generierungen</h3>
            <p style="font-size:12px;color:var(--gray-400);margin-top:2px;">${runs.length} Artikel aktuell in der Pipeline</p>
        </div><div class="card-body" style="padding:0;">
            <table style="width:100%;font-size:13px;">
                <thead><tr style="background:#FAFAFA;">
                    <th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:0.04em;color:var(--gray-500);">Topic</th>
                    <th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:0.04em;color:var(--gray-500);">Stage</th>
                    <th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:0.04em;color:var(--gray-500);width:25%;">Fortschritt</th>
                    <th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:0.04em;color:var(--gray-500);">ETA</th>
                    <th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:0.04em;color:var(--gray-500);">Kosten</th>
                </tr></thead><tbody>`;
        runs.forEach(r => {
            html += `<tr style="border-top:1px solid var(--gray-100);">
                <td style="padding:12px 16px;">${_esc(r.topic)}</td>
                <td style="padding:12px 16px;"><span style="background:var(--beurer-magenta-subtle);color:var(--beurer-magenta);padding:3px 10px;border-radius:99px;font-size:11px;font-weight:600;">${_esc(r.stage_name)}</span></td>
                <td style="padding:12px 16px;"><div style="background:var(--gray-100);height:8px;border-radius:4px;overflow:hidden;"><div style="width:${r.progress_pct}%;height:100%;background:var(--beurer-magenta);transition:width 0.3s;"></div></div><div style="font-size:11px;color:var(--gray-500);margin-top:3px;">${r.progress_pct}%</div></td>
                <td style="padding:12px 16px;text-align:right;font-variant-numeric:tabular-nums;">${r.eta_sec}s</td>
                <td style="padding:12px 16px;text-align:right;font-variant-numeric:tabular-nums;">€ ${r.cost_eur_so_far.toFixed(2)}</td>
            </tr>`;
        });
        html += `</tbody></table></div></div>`;
    }

    // ── A/B Tests ──
    if (ab.length) {
        html += `<div class="card" style="margin-bottom:24px;"><div class="card-header">
            <h3>A/B Tests · Data-driven Headlines &amp; Intros</h3>
            <p style="font-size:12px;color:var(--gray-400);margin-top:2px;">Systematische Optimierung jeder Komponente via CTR/Scroll/Read-Time</p>
        </div><div class="card-body" style="padding:20px 24px;">`;
        ab.forEach(test => {
            html += `<div style="border:1px solid var(--gray-200);border-radius:var(--radius-sm);padding:16px 20px;margin-bottom:14px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
                    <div>
                        <div style="font-weight:600;font-size:13px;margin-bottom:4px;">${_esc(test.test_type)} · ${_esc(test.article_id)}</div>
                        <div style="font-size:11px;color:var(--gray-500);">Status: ${_esc(test.status)} · Signifikanz: ${test.statistical_significance}%</div>
                    </div>
                    <div style="background:${test.status === 'completed' ? 'var(--success-light)' : 'var(--warning-light)'};color:${test.status === 'completed' ? 'var(--success)' : 'var(--warning)'};padding:3px 10px;border-radius:99px;font-size:10px;font-weight:700;text-transform:uppercase;">${_esc(test.status)}</div>
                </div>
                <div style="display:grid;grid-template-columns:repeat(${test.variants.length}, 1fr);gap:10px;">`;
            test.variants.forEach(v => {
                const metric_key = Object.keys(v).find(k => !['label','text','winner'].includes(k));
                const metric_val = metric_key ? v[metric_key] : '—';
                html += `<div style="padding:12px 14px;background:${v.winner ? 'var(--success-light)' : 'var(--gray-50)'};border-radius:var(--radius-sm);border:1px solid ${v.winner ? 'var(--success)' : 'var(--gray-200)'};">
                    <div style="font-size:10px;font-weight:700;color:${v.winner ? 'var(--success)' : 'var(--gray-500)'};text-transform:uppercase;margin-bottom:4px;">${_esc(v.label)}${v.winner ? ' · WINNER' : ''}</div>
                    <div style="font-size:12px;line-height:1.4;color:var(--gray-700);margin-bottom:6px;">${_esc(v.text)}</div>
                    <div style="font-size:11px;font-weight:700;color:var(--gray-900);">${_esc(metric_key)}: ${metric_val}</div>
                </div>`;
            });
            html += `</div>
                <div style="margin-top:12px;font-size:12px;color:var(--gray-600);padding-top:10px;border-top:1px solid var(--gray-100);"><strong>Empfehlung:</strong> ${_esc(test.recommendation)}</div>
            </div>`;
        });
        html += `</div></div>`;
    }

    // ── Quality Checks ──
    if (qc.length) {
        html += `<div class="card" style="margin-bottom:24px;"><div class="card-header">
            <h3>Quality Gates · automatisierte Prüfungen</h3>
            <p style="font-size:12px;color:var(--gray-400);margin-top:2px;">Artikel dürfen erst in CMS, wenn alle Checks grün sind</p>
        </div><div class="card-body" style="padding:16px 24px;">
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;">`;
        qc.forEach(c => {
            const color = c.pass_rate >= 97 ? 'var(--success)' : c.pass_rate >= 92 ? 'var(--warning)' : 'var(--error)';
            html += `<div style="padding:12px 14px;border:1px solid var(--gray-200);border-left:3px solid ${color};border-radius:var(--radius-sm);">
                <div style="font-size:12px;color:var(--gray-700);margin-bottom:6px;">${_esc(c.check)}</div>
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-weight:700;font-size:16px;color:${color};">${c.pass_rate}%</div>
                    <div style="font-size:11px;color:var(--success);">${_esc(c.trend)}</div>
                </div>
            </div>`;
        });
        html += `</div></div></div>`;
    }

    // ── Insights ──
    if (insights.length) {
        html += `<div class="card" style="margin-bottom:24px;"><div class="card-header">
            <h3>Pipeline-Insights &amp; Handlungsempfehlungen</h3>
        </div><div class="card-body" style="padding:12px 24px 20px;">`;
        insights.forEach(i => {
            const config = {
                success:    { bg: 'var(--success-light)',   fg: 'var(--success)',   icon: '✓' },
                warning:    { bg: 'var(--warning-light)',   fg: 'var(--warning)',   icon: '⚠' },
                opportunity:{ bg: 'var(--beurer-magenta-subtle)', fg: 'var(--beurer-magenta)', icon: '★' },
            }[i.level] || { bg: 'var(--gray-100)', fg: 'var(--gray-700)', icon: 'ℹ' };
            html += `<div style="background:${config.bg};color:var(--gray-800);padding:12px 16px;border-left:3px solid ${config.fg};border-radius:0 var(--radius-sm) var(--radius-sm) 0;margin:8px 0;font-size:13px;line-height:1.5;">
                <span style="color:${config.fg};font-weight:700;margin-right:6px;">${config.icon}</span> ${_esc(i.text)}
            </div>`;
        });
        html += `</div></div>`;
    }

    html += '</div>';
    host.innerHTML = html;

    // Stage click handlers
    host.querySelectorAll('.pipeline-stage-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.stage;
            host.querySelectorAll('.pipeline-stage-btn').forEach(b => {
                b.style.background = 'var(--beurer-magenta-subtle)';
                b.style.boxShadow = 'none';
            });
            btn.style.background = 'var(--beurer-magenta)';
            btn.style.color = 'white';
            btn.querySelectorAll('div').forEach(d => { d.style.color = 'white'; });
            renderStageDetail(id);
        });
    });
    // Auto-open first stage
    if (stages.length) {
        const first = host.querySelector('.pipeline-stage-btn');
        if (first) first.click();
    }
}

function renderStageDetail(stageId) {
    const host = document.getElementById('pipeline-stage-detail');
    if (!host) return;
    const stages = ((DASHBOARD_DATA.pipeline || {}).stages || []);
    const s = stages.find(x => x.id === stageId);
    if (!s) { host.innerHTML = ''; return; }
    const _esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

    let html = `<div style="background:white;border:1px solid var(--gray-200);border-radius:var(--radius-sm);padding:20px 24px;margin-top:12px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;">
            <div>
                <div style="font-weight:700;font-size:15px;margin-bottom:4px;">${_esc(s.name)}</div>
                <div style="font-size:12px;color:var(--gray-500);line-height:1.5;">${_esc(s.description)}</div>
            </div>
            <div style="font-size:11px;color:var(--gray-500);text-align:right;">
                <div>Base model: <strong style="color:var(--gray-800);">${_esc(s.model)}</strong></div>
                <div>Temperature: <strong style="color:var(--gray-800);">${s.temperature}</strong></div>
                <div>Token budget: <strong style="color:var(--gray-800);">${s.token_cost_avg.toLocaleString('de-DE')} avg</strong></div>
            </div>
        </div>
        <div style="font-size:12px;font-weight:700;color:var(--gray-700);text-transform:uppercase;letter-spacing:0.04em;margin:18px 0 10px;">Aktive Agenten (${(s.agents||[]).length})</div>`;

    (s.agents || []).forEach(a => {
        html += `<div style="border:1px solid var(--gray-200);border-radius:var(--radius-sm);padding:14px 18px;margin-bottom:10px;background:#FAFAFA;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                <div style="flex:1;min-width:0;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                        <span style="font-weight:700;font-size:13px;">${_esc(a.name)}</span>
                        <span style="background:var(--success-light);color:var(--success);padding:1px 8px;border-radius:99px;font-size:10px;font-weight:700;text-transform:uppercase;">${_esc(a.status)}</span>
                    </div>
                    <div style="font-size:12px;color:var(--gray-600);line-height:1.5;margin-bottom:6px;">${_esc(a.role)}</div>
                    <div style="display:flex;gap:16px;font-size:11px;color:var(--gray-500);flex-wrap:wrap;">
                        <span>Model: <strong style="color:var(--gray-800);">${_esc(a.model)}</strong></span>
                        <span>Tokens: <strong style="color:var(--gray-800);">${a.tokens_avg.toLocaleString('de-DE')}</strong></span>
                        <span>P95 Latency: <strong style="color:var(--gray-800);">${a.p95_ms.toLocaleString('de-DE')}ms</strong></span>
                        <span>Accuracy: <strong style="color:var(--gray-800);">${a.accuracy}%</strong></span>
                    </div>
                </div>
                <div style="display:flex;gap:6px;">
                    <button style="background:white;border:1px solid var(--gray-300);padding:5px 10px;border-radius:var(--radius-sm);font-size:11px;cursor:pointer;">Prompt</button>
                    <button style="background:white;border:1px solid var(--gray-300);padding:5px 10px;border-radius:var(--radius-sm);font-size:11px;cursor:pointer;">Logs</button>
                    <button style="background:white;border:1px solid var(--gray-300);padding:5px 10px;border-radius:var(--radius-sm);font-size:11px;cursor:pointer;">A/B</button>
                </div>
            </div>
        </div>`;
    });

    // Recommended / add-on agents
    if ((s.recommended_agents || []).length) {
        html += `<div style="font-size:12px;font-weight:700;color:var(--gray-700);text-transform:uppercase;letter-spacing:0.04em;margin:22px 0 10px;">Empfohlene Agenten (${s.recommended_agents.length}) <span style="font-weight:400;color:var(--gray-500);text-transform:none;letter-spacing:0;">· aktivieren für data-driven improvements</span></div>`;
        s.recommended_agents.forEach(a => {
            html += `<div style="border:1px dashed var(--beurer-magenta);border-radius:var(--radius-sm);padding:14px 18px;margin-bottom:10px;background:var(--beurer-magenta-subtle);">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                    <div style="flex:1;min-width:0;">
                        <div style="font-weight:700;font-size:13px;color:var(--beurer-magenta);margin-bottom:4px;">+ ${_esc(a.name)}</div>
                        <div style="font-size:12px;color:var(--gray-700);line-height:1.5;margin-bottom:6px;">${_esc(a.rationale)}</div>
                        <div style="font-size:11px;color:var(--gray-800);"><strong>Impact:</strong> ${_esc(a.estimated_impact)}</div>
                    </div>
                    <button style="background:var(--beurer-magenta);color:white;border:none;padding:6px 14px;border-radius:var(--radius-sm);font-size:12px;cursor:pointer;font-weight:600;white-space:nowrap;">Aktivieren</button>
                </div>
            </div>`;
        });
    }

    html += `</div>`;
    host.innerHTML = html;
}

// Ensure Pipeline tab renders when activated. Patch the tab-activation flow.
(function() {
    if (typeof window === 'undefined' || window.location.protocol !== 'file:') return;
    const _origActivate = window.activateSidebarTab;
    if (typeof _origActivate === 'function') {
        window.activateSidebarTab = function(tabId) {
            _origActivate.call(this, tabId);
            if (tabId === 'pipeline') {
                setTimeout(() => { try { renderPipelineTab(); } catch (e) { console.error(e); } }, 30);
            }
        };
    }

    // Inject a Pipeline sidebar item at DOMContentLoaded (after nav is rendered)
    function injectPipelineNav() {
        const nav = document.getElementById('sidebarNav');
        if (!nav) { setTimeout(injectPipelineNav, 100); return; }
        if (nav.querySelector('[data-tab="pipeline"]')) return;
        // Place it right after "Content Planung" under the INHALTE group
        const contentBtn = nav.querySelector('[data-tab="content"]');
        const icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="6" height="6" rx="1"/><rect x="15" y="4" width="6" height="6" rx="1"/><rect x="9" y="14" width="6" height="6" rx="1"/><path d="M6 10v2a2 2 0 0 0 2 2h1"/><path d="M18 10v2a2 2 0 0 1-2 2h-1"/></svg>`;
        const btn = document.createElement('button');
        btn.className = 'sidebar-nav-item';
        btn.dataset.tab = 'pipeline';
        btn.dataset.tooltip = 'Pipeline · Agenten';
        btn.innerHTML = `${icon}<span class="nav-label">Pipeline · Agenten</span>`;
        btn.addEventListener('click', () => activateSidebarTab('pipeline'));
        if (contentBtn && contentBtn.nextSibling) {
            contentBtn.parentNode.insertBefore(btn, contentBtn.nextSibling);
        } else {
            nav.appendChild(btn);
        }
    }
    document.addEventListener('DOMContentLoaded', injectPipelineNav);
    if (document.readyState !== 'loading') injectPipelineNav();
})();
"""


if __name__ == "__main__":
    main()
