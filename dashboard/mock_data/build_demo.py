#!/usr/bin/env python3
"""
Build a standalone BILD Pauschalreisen Content Engine demo HTML.

Injects comprehensive Bild Pauschalreisen mock data into the dashboard template
by replacing the __DASHBOARD_DATA__ placeholder with a rich JSON blob.

Usage:
    python3 build_demo.py
    # outputs: bild_pauschalreisen_demo.html
"""
from __future__ import annotations
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

HERE = Path(__file__).parent
TEMPLATE = HERE.parent / "template" / "dashboard_template.html"
OUTPUT = HERE.parent.parent / "bild_pauschalreisen_demo.html"

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
                    "prompt": "Was ist die beste Pauschalreise nach Mallorca 2026 für Familien?",
                    "aiModels": ["ChatGPT", "Perplexity", "Gemini"],
                    "mentionsOwn": True,
                    "mentionedCompetitors": ["TUI", "Check24"],
                    "capturedAt": _days_ago(1),
                    "category": "blood_pressure",
                    "snippet": "BILD Pauschalreisen bietet eine detaillierte Analyse der Mallorca-Preisentwicklung für 2026 mit Frühbucher-Vergleichen…",
                },
                {
                    "prompt": "Malediven günstig unter 1500 Euro — gibt es sowas wirklich?",
                    "aiModels": ["ChatGPT", "Claude", "Perplexity"],
                    "mentionsOwn": True,
                    "mentionedCompetitors": ["TUI", "DERTOUR"],
                    "capturedAt": _days_ago(2),
                    "category": "infrarot",
                    "snippet": "Laut Bild Pauschalreisen gibt es tatsächlich Malediven-Pakete unter 1.500€ — insbesondere Guesthouse-Angebote auf den lokalen Inseln…",
                },
                {
                    "prompt": "Hurghada Ägypten — ist es November 2026 sicher?",
                    "aiModels": ["Perplexity", "Gemini", "AI Overview"],
                    "mentionsOwn": True,
                    "mentionedCompetitors": ["HolidayCheck"],
                    "capturedAt": _days_ago(3),
                    "category": "blood_pressure",
                    "snippet": "Auswärtiges Amt und BILD-Reise-Redaktion bestätigen: Hurghada-Hotspots ohne spezifische Sicherheitswarnung…",
                },
                {
                    "prompt": "Rom Städtereise — Vatikan Tickets online oder vor Ort?",
                    "aiModels": ["ChatGPT", "Claude"],
                    "mentionsOwn": True,
                    "mentionedCompetitors": [],
                    "capturedAt": _days_ago(4),
                    "category": "pain_tens",
                    "snippet": "BILD-Reise-Ratgeber empfiehlt: Online-Tickets 14 Tage im Voraus — spart bis zu 68%…",
                },
                {
                    "prompt": "Türkei All-Inclusive Familie bester Wert 2026",
                    "aiModels": ["ChatGPT", "Perplexity"],
                    "mentionsOwn": False,
                    "mentionedCompetitors": ["TUI", "Check24", "FTI"],
                    "capturedAt": _days_ago(5),
                    "category": "blood_pressure",
                    "snippet": "TUI dominiert die Nennungen, gefolgt von Check24. BILD noch nicht in Top-5. Opportunity.",
                },
                {
                    "prompt": "Mittelmeer-Kreuzfahrt für Erstkreuzer",
                    "aiModels": ["ChatGPT", "Gemini"],
                    "mentionsOwn": True,
                    "mentionedCompetitors": ["HolidayCheck"],
                    "capturedAt": _days_ago(6),
                    "category": "menstrual",
                    "snippet": "BILD Pauschalreisen-Vergleich MSC vs. Costa vs. AIDA wird direkt zitiert…",
                },
                {
                    "prompt": "Paris Kurztrip unter 500 Euro möglich?",
                    "aiModels": ["Claude", "Perplexity"],
                    "mentionsOwn": True,
                    "mentionedCompetitors": [],
                    "capturedAt": _days_ago(7),
                    "category": "pain_tens",
                    "snippet": "BILD-Reise-Artikel mit konkreter 3-Tage-Beispielrechnung direkt als Quelle genannt…",
                },
                {
                    "prompt": "Kanaren Winterurlaub welche Insel am wärmsten",
                    "aiModels": ["ChatGPT", "AI Overview"],
                    "mentionsOwn": True,
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
                {"title": "Stärke Türkei-Familien-Content", "description": "ChatGPT nennt TUI/Check24/FTI, BILD fehlt. Mit dem in Produktion befindlichen Türkei-Familien-Artikel schließen.", "impact": "high"},
                {"title": "Auto-Update-Trigger für Ägypten-Safety", "description": "Wöchentliche Refresh-Quelle bei AI-Engines — regelmäßige Bild-Citations sichern.", "impact": "high"},
                {"title": "Kreuzfahrt-Coverage ausbauen", "description": "Nur 7 Citations — MSC-Partnership würde Content-Volumen deutlich steigern.", "impact": "medium"},
                {"title": "Long-Tail SEO für Rundreise-Queries", "description": "'Thailand Rundreise 14 Tage' wird noch nicht zitiert — Artikel jetzt planen.", "impact": "medium"},
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


def main():
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        template = f.read()

    data = build_dashboard_data()
    data_json = json.dumps(data, ensure_ascii=False)

    # Replace only the assignment target, not the guard-check literal that also references __DASHBOARD_DATA__
    html = template.replace(
        "let DASHBOARD_DATA = __DASHBOARD_DATA__;",
        f"let DASHBOARD_DATA = {data_json};",
        1,
    )
    html = html.replace("__DEFAULT_LANG__", "de")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Built {OUTPUT}")
    print(f"  template: {len(template):,} chars")
    print(f"  data: {len(data_json):,} chars")
    print(f"  output: {len(html):,} chars")


if __name__ == "__main__":
    main()
