"""Shared constants for report generation.

Centralized constants used across data_aggregator, pdf_renderer,
html_renderer, excel_renderer, and report_service modules.
"""

# =============================================================================
# BEURER CORPORATE COLORS
# =============================================================================
BEURER_MAGENTA = "#C60050"
BEURER_DARK = "#1a1a1a"
BEURER_LIGHT = "#f5f5f5"
BEURER_GRAY = "#666666"

# =============================================================================
# PRODUCT CATALOGS (structured) + flat lists (backward compat)
# =============================================================================
BEURER_PRODUCT_CATALOG = {
    "BM 27": {"category": "blood_pressure", "priority": 1},
    "BM 25": {"category": "blood_pressure", "priority": 1},
    "BM 81": {"category": "blood_pressure", "priority": 1},
    "BC 81": {"category": "blood_pressure", "priority": 1},
    "BM 53": {"category": "blood_pressure", "priority": 2},
    "BM 64": {"category": "blood_pressure", "priority": 2},
    "BC 54": {"category": "blood_pressure", "priority": 2},
    "BC 27": {"category": "blood_pressure", "priority": 2},
    "BM 54": {"category": "blood_pressure", "priority": 3},
    "BM 59": {"category": "blood_pressure", "priority": 3},
    "BM 96": {"category": "blood_pressure", "priority": 3},
    "BM 58": {"category": "blood_pressure", "priority": 4},  # legacy
    "BM 77": {"category": "blood_pressure", "priority": 4},  # legacy
    "BM 85": {"category": "blood_pressure", "priority": 4},  # legacy
    "EM 59": {"category": "pain_tens", "priority": 1},
    "EM 89": {"category": "pain_tens", "priority": 1},
    "EM 50": {"category": "pain_tens", "priority": 2},
    "EM 55": {"category": "pain_tens", "priority": 2},
    "EM 49": {"category": "pain_tens", "priority": 3},  # legacy
    "EM 80": {"category": "pain_tens", "priority": 3},  # legacy
    "IL 50": {"category": "infrarot", "priority": 1},
    "IL 60": {"category": "infrarot", "priority": 1},
}
BEURER_PRODUCTS = list(BEURER_PRODUCT_CATALOG.keys())

COMPETITOR_PRODUCT_CATALOG = {
    "Omron M500":              {"category": "blood_pressure", "brand": "Omron"},
    "Omron M400":              {"category": "blood_pressure", "brand": "Omron"},
    "Withings BPM":            {"category": "blood_pressure", "brand": "Withings"},
    "AUVON TENS Gerät":        {"category": "pain_tens", "brand": "AUVON"},
    "Orthomechanik TENS/EMS":  {"category": "pain_tens", "brand": "Orthomechanik"},
    "Comfytemp TENS Gerät":    {"category": "pain_tens", "brand": "Comfytemp"},
    "GHTENS":                  {"category": "pain_tens", "brand": "GHTENS"},
    "Comfytemp Wärmegürtel":   {"category": "infrarot", "brand": "Comfytemp"},
    "Slimpal Wärmegürtel":     {"category": "infrarot", "brand": "Slimpal"},
    "Medisana IR 850":         {"category": "infrarot", "brand": "Medisana"},
    # AI-cited competitors (Peec AI data, Feb 2026)
    "SaneoTENS":               {"category": "pain_tens", "brand": "SaneoTENS"},
    "Axion TENS":              {"category": "pain_tens", "brand": "Axion"},
    "Menstruflow TENS":        {"category": "menstrual", "brand": "Menstruflow"},
}
COMPETITOR_PRODUCTS = list(COMPETITOR_PRODUCT_CATALOG.keys()) + ["Omron"]

# Maps brand name -> set of categories derived from product catalogs
BRAND_CATEGORY_MAP = {}
for _prod, _meta in COMPETITOR_PRODUCT_CATALOG.items():
    _brand = _meta["brand"]
    BRAND_CATEGORY_MAP.setdefault(_brand, set()).add(_meta["category"])
# Add Omron explicitly (keyword-only competitor, no product entry for bare "Omron")
BRAND_CATEGORY_MAP.setdefault("Omron", set()).add("blood_pressure")

# Beurer category map (from BEURER_PRODUCT_CATALOG)
BEURER_CATEGORY_MAP = {}
for _prod, _meta in BEURER_PRODUCT_CATALOG.items():
    BEURER_CATEGORY_MAP.setdefault("Beurer", set()).add(_meta["category"])


def format_products_for_llm_prompt() -> str:
    """Build product list string for classification/LLM prompts."""
    by_cat = {}
    for product, meta in BEURER_PRODUCT_CATALOG.items():
        by_cat.setdefault(meta["category"], []).append(product)
    lines = []
    cat_labels = {
        "blood_pressure": "Blood pressure monitors",
        "pain_tens": "TENS/EMS devices",
        "infrarot": "Infrared lamps",
    }
    for cat, label in cat_labels.items():
        if cat in by_cat:
            lines.append(f"- {label}: {', '.join(by_cat[cat])}")
    return "\n".join(lines)

# =============================================================================
# DEVICE-RELATED KEYWORDS
# =============================================================================
DEVICE_KEYWORDS = [
    "messgerät", "gerät", "oberarm", "handgelenk", "manschette",
    "display", "akku", "batterie", "genauigkeit", "fehler",
    "app", "bluetooth", "kaufen", "empfehlen", "tens", "ems",
    "modell", "sensor", "kalibrieren", "anzeige", "speicher"
]

# Brand names to boost relevance
BRAND_NAMES = [
    "beurer", "omron", "withings", "sanitas", "medisana", "braun",
    "auvon", "orthomechanik", "comfytemp", "slimpal", "ghtens",
    "saneotens", "saneo", "axion", "menstruflow",
]

# =============================================================================
# HEALTH-ONLY PATTERNS (No device context)
# =============================================================================
HEALTH_ONLY_PATTERNS = [
    "sind meine werte normal",
    "habe ich bluthochdruck",
    "ist mein blutdruck",
    "was bedeutet",
    "symptome",
    "arzt fragen",
    "zum arzt",
    # Age/body questions without device context
    "ab wie vielen jahren",
    "wie alt",
    "für welches alter",
    "macht den bauch",
    "körper",
    "muskeln aufbauen",
    # General health without device focus
    "abnehmen",
    "gewicht",
    "ernährung"
]

# =============================================================================
# QUESTION CATEGORIZATION PATTERNS
# =============================================================================
PURCHASE_INTENT_PATTERNS = [
    "kaufen", "bestellen", "empfehlen", "empfehlung", "vergleich",
    "preisvergleich", "lohnt sich", "apotheke",
    "welches gerät", "welches modell",
    "wo kaufen", "wo bestellen",
    "online kaufen", "online bestellen",
]

TROUBLESHOOTING_PATTERNS = [
    "fehler", "error", "funktioniert nicht", "problem", "defekt", "kaputt",
    "zeigt nicht", "falsch", "ungenau", "batterie", "akku", "reparatur",
    "garantie", "reklamation", "hilfe", "support", "anleitung"
]

USAGE_PATTERNS = [
    "wie messe", "richtig messen", "wann messen", "wie oft", "anleitung",
    "bedienung", "verwenden", "benutzen", "einstellen", "kalibrieren",
    "app verbinden", "bluetooth", "speichern", "auswerten"
]

# =============================================================================
# GERMAN CATEGORY LABELS
# =============================================================================
CATEGORY_LABELS_DE = {
    "blood_pressure": "Blutdruck",
    "pain_tens": "Schmerz/TENS",
    "infrarot": "Infrarot/Wärme",
    "menstrual": "Menstruation",
    "other": "Sonstige",
    "unclassified": "Nicht klassifiziert",
    "unknown": "Unbekannt"
}

# Question category labels
QUESTION_CATEGORY_LABELS_DE = {
    "purchase_intent": "Kaufberatung",
    "troubleshooting": "Problem",
    "usage": "Anwendung"
}

# Severity labels
SEVERITY_LABELS_DE = {
    "high": "Hoch",
    "medium": "Mittel",
    "low": "Niedrig"
}

# =============================================================================
# SCORE DEFINITIONS
# =============================================================================
# These scores are used throughout the report to prioritize and filter items.

SCORE_DEFINITIONS = {
    "relevance_score": {
        "name": "Strategische Relevanz",
        "name_en": "Strategic Relevance Score",
        "range": "0.0 - 1.0",
        "description_de": (
            "Bewertet, wie handlungsrelevant und aufschlussreich ein Beitrag "
            "für Beurers Produktstrategie ist. Wird durch LLM-Klassifizierung "
            "(Gemini) berechnet mit expliziten Bewertungsstufen und Konsistenzprüfung "
            "gegen den Geräte-Relevanz-Score."
        ),
        "description_en": (
            "Evaluates how actionable and insightful a post is for Beurer's "
            "product strategy. Calculated by LLM classification (Gemini) with "
            "explicit scoring tiers and consistency check against device relevance score."
        ),
        "interpretation": {
            "0.9-1.0": "Sehr hoch - Spezifische Beurer-Produkterfahrung oder -Empfehlung",
            "0.7-0.8": "Hoch - Kaufentscheidung, Produktvergleich oder konkretes Geräteproblem",
            "0.5-0.6": "Mittel - Gerätekategorie-Diskussion mit verwertbaren Erkenntnissen",
            "0.3-0.4": "Niedrig - Entfernt verwandtes Gesundheitsthema, kein Gerätebezug",
            "0.0-0.2": "Minimal - Reine Gesundheits-/Lifestyle-Frage ohne Produkt-Kontext"
        }
    },
    "device_relevance_score": {
        "name": "Geräte-Relevanz-Score",
        "name_en": "Device Relevance Score",
        "range": "0.0 - 1.0",
        "description_de": (
            "Bewertet, wie stark ein Beitrag auf Geräte/Produkte fokussiert ist "
            "(im Gegensatz zu reinen Gesundheitsfragen). Wird durch LLM-Klassifizierung berechnet."
        ),
        "description_en": (
            "Evaluates how device/product-focused a post is "
            "(as opposed to pure health questions). Calculated by LLM classification."
        ),
        "interpretation": {
            "0.9-1.0": "Nennt spezifisches Gerät/Marke direkt",
            "0.7-0.8": "Fragt nach Empfehlungen/Vergleichen",
            "0.5-0.6": "Erwähnt Gerätekategorie, fokussiert auf Nutzung",
            "0.3-0.4": "Könnte mit Gerät beantwortet werden",
            "0.0-0.2": "Reine Gesundheitsfrage, kein Gerätebezug"
        }
    },
    "gap_score": {
        "name": "Content-Gap-Score",
        "name_en": "Content Gap Score",
        "range": "0.0 - 1.2",
        "description_de": (
            "Identifiziert Content-Chancen basierend auf Relevanz-Score plus Bonus "
            "für bevorzugte Q&A-Quellen (gutefrage, reddit, Foren). "
            "Höhere Werte = größere Chance für Beurer-Content."
        ),
        "description_en": (
            "Identifies content opportunities based on relevance score plus bonus "
            "for preferred Q&A sources (gutefrage, reddit, forums). "
            "Higher values = greater opportunity for Beurer content."
        ),
        "calculation": "relevance_score + 0.1 (wenn Quelle = gutefrage/reddit/forum)",
        "interpretation": {
            "0.8-1.2": "Hohe Priorität - Unbeantwortete Frage mit starkem Gerätebezug",
            "0.6-0.8": "Mittlere Priorität - Gute Content-Chance",
            "0.5-0.6": "Niedrige Priorität - Mögliche Chance"
        }
    }
}

# Short descriptions for Excel column headers
SCORE_TOOLTIPS = {
    "relevance_score": "0-1: Strategische Relevanz für Beurer (LLM-berechnet)",
    "device_relevance_score": "0-1: Gerätebezug vs. reine Gesundheitsfrage",
    "gap_score": "0-1.2: Content-Chance (Relevanz + Quellen-Bonus)"
}

# =============================================================================
# SENTIMENT DEEP-DIVE CONSTANTS
# =============================================================================

# Sentiment cause categories for deep-dive analysis
# 9 categories with expanded keywords for ~100% classification coverage.
# Order matters: first match wins during classification.
SENTIMENT_CAUSES = {
    "geraete_fehler": {
        "label_de": "Geräte-Fehler",
        "keywords": [
            "defekt", "kaputt", "funktioniert nicht", "fehler", "broken", "geht nicht",
            "ausgefallen", "stürzt ab", "startet nicht", "schaltet sich ab", "reagiert nicht",
            "display defekt", "fehlermeldung", "error", "eingeschickt", "garantiefall",
            "ersatzgerät", "hält nicht lange", "lebensdauer", "geht nicht mehr",
            "funktioniert nicht mehr", "abgebrochen", "ausfall"
        ],
        "action_default": "QA/Support informieren, Fehler dokumentieren",
        "is_actionable": True
    },
    "messgenauigkeit": {
        "label_de": "Messgenauigkeit",
        "keywords": [
            "ungenau", "falsche werte", "messwerte stimmen nicht", "abweichung", "schwankt",
            "arzt misst anders", "beim arzt anders", "weicht ab", "messfehler", "misst falsch",
            "misst zu hoch", "misst zu niedrig", "unzuverlässig", "kalibrieren", "genauigkeit",
            "messungenauigkeit", "unterschiedliche werte", "werte stimmen nicht",
            "ergebnis stimmt nicht", "nicht genau", "falsch gemessen"
        ],
        "action_default": "Produktteam informieren, FAQ zu korrekter Messung erstellen",
        "is_actionable": True
    },
    "komfort_anwendung": {
        "label_de": "Komfort/Anwendung",
        "keywords": [
            "kompliziert", "verwirrend", "anleitung", "schwierig", "umständlich",
            "nicht intuitiv", "unbequem", "drückt", "manschette zu eng", "manschette rutscht",
            "unangenehm", "zu laut", "display schlecht lesbar", "schrift zu klein",
            "handhabung", "bedienung", "zu groß", "zu schwer", "unpraktisch",
            "schlecht ablesbar", "schwer zu bedienen"
        ],
        "action_default": "UX-Feedback an Produktmanagement, Tutorial-Content erstellen",
        "is_actionable": True
    },
    "app_konnektivitaet": {
        "label_de": "App/Konnektivität",
        "keywords": [
            "bluetooth", " app ", "verbindung", "koppeln", "pairing", "synchronisieren", "sync ",
            "daten übertragen", "app stürzt", "verbindet sich nicht", "healthmanager",
            "health manager", "beurer app", "wlan", "datenübertragung", "kompatibel",
            "app funktioniert", "keine verbindung", "kopplung", "übertragung",
            "smartphone", "handy verbinden", "die app", "der app", "eine app"
        ],
        "action_default": "App-Team informieren, Kompatibilitätsliste prüfen",
        "is_actionable": True
    },
    "preis_wert": {
        "label_de": "Preis/Wert",
        "keywords": [
            "teuer", "preis", "kosten", "zu viel", "billiger", "günstig", "preis-leistung",
            "nicht wert", "überteuert", "lohnt sich nicht", "für den preis", "zu teuer",
            "preislich", "geld", "investition", "preisvergleich"
        ],
        "action_default": "Preispositionierung beobachten, Mehrwert-Kommunikation stärken",
        "is_actionable": True
    },
    "service_support": {
        "label_de": "Service/Support",
        "keywords": [
            "support", "kundenservice", "antwort", "garantie", "reparatur", "hotline",
            "erreichbar", "reaktionszeit", "wartezeit", "keine antwort", "unfreundlich",
            "reklamation", "beschwerde", "rücksendung", "erstattung", "service",
            "kundendienst", "kontakt", "nicht erreichbar", "lange warten"
        ],
        "action_default": "Service-Team informieren, Prozesse überprüfen",
        "is_actionable": True
    },
    "gesundheitsfrage": {
        "label_de": "Gesundheitsfrage",
        "keywords": [
            "sind meine werte normal", "habe ich bluthochdruck", "symptome", "arzt fragen",
            "zum arzt", "diagnose", "angst ", "sorge ", "medikament", "tabletten",
            "nebenwirkung", "therapie", "normwerte", "grenzwerte", "hypertonie",
            "bluthochdruck", "schmerzen", "krankheit", "behandlung", "gesundheit",
            "beim arzt", "mein arzt", "zum arzt", "krank ", "meine werte"
        ],
        "action_default": "Kein direkter Handlungsbedarf (Gesundheitsthema)",
        "is_actionable": False
    },
    "wettbewerber_bezogen": {
        "label_de": "Wettbewerber-bezogen",
        "keywords": [
            "omron", "withings", "sanitas", "medisana", "braun", "boso", "aponorm",
            "auvon", "orthomechanik", "comfytemp", "slimpal", "ghtens",
            "saneotens", "saneo", "saneostore", "axion", "menstruflow",
            "andere marke", "konkurrenz", "wettbewerber"
        ],
        "action_default": "Kein direkter Handlungsbedarf (Wettbewerber-Feedback)",
        "is_actionable": False
    },
    "sonstiges": {
        "label_de": "Sonstiges",
        "keywords": [],
        "action_default": "Manuell prüfen",
        "is_actionable": False
    }
}

# Competitor brand mapping for competitive intelligence
COMPETITOR_BRANDS = {
    "omron": "Omron",
    "withings": "Withings",
    "sanitas": "Sanitas",
    "medisana": "Medisana",
    "braun": "Braun",
    "auvon": "AUVON",
    "orthomechanik": "Orthomechanik",
    "comfytemp": "Comfytemp",
    "slimpal": "Slimpal",
    "ghtens": "GHTENS",
    "saneotens": "SaneoTENS",
    "saneo": "SaneoTENS",
    "saneostore": "SaneoTENS",
    "axion": "Axion",
    "menstruflow": "Menstruflow",
}

# =============================================================================
# KEY ACTIONS CONSTANTS
# =============================================================================

# Priority levels for Key Actions section
PRIORITY_LEVELS = {
    "urgent": {"label": "URGENT", "label_de": "DRINGEND", "color": "#FF3B30", "deadline": "Sofort"},
    "high": {"label": "HIGH", "label_de": "HOCH", "color": "#FF9500", "deadline": "Diese Woche"},
    "normal": {"label": "NORMAL", "label_de": "NORMAL", "color": "#34C759", "deadline": "Nächste Woche"}
}

# Responsible parties for action items
RESPONSIBLE_PARTIES = {
    "support": "Support",
    "content": "Content",
    "marketing": "Marketing",
    "qa": "QA",
    "product": "Produkt"
}

# =============================================================================
# CUSTOMER JOURNEY INTELLIGENCE CONSTANTS
# =============================================================================

# Journey stages (1-5) matching the Customer Journey Intelligence design doc
JOURNEY_STAGES = [
    "awareness",        # Stage 1: Pain/problem awareness — user recognizes a health issue
    "consideration",    # Stage 2: Solution seeking — user researches possible solutions
    "comparison",       # Stage 3: Method/product comparison — user evaluates specific options
    "purchase",         # Stage 4: Purchase decision — user buys or asks about buying
    "advocacy",         # Stage 5: Post-purchase advocacy — user shares experience/recommends
]

JOURNEY_STAGE_LABELS_DE = {
    "awareness": "Bewusstsein",
    "consideration": "Lösungssuche",
    "comparison": "Vergleich",
    "purchase": "Kaufentscheidung",
    "advocacy": "Erfahrung/Empfehlung",
}

# Pain categories for pre-purchase journey analysis
PAIN_CATEGORY_LABELS_DE = {
    "ruecken_nacken": "Rücken-/Nackenschmerzen",
    "gelenke_arthrose": "Gelenk-/Arthroseschmerzen",
    "menstruation": "Menstruationsschmerzen",
    "kopfschmerzen": "Kopfschmerzen/Migräne",
    "bluthochdruck": "Bluthochdruck/Kreislauf",
    "neuropathie": "Neuropathie/Nervenschmerzen",
    "sonstige_schmerzen": "Sonstige Schmerzen",
}

# Solution types mentioned in discussions
SOLUTION_LABELS_DE = {
    "tens_ems": "TENS/EMS-Therapie",
    "waermetherapie": "Wärmetherapie/Infrarot",
    "blutdruckmessung": "Blutdruckmessung",
    "medikamente": "Medikamente",
    "physiotherapie": "Physiotherapie",
    "hausmittel": "Hausmittel/Naturheilkunde",
    "arztbesuch": "Arztbesuch",
    "sport_bewegung": "Sport/Bewegung",
    "massage": "Massage",
    "akupunktur": "Akupunktur",
    "sonstiges": "Sonstige",
}

# Solutions with high Beurer product relevance (for bridge moment detection)
HIGH_BEURER_RELEVANCE_SOLUTIONS = [
    "tens_ems",
    "waermetherapie",
    "blutdruckmessung",
]

# =============================================================================
# DEEP INSIGHTS CLASSIFICATION CONSTANTS
# =============================================================================

# Pain locations (pain_tens / menstrual items)
PAIN_LOCATIONS = [
    "ruecken_oberer", "ruecken_unterer", "nacken", "schulter", "knie",
    "huelte", "handgelenk", "ellbogen", "fuss", "unterleib", "ganzer_koerper",
    "kopf_migraene", "nerven_ischias", "gelenke_allgemein", "muskelverspannung",
    "fibromyalgie",
]
PAIN_LOCATION_LABELS_DE = {
    "ruecken_oberer": "Oberer Rücken",
    "ruecken_unterer": "Unterer Rücken / LWS",
    "nacken": "Nacken / HWS",
    "schulter": "Schulter",
    "knie": "Knie",
    "huelte": "Hüfte",
    "handgelenk": "Handgelenk",
    "ellbogen": "Ellbogen",
    "fuss": "Fuß / Sprunggelenk",
    "unterleib": "Unterleib / Becken",
    "ganzer_koerper": "Ganzer Körper / Diffus",
    "kopf_migraene": "Kopf / Migräne",
    "nerven_ischias": "Nerven / Ischias",
    "gelenke_allgemein": "Gelenke (allgemein)",
    "muskelverspannung": "Muskelverspannung",
    "fibromyalgie": "Fibromyalgie",
}

# Pain severity
PAIN_SEVERITIES = ["leicht", "mittel", "stark", "chronisch", "akut"]
PAIN_SEVERITY_LABELS_DE = {
    "leicht": "Leicht",
    "mittel": "Mittel",
    "stark": "Stark",
    "chronisch": "Chronisch",
    "akut": "Akut",
}

# Pain duration
PAIN_DURATIONS = ["akut_tage", "wochen", "monate", "jahre_chronisch", "episodisch"]
PAIN_DURATION_LABELS_DE = {
    "akut_tage": "Akut (Tage)",
    "wochen": "Wochen",
    "monate": "Monate",
    "jahre_chronisch": "Jahre / Chronisch",
    "episodisch": "Episodisch (wiederkehrend)",
}

# Blood pressure concern types
BP_CONCERN_TYPES = [
    "messgenauigkeit", "schwankende_werte", "weisser_kittel",
    "medikamenten_kontrolle", "morgen_abend_unterschied",
    "arm_unterschied", "geraete_vergleich", "normwerte_frage",
    "hypertonie_angst", "monitoring_routine",
]
BP_CONCERN_LABELS_DE = {
    "messgenauigkeit": "Messgenauigkeit",
    "schwankende_werte": "Schwankende Werte",
    "weisser_kittel": "Weißkittel-Hypertonie",
    "medikamenten_kontrolle": "Medikamenten-Kontrolle",
    "morgen_abend_unterschied": "Morgen-/Abend-Unterschied",
    "arm_unterschied": "Links-/Rechts-Arm-Unterschied",
    "geraete_vergleich": "Geräte-Vergleich (Arzt vs. Zuhause)",
    "normwerte_frage": "Normwerte-Frage",
    "hypertonie_angst": "Hypertonie-Angst",
    "monitoring_routine": "Monitoring-Routine",
}

# Blood pressure severity
BP_SEVERITIES = ["optimal", "normal", "hoch_normal", "hypertonie_1", "hypertonie_2", "unspecified"]
BP_SEVERITY_LABELS_DE = {
    "optimal": "Optimal (<120/80)",
    "normal": "Normal (120-129/80-84)",
    "hoch_normal": "Hoch-Normal (130-139/85-89)",
    "hypertonie_1": "Hypertonie Grad 1 (140-159/90-99)",
    "hypertonie_2": "Hypertonie Grad 2+ (≥160/≥100)",
    "unspecified": "Unspezifiziert (BP erwähnt, kein Wert)",
}

# Life situations
LIFE_SITUATIONS = [
    "schwangerschaft", "buero_arbeit", "sport_aktiv", "senioren",
    "eltern_baby", "pendler", "schichtarbeit", "homeoffice",
    "pflegende_angehoerige", "studenten", "chronisch_krank",
    "post_op", "uebergewicht", "stress_burnout", "reisende",
    "frisch_diagnostiziert", "medikamenten_nebenwirkungen_sucher",
    "fitness_ems", "migraene_patient", "fibromyalgie_patient", "endometriose",
]
LIFE_SITUATION_LABELS_DE = {
    "schwangerschaft": "Schwangerschaft",
    "buero_arbeit": "Büro-/Schreibtischarbeit",
    "sport_aktiv": "Sport / Aktiver Lebensstil",
    "senioren": "Senioren / Ältere Erwachsene",
    "eltern_baby": "Eltern / Babypflege",
    "pendler": "Pendler / Unterwegs",
    "schichtarbeit": "Schichtarbeit",
    "homeoffice": "Homeoffice",
    "pflegende_angehoerige": "Pflegende Angehörige",
    "studenten": "Studenten",
    "chronisch_krank": "Chronisch Erkrankte",
    "post_op": "Post-OP / Rehabilitation",
    "uebergewicht": "Übergewicht / Adipositas",
    "stress_burnout": "Stress / Burnout",
    "reisende": "Reisende",
    "frisch_diagnostiziert": "Frisch diagnostiziert",
    "medikamenten_nebenwirkungen_sucher": "Medikamenten-Nebenwirkungen",
    "fitness_ems": "Fitness / EMS-Training",
    "migraene_patient": "Migräne-Patient",
    "fibromyalgie_patient": "Fibromyalgie-Patient",
    "endometriose": "Endometriose",
}

# User segments (WHO the person is) — split from life_situation
USER_SEGMENTS = [
    "schwangerschaft", "buero_arbeit", "sport_aktiv", "senioren",
    "eltern_baby", "pendler", "schichtarbeit", "homeoffice",
    "pflegende_angehoerige", "studenten", "reisende", "fitness_ems",
]
USER_SEGMENT_LABELS_DE = {
    "schwangerschaft": "Schwangerschaft",
    "buero_arbeit": "Büro-/Schreibtischarbeit",
    "sport_aktiv": "Sport / Aktiver Lebensstil",
    "senioren": "Senioren / Ältere Erwachsene",
    "eltern_baby": "Eltern / Babypflege",
    "pendler": "Pendler / Unterwegs",
    "schichtarbeit": "Schichtarbeit",
    "homeoffice": "Homeoffice",
    "pflegende_angehoerige": "Pflegende Angehörige",
    "studenten": "Studenten",
    "reisende": "Reisende",
    "fitness_ems": "Fitness / EMS-Training",
}
USER_SEGMENT_LABELS_EN = {
    "schwangerschaft": "Pregnancy",
    "buero_arbeit": "Office/Desk Work",
    "sport_aktiv": "Sports / Active Lifestyle",
    "senioren": "Seniors / Older Adults",
    "eltern_baby": "Parents / Baby Care",
    "pendler": "Commuters / On-the-go",
    "schichtarbeit": "Shift Work",
    "homeoffice": "Home Office",
    "pflegende_angehoerige": "Family Caregivers",
    "studenten": "Students",
    "reisende": "Travelers",
    "fitness_ems": "Fitness / EMS Training",
}

# Problem categories (WHAT condition they have) — split from life_situation
PROBLEM_CATEGORIES_LIST = [
    "chronisch_krank", "post_op", "uebergewicht", "stress_burnout",
    "frisch_diagnostiziert", "medikamenten_nebenwirkungen_sucher",
    "migraene_patient", "fibromyalgie_patient", "endometriose",
]
PROBLEM_CATEGORY_LABELS_DE = {
    "chronisch_krank": "Chronisch Erkrankte",
    "post_op": "Post-OP / Rehabilitation",
    "uebergewicht": "Übergewicht / Adipositas",
    "stress_burnout": "Stress / Burnout",
    "frisch_diagnostiziert": "Frisch diagnostiziert",
    "medikamenten_nebenwirkungen_sucher": "Medikamenten-Nebenwirkungen",
    "migraene_patient": "Migräne-Patient",
    "fibromyalgie_patient": "Fibromyalgie-Patient",
    "endometriose": "Endometriose",
}
PROBLEM_CATEGORY_LABELS_EN = {
    "chronisch_krank": "Chronically Ill",
    "post_op": "Post-Surgery / Rehabilitation",
    "uebergewicht": "Overweight / Obesity",
    "stress_burnout": "Stress / Burnout",
    "frisch_diagnostiziert": "Newly Diagnosed",
    "medikamenten_nebenwirkungen_sucher": "Medication Side Effects",
    "migraene_patient": "Migraine Patient",
    "fibromyalgie_patient": "Fibromyalgia Patient",
    "endometriose": "Endometriosis",
}

# Solution frustrations
SOLUTION_FRUSTRATIONS = [
    "keine_besserung", "nebenwirkungen_medikamente", "zu_teuer",
    "keine_langzeitwirkung", "unangenehme_anwendung", "widerspruechliche_infos",
    "arzt_nimmt_nicht_ernst", "wartezeit_arzt", "geraet_kompliziert",
    "manschette_problem", "app_verbindung", "messungenauigkeit",
]
FRUSTRATION_LABELS_DE = {
    "keine_besserung": "Keine Besserung trotz Therapie",
    "nebenwirkungen_medikamente": "Nebenwirkungen von Medikamenten",
    "zu_teuer": "Zu teuer / Kosten",
    "keine_langzeitwirkung": "Keine Langzeitwirkung",
    "unangenehme_anwendung": "Unangenehme Anwendung",
    "widerspruechliche_infos": "Widersprüchliche Informationen",
    "arzt_nimmt_nicht_ernst": "Arzt nimmt nicht ernst",
    "wartezeit_arzt": "Wartezeit beim Arzt",
    "geraet_kompliziert": "Gerät zu kompliziert",
    "manschette_problem": "Manschetten-Problem",
    "app_verbindung": "App-/Verbindungsprobleme",
    "messungenauigkeit": "Mess-Ungenauigkeit",
}

# Negative root causes
NEGATIVE_ROOT_CAUSES = [
    "produkt_defekt", "fehlbedienung", "falsche_erwartung",
    "kompatibilitaet", "service_mangel", "preis_leistung", "design_ergonomie",
]
NEGATIVE_ROOT_CAUSE_LABELS_DE = {
    "produkt_defekt": "Produkt-Defekt / Hardware",
    "fehlbedienung": "Fehlbedienung / Anwenderfehler",
    "falsche_erwartung": "Falsche Erwartung",
    "kompatibilitaet": "Kompatibilitäts-Problem",
    "service_mangel": "Service-Mangel",
    "preis_leistung": "Preis-Leistung",
    "design_ergonomie": "Design / Ergonomie",
}

# Coping strategies (normalized keys for array field)
COPING_STRATEGIES = [
    "ibuprofen", "paracetamol", "physiotherapie", "tens_geraet",
    "waermetherapie", "yoga", "arztbesuch", "bp_medikamente",
    "home_monitoring", "ernaehrung_diaet", "meditation",
    "massage", "bewegung_sport", "entspannung",
    "kaltetherapie", "osteopathie", "chiropraktik", "akupunktur",
]
COPING_STRATEGY_LABELS_DE = {
    "ibuprofen": "Ibuprofen / Schmerzmittel",
    "paracetamol": "Paracetamol",
    "physiotherapie": "Physiotherapie",
    "tens_geraet": "TENS-Gerät",
    "waermetherapie": "Wärme-/Infrarottherapie",
    "yoga": "Yoga / Stretching",
    "arztbesuch": "Arztbesuch",
    "bp_medikamente": "Blutdruck-Medikamente",
    "home_monitoring": "Heim-Monitoring",
    "ernaehrung_diaet": "Ernährung / Diät",
    "meditation": "Meditation / Achtsamkeit",
    "massage": "Massage",
    "bewegung_sport": "Bewegung / Sport",
    "entspannung": "Entspannung / Stressabbau",
    "kaltetherapie": "Kältetherapie",
    "osteopathie": "Osteopathie",
    "chiropraktik": "Chiropraktik",
    "akupunktur": "Akupunktur",
}

# Bridge moment types (transition triggers in customer journey)
BRIDGE_MOMENT_TYPES = {
    "schmerz_loest_arztbesuch_aus": "Schmerz löst Arztbesuch aus",
    "medikament_loest_alternativsuche_aus": "Medikament löst Alternativsuche aus",
    "arzt_empfiehlt_geraet": "Arzt empfiehlt Gerät",
    "freund_empfiehlt_produkt": "Freund/Familie empfiehlt Produkt",
    "online_recherche_loest_kauf_aus": "Online-Recherche löst Kauf aus",
    "testbericht_weckt_interesse": "Testbericht weckt Interesse",
    "diagnose_loest_monitoring_aus": "Diagnose löst Monitoring aus",
    "vergleich_loest_entscheidung_aus": "Vergleich löst Entscheidung aus",
    "none_identified": "Kein Bridge-Moment identifiziert",
}

# =============================================================================
# EMOTION / INTENT / ASPECT / LANGUAGE CONSTANTS
# =============================================================================

EMOTION_VALUES = [
    "frustration", "relief", "anxiety", "satisfaction",
    "confusion", "anger", "hope", "resignation",
]
EMOTION_LABELS_DE = {
    "frustration": "Frustration",
    "relief": "Erleichterung",
    "anxiety": "Angst/Sorge",
    "satisfaction": "Zufriedenheit",
    "confusion": "Verwirrung",
    "anger": "Ärger/Wut",
    "hope": "Hoffnung",
    "resignation": "Resignation",
}

INTENT_VALUES = [
    "purchase_question", "troubleshooting", "experience_sharing",
    "recommendation_request", "comparison", "general_question",
    "complaint", "advocacy",
]
INTENT_LABELS_DE = {
    "purchase_question": "Kaufberatung",
    "troubleshooting": "Fehlerbehebung",
    "experience_sharing": "Erfahrungsbericht",
    "recommendation_request": "Empfehlungsanfrage",
    "comparison": "Vergleich",
    "general_question": "Allgemeine Frage",
    "complaint": "Beschwerde",
    "advocacy": "Empfehlung/Lob",
}

ASPECT_CATEGORIES = [
    "messgenauigkeit", "bedienbarkeit", "verarbeitung",
    "preis_leistung", "app_konnektivitaet", "manschette_elektroden",
    "display_anzeige", "schmerzlinderung", "akku_batterie", "kundenservice",
]
ASPECT_LABELS_DE = {
    "messgenauigkeit": "Messgenauigkeit",
    "bedienbarkeit": "Bedienbarkeit",
    "verarbeitung": "Verarbeitung/Qualität",
    "preis_leistung": "Preis-Leistung",
    "app_konnektivitaet": "App/Konnektivität",
    "manschette_elektroden": "Manschette/Elektroden",
    "display_anzeige": "Display/Anzeige",
    "schmerzlinderung": "Schmerzlinderung",
    "akku_batterie": "Akku/Batterie",
    "kundenservice": "Kundenservice",
}

LANGUAGE_VALUES = ["de", "en", "other"]

# =============================================================================
# KEYWORD → ASPECT KEY mapping (normalizes raw German keywords to aspect keys)
# =============================================================================
KEYWORD_TO_ASPECT = {
    # messgenauigkeit
    "ungenau": "messgenauigkeit", "falsche werte": "messgenauigkeit",
    "messwerte": "messgenauigkeit", "abweichung": "messgenauigkeit",
    "messgenauigkeit": "messgenauigkeit", "genauigkeit": "messgenauigkeit",
    "kalibrieren": "messgenauigkeit", "messfehler": "messgenauigkeit",
    # bedienbarkeit
    "kompliziert": "bedienbarkeit", "umständlich": "bedienbarkeit",
    "bedienung": "bedienbarkeit", "anleitung": "bedienbarkeit",
    "bedienbarkeit": "bedienbarkeit", "schwierig": "bedienbarkeit",
    # verarbeitung
    "verarbeitung": "verarbeitung", "qualität": "verarbeitung",
    "defekt": "verarbeitung", "kaputt": "verarbeitung",
    "billig": "verarbeitung", "plastik": "verarbeitung",
    # preis_leistung
    "teuer": "preis_leistung", "preis": "preis_leistung",
    "kosten": "preis_leistung", "preis-leistung": "preis_leistung",
    "günstig": "preis_leistung", "überteuert": "preis_leistung",
    # app_konnektivitaet
    "app": "app_konnektivitaet", "bluetooth": "app_konnektivitaet",
    "verbindung": "app_konnektivitaet", "koppeln": "app_konnektivitaet",
    "sync": "app_konnektivitaet", "konnektivität": "app_konnektivitaet",
    # manschette_elektroden
    "manschette": "manschette_elektroden", "elektroden": "manschette_elektroden",
    "drückt": "manschette_elektroden", "rutscht": "manschette_elektroden",
    "unbequem": "manschette_elektroden", "pad": "manschette_elektroden",
    # display_anzeige
    "display": "display_anzeige", "anzeige": "display_anzeige",
    "ablesbar": "display_anzeige", "schrift": "display_anzeige",
    "bildschirm": "display_anzeige",
    # schmerzlinderung
    "schmerzlinderung": "schmerzlinderung", "wirkung": "schmerzlinderung",
    "hilft nicht": "schmerzlinderung", "keine besserung": "schmerzlinderung",
    "wirkungslos": "schmerzlinderung", "linderung": "schmerzlinderung",
    # akku_batterie
    "batterie": "akku_batterie", "akku": "akku_batterie",
    "laufzeit": "akku_batterie", "laden": "akku_batterie",
    # kundenservice
    "kundenservice": "kundenservice", "support": "kundenservice",
    "garantie": "kundenservice", "reklamation": "kundenservice",
    "hotline": "kundenservice", "service": "kundenservice",
}

# =============================================================================
# ASPECT → ADVANTAGE MAP (3 variants each for dedup across competitors)
# =============================================================================
ASPECT_ADVANTAGE_MAP = {
    "messgenauigkeit": {
        "advantages": [
            "Klinisch validierte Messgenauigkeit",
            "WHO-konforme Messtechnologie",
            "Arzt-Referenzgenauigkeit für Zuhause",
        ],
        "content_ideas": [
            "Genauigkeitsvergleich: Beurer vs. {competitor} — Faktencheck",
            "Warum Messgenauigkeit entscheidend ist — Beurer-Vorteil zeigen",
            "Klinische Validierung erklärt: So schneidet Beurer ab vs. {competitor}",
        ],
    },
    "bedienbarkeit": {
        "advantages": [
            "Intuitive Ein-Knopf-Bedienung",
            "Benutzerfreundliches Design für alle Altersgruppen",
            "Einfachste Inbetriebnahme am Markt",
        ],
        "content_ideas": [
            "Bedienungsvergleich: Beurer vs. {competitor} im Alltagstest",
            "So einfach geht Messen — Beurer-Bedienbarkeit im Fokus",
            "Senioren-freundlich: Warum Beurer einfacher ist als {competitor}",
        ],
    },
    "verarbeitung": {
        "advantages": [
            "Deutsche Qualitätsstandards in der Verarbeitung",
            "Langlebige Materialien & robustes Design",
            "100 Jahre Beurer Qualitätstradition",
        ],
        "content_ideas": [
            "Qualitätsvergleich: Beurer-Verarbeitung vs. {competitor}",
            "Langlebigkeit im Test — warum Beurer länger hält als {competitor}",
            "Made with German engineering: Beurer-Qualität im Detail",
        ],
    },
    "preis_leistung": {
        "advantages": [
            "Besseres Preis-Leistungs-Verhältnis",
            "Mehr Funktionen zum gleichen Preis",
            "Langfristiger Wert durch Qualität & Service",
        ],
        "content_ideas": [
            "Preis-Leistungs-Vergleich: Beurer vs. {competitor}",
            "Was bekommt man für sein Geld? Beurer vs. {competitor} im Detail",
            "Gesamtkosten-Rechnung: Warum Beurer günstiger ist als {competitor}",
        ],
    },
    "app_konnektivitaet": {
        "advantages": [
            "Beurer HealthManager Pro App-Ökosystem",
            "Nahtlose Bluetooth-Kopplung & Datenexport",
            "Umfassende Gesundheitsdaten-Plattform",
        ],
        "content_ideas": [
            "App-Vergleich: Beurer HealthManager vs. {competitor}-App",
            "Konnektivität im Test — Beurer vs. {competitor} Bluetooth-Erfahrung",
            "Datenmanagement leicht gemacht: Beurer-App-Vorteile vs. {competitor}",
        ],
    },
    "manschette_elektroden": {
        "advantages": [
            "Ergonomische Universalmanschette für jeden Armumfang",
            "Hautfreundliche Elektroden mit optimaler Haftung",
            "Komfort-optimiertes Zubehör-Design",
        ],
        "content_ideas": [
            "Manschetten-Vergleich: Beurer-Komfort vs. {competitor}",
            "Elektroden-Qualität im Test — Beurer vs. {competitor}",
            "Tragekomfort entscheidet: Beurer-Zubehör-Vorteile vs. {competitor}",
        ],
    },
    "display_anzeige": {
        "advantages": [
            "XL-Display mit optimaler Ablesbarkeit",
            "Beleuchtetes Display für jede Lichtsituation",
            "Klare Anzeige mit Ampel-Farbsystem",
        ],
        "content_ideas": [
            "Display-Vergleich: Beurer vs. {competitor} Ablesbarkeit",
            "Lesbarkeit im Alltag — Beurer-Display vs. {competitor}",
            "Werte auf einen Blick: Beurer-Anzeige-Vorteile vs. {competitor}",
        ],
    },
    "schmerzlinderung": {
        "advantages": [
            "Klinisch erprobte TENS-Programme für gezielte Schmerzlinderung",
            "Breites Therapiespektrum mit individuellen Programmen",
            "Medizinprodukt-zertifizierte Schmerztherapie",
        ],
        "content_ideas": [
            "Wirksamkeitsvergleich: Beurer-TENS vs. {competitor} Schmerzlinderung",
            "Therapie-Programme im Test — Beurer vs. {competitor}",
            "Effektive Schmerzlinderung: Warum Beurer wirksamer ist als {competitor}",
        ],
    },
    "akku_batterie": {
        "advantages": [
            "Langlebige Batterie / USB-C Laden",
            "Energieeffizientes Design für lange Nutzungsdauer",
            "Flexible Stromversorgung (Akku + Batterie)",
        ],
        "content_ideas": [
            "Akkulaufzeit-Vergleich: Beurer vs. {competitor}",
            "Batterie im Alltag — Beurer vs. {competitor} Laufzeit-Test",
            "Stromversorgung verglichen: Beurer-Vorteile vs. {competitor}",
        ],
    },
    "kundenservice": {
        "advantages": [
            "Deutscher Kundenservice mit persönlicher Beratung",
            "Schnelle Garantieabwicklung & Ersatzteilversorgung",
            "Umfassendes Service-Netzwerk in DACH",
        ],
        "content_ideas": [
            "Service-Vergleich: Beurer-Support vs. {competitor}-Erfahrung",
            "Garantie & Service: Beurer-Vorteile gegenüber {competitor}",
            "Kundenzufriedenheit: Beurer-Service vs. {competitor} im Vergleich",
        ],
    },
}

# Source category map: groups sources for dashboard display
SOURCE_CATEGORY_MAP = {
    "Foren": [
        "reddit", "gutefrage", "fragen.onmeda.de", "diabetes-forum.de",
        "seniorentreff.de", "med1.de", "lifeline.de",
    ],
    "Shops & Bewertungen": [
        "amazon.de", "otto.de", "coolblue.de", "idealo.de",
        "mediamarkt.de", "saturn.de", "expert.de", "docmorris.de", "shop-apotheke.de",
    ],
    "Testberichte & Medien": [
        "chip.de", "testberichte.de", "faz.net", "stern.de",
        "computerbild.de", "techstage.de", "vergleich.org",
        "test.de", "rtl.de", "focus.de", "ndr.de",
    ],
    "Video": ["youtube", "youtube_transcript", "tiktok", "instagram", "twitter"],
    "Gesundheitsportale": [
        "endometriose-vereinigung.de", "rheuma-liga.de",
        "netdoktor.de", "apotheken-umschau.de", "onmeda.de",
    ],
}


RETAILER_LISTING_DOMAINS = {
    "mediamarkt.de", "mediamarkt.at", "saturn.de", "saturn.at", "expert.de",
}

# =============================================================================
# OTHER SUBCATEGORIES (breakdown for items classified as "other")
# =============================================================================
OTHER_SUBCATEGORIES = {
    "general_health": {
        "label_de": "Allgemeine Gesundheit",
        "keywords": ["gesundheit", "krankheit", "symptom", "diagnose", "therapie", "behandlung", "arzt", "klinik", "hospital", "praxis"]
    },
    "wellness_lifestyle": {
        "label_de": "Wellness/Lifestyle",
        "keywords": ["wellness", "fitness", "ernährung", "abnehmen", "yoga", "meditation", "schlaf", "stress", "entspannung", "sport"]
    },
    "medical_professional": {
        "label_de": "Medizinische Fachfragen",
        "keywords": ["medikament", "tabletten", "nebenwirkung", "dosierung", "rezept", "facharzt", "operation", "chirurg"]
    },
    "mental_health": {
        "label_de": "Psychische Gesundheit",
        "keywords": ["depression", "angst", "panik", "burnout", "psychisch", "therapeut", "psycholog"]
    },
    "nutrition_supplements": {
        "label_de": "Ernährung/Nahrungsergänzung",
        "keywords": ["vitamin", "supplement", "nahrungsergänzung", "mineral", "eiweiß", "protein", "diät"]
    },
    "unrelated": {
        "label_de": "Nicht zuordenbar",
        "keywords": []
    }
}


def get_source_category(source: str) -> str:
    """Map a source name to its display category."""
    source_lower = source.lower()
    for category, sources in SOURCE_CATEGORY_MAP.items():
        if any(s in source_lower for s in sources):
            return category
    return "Sonstige"


# =============================================================================
# HEALTH RELEVANCE KEYWORDS (for pre-save noise filtering)
# =============================================================================
# Items whose title+content contain at least one of these keywords pass the filter.
# Covers: blood pressure, pain/TENS, infrared, menstrual, general health devices,
# and all tracked brand names.
HEALTH_RELEVANCE_KEYWORDS = [
    # Blood pressure (German)
    "blutdruck", "bluthochdruck", "hypertonie", "blutdruckmessgerät", "blutdruckmesser",
    "oberarm", "handgelenk", "manschette", "systolisch", "diastolisch", "puls",
    "blutdruckmessung", "blutdruckwerte",
    # Pain / TENS / EMS
    "tens", "ems", "reizstrom", "schmerztherapie", "elektrotherapie",
    "schmerzlinderung", "muskelstimulation", "elektroden", "nervenstimulation",
    # Infrared / heat therapy
    "infrarot", "infrarotlampe", "rotlicht", "wärmelampe", "wärmetherapie",
    "wärmegürtel", "tiefenwärme",
    # Menstrual
    "menstruation", "regelschmerzen", "periode", "periodenschmerzen",
    "unterleibsschmerzen", "menstruationsbeschwerden",
    # General health devices
    "messgerät", "gesundheitsgerät", "medizinprodukt", "therapiegerät",
    "fieberthermometer", "pulsoximeter",
    # Pain categories
    "rückenschmerzen", "nackenschmerzen", "gelenkschmerzen", "arthrose",
    "kopfschmerzen", "migräne", "neuropathie", "nervenschmerzen",
    "schmerzen", "schmerzbehandlung",
    # Beurer brand + products
    "beurer",
    # Competitor brands (items mentioning these are relevant for competitive intel)
    "omron", "withings", "sanitas", "medisana", "braun",
    "auvon", "orthomechanik", "comfytemp", "slimpal", "ghtens",
    "saneotens", "saneo", "saneostore", "axion", "menstruflow",
    # Product model patterns
    "bm 27", "bm 25", "bm 81", "bc 81", "bm 53", "bm 64", "bc 54", "bc 27",
    "bm 54", "bm 59", "bm 96", "bm 58", "bm 77", "bm 85",
    "em 59", "em 89", "em 50", "em 55", "em 49", "em 80",
    "il 50", "il 60",
]
