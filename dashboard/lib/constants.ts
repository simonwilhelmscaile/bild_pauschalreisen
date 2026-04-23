/**
 * Shared constants for TypeScript aggregator — ported from report/constants.py.
 */

// =============================================================================
// PRODUCT CATALOGS
// =============================================================================
export const BEURER_PRODUCT_CATALOG: Record<string, { category: string; priority: number }> = {
  "BM 27": { category: "blood_pressure", priority: 1 },
  "BM 25": { category: "blood_pressure", priority: 1 },
  "BM 81": { category: "blood_pressure", priority: 1 },
  "BC 81": { category: "blood_pressure", priority: 1 },
  "BM 53": { category: "blood_pressure", priority: 2 },
  "BM 64": { category: "blood_pressure", priority: 2 },
  "BC 54": { category: "blood_pressure", priority: 2 },
  "BC 27": { category: "blood_pressure", priority: 2 },
  "BM 54": { category: "blood_pressure", priority: 3 },
  "BM 59": { category: "blood_pressure", priority: 3 },
  "BM 96": { category: "blood_pressure", priority: 3 },
  "BM 58": { category: "blood_pressure", priority: 4 },
  "BM 77": { category: "blood_pressure", priority: 4 },
  "BM 85": { category: "blood_pressure", priority: 4 },
  "EM 59": { category: "pain_tens", priority: 1 },
  "EM 89": { category: "pain_tens", priority: 1 },
  "EM 50": { category: "pain_tens", priority: 2 },
  "EM 55": { category: "pain_tens", priority: 2 },
  "EM 49": { category: "pain_tens", priority: 3 },
  "EM 80": { category: "pain_tens", priority: 3 },
  "IL 50": { category: "infrarot", priority: 1 },
  "IL 60": { category: "infrarot", priority: 1 },
};
export const BEURER_PRODUCTS = Object.keys(BEURER_PRODUCT_CATALOG);

export const COMPETITOR_PRODUCT_CATALOG: Record<string, { category: string; brand: string }> = {
  "Omron M500": { category: "blood_pressure", brand: "Omron" },
  "Omron M400": { category: "blood_pressure", brand: "Omron" },
  "Withings BPM": { category: "blood_pressure", brand: "Withings" },
  "AUVON TENS Gerät": { category: "pain_tens", brand: "AUVON" },
  "Orthomechanik TENS/EMS": { category: "pain_tens", brand: "Orthomechanik" },
  "Comfytemp TENS Gerät": { category: "pain_tens", brand: "Comfytemp" },
  "GHTENS": { category: "pain_tens", brand: "GHTENS" },
  "Comfytemp Wärmegürtel": { category: "infrarot", brand: "Comfytemp" },
  "Slimpal Wärmegürtel": { category: "infrarot", brand: "Slimpal" },
  "Medisana IR 850": { category: "infrarot", brand: "Medisana" },
  "SaneoTENS": { category: "pain_tens", brand: "SaneoTENS" },
  "Axion TENS": { category: "pain_tens", brand: "Axion" },
  "Menstruflow TENS": { category: "menstrual", brand: "Menstruflow" },
};
export const COMPETITOR_PRODUCTS = [...Object.keys(COMPETITOR_PRODUCT_CATALOG), "Omron"];

// Brand → set of categories
export const BRAND_CATEGORY_MAP: Record<string, Set<string>> = {};
for (const [, meta] of Object.entries(COMPETITOR_PRODUCT_CATALOG)) {
  if (!BRAND_CATEGORY_MAP[meta.brand]) BRAND_CATEGORY_MAP[meta.brand] = new Set();
  BRAND_CATEGORY_MAP[meta.brand].add(meta.category);
}
if (!BRAND_CATEGORY_MAP["Omron"]) BRAND_CATEGORY_MAP["Omron"] = new Set();
BRAND_CATEGORY_MAP["Omron"].add("blood_pressure");

// =============================================================================
// KEYWORD PATTERNS
// =============================================================================
export const HEALTH_ONLY_PATTERNS = [
  "sind meine werte normal", "habe ich bluthochdruck", "ist mein blutdruck",
  "was bedeutet", "symptome", "arzt fragen", "zum arzt",
  "ab wie vielen jahren", "wie alt", "für welches alter",
  "macht den bauch", "körper", "muskeln aufbauen",
  "abnehmen", "gewicht", "ernährung",
];

export const PURCHASE_INTENT_PATTERNS = [
  "kaufen", "bestellen", "empfehlen", "empfehlung", "vergleich",
  "preisvergleich", "lohnt sich", "apotheke",
  "welches gerät", "welches modell",
  "wo kaufen", "wo bestellen",
  "online kaufen", "online bestellen",
];

export const TROUBLESHOOTING_PATTERNS = [
  "fehler", "error", "funktioniert nicht", "problem", "defekt", "kaputt",
  "zeigt nicht", "falsch", "ungenau", "batterie", "akku", "reparatur",
  "garantie", "reklamation", "hilfe", "support", "anleitung",
];

export const USAGE_PATTERNS = [
  "wie messe", "richtig messen", "wann messen", "wie oft", "anleitung",
  "bedienung", "verwenden", "benutzen", "einstellen", "kalibrieren",
  "app verbinden", "bluetooth", "speichern", "auswerten",
];

export const DEVICE_KEYWORDS = [
  "messgerät", "gerät", "oberarm", "handgelenk", "manschette",
  "display", "akku", "batterie", "genauigkeit", "fehler",
  "app", "bluetooth", "kaufen", "empfehlen", "tens", "ems",
  "modell", "sensor", "kalibrieren", "anzeige", "speicher",
];

export const BRAND_NAMES = [
  "beurer", "omron", "withings", "sanitas", "medisana", "braun",
  "auvon", "orthomechanik", "comfytemp", "slimpal", "ghtens",
  "saneotens", "saneo", "axion", "menstruflow",
];

// =============================================================================
// GERMAN LABELS
// =============================================================================
export const CATEGORY_LABELS_DE: Record<string, string> = {
  blood_pressure: "Blutdruck",
  pain_tens: "Schmerz/TENS",
  infrarot: "Infrarot/Wärme",
  menstrual: "Menstruation",
  other: "Sonstige",
  unclassified: "Nicht klassifiziert",
  unknown: "Unbekannt",
};

export const JOURNEY_STAGES = [
  "awareness", "consideration", "comparison", "purchase", "advocacy",
] as const;

export const JOURNEY_STAGE_LABELS_DE: Record<string, string> = {
  awareness: "Bewusstsein",
  consideration: "Lösungssuche",
  comparison: "Vergleich",
  purchase: "Kaufentscheidung",
  advocacy: "Erfahrung/Empfehlung",
};

/** Which pain_category values are semantically relevant per item category.
 *  Used to filter cross-category bleed in per-category views. */
export const CATEGORY_PAIN_CATEGORIES: Record<string, string[]> = {
  blood_pressure: ["bluthochdruck"],
  pain_tens: ["ruecken_nacken", "gelenke_arthrose", "kopfschmerzen", "neuropathie", "sonstige_schmerzen"],
  menstrual: ["menstruation"],
  infrarot: ["ruecken_nacken", "gelenke_arthrose", "sonstige_schmerzen"],
};

/** Medication classes to strip per category to avoid cross-category bleed. */
export const CATEGORY_EXCLUDED_MED_CLASSES: Record<string, string[]> = {
  blood_pressure: ["Schmerzmittel", "Entzündungshemmer"],
  pain_tens: ["Blutdruck-Medikamente"],
  menstrual: ["Blutdruck-Medikamente"],
};

export const PAIN_CATEGORY_LABELS_DE: Record<string, string> = {
  ruecken_nacken: "Rücken-/Nackenschmerzen",
  gelenke_arthrose: "Gelenk-/Arthroseschmerzen",
  menstruation: "Menstruationsschmerzen",
  kopfschmerzen: "Kopfschmerzen/Migräne",
  bluthochdruck: "Bluthochdruck/Kreislauf",
  neuropathie: "Neuropathie/Nervenschmerzen",
  sonstige_schmerzen: "Sonstige Schmerzen",
};

export const SOLUTION_LABELS_DE: Record<string, string> = {
  tens_ems: "TENS/EMS-Therapie",
  waermetherapie: "Wärmetherapie/Infrarot",
  blutdruckmessung: "Blutdruckmessung",
  medikamente: "Medikamente",
  physiotherapie: "Physiotherapie",
  hausmittel: "Hausmittel/Naturheilkunde",
  arztbesuch: "Arztbesuch",
  sport_bewegung: "Sport/Bewegung",
  massage: "Massage",
  akupunktur: "Akupunktur",
  sonstiges: "Sonstige",
};

export const HIGH_BEURER_RELEVANCE_SOLUTIONS = [
  "tens_ems", "waermetherapie", "blutdruckmessung",
];

export const COPING_STRATEGY_LABELS_DE: Record<string, string> = {
  ibuprofen: "Ibuprofen / Schmerzmittel",
  paracetamol: "Paracetamol",
  physiotherapie: "Physiotherapie",
  tens_geraet: "TENS-Gerät",
  waermetherapie: "Wärme-/Infrarottherapie",
  yoga: "Yoga / Stretching",
  arztbesuch: "Arztbesuch",
  bp_medikamente: "Blutdruck-Medikamente",
  home_monitoring: "Heim-Monitoring",
  ernaehrung_diaet: "Ernährung / Diät",
  meditation: "Meditation / Achtsamkeit",
  massage: "Massage",
  bewegung_sport: "Bewegung / Sport",
  entspannung: "Entspannung / Stressabbau",
  kaltetherapie: "Kältetherapie",
  osteopathie: "Osteopathie",
  chiropraktik: "Chiropraktik",
  akupunktur: "Akupunktur",
};

export const LIFE_SITUATION_LABELS_DE: Record<string, string> = {
  schwangerschaft: "Schwangerschaft",
  buero_arbeit: "Büro-/Schreibtischarbeit",
  sport_aktiv: "Sport / Aktiver Lebensstil",
  senioren: "Senioren / Ältere Erwachsene",
  eltern_baby: "Eltern / Babypflege",
  pendler: "Pendler / Unterwegs",
  schichtarbeit: "Schichtarbeit",
  homeoffice: "Homeoffice",
  pflegende_angehoerige: "Pflegende Angehörige",
  studenten: "Studenten",
  chronisch_krank: "Chronisch Erkrankte",
  post_op: "Post-OP / Rehabilitation",
  uebergewicht: "Übergewicht / Adipositas",
  stress_burnout: "Stress / Burnout",
  reisende: "Reisende",
  frisch_diagnostiziert: "Frisch diagnostiziert",
  medikamenten_nebenwirkungen_sucher: "Medikamenten-Nebenwirkungen",
  fitness_ems: "Fitness / EMS-Training",
  migraene_patient: "Migräne-Patient",
  fibromyalgie_patient: "Fibromyalgie-Patient",
  endometriose: "Endometriose",
};

// User segments (WHO the person is) — split from life_situation
export const USER_SEGMENTS = [
  "schwangerschaft", "buero_arbeit", "sport_aktiv", "senioren",
  "eltern_baby", "pendler", "schichtarbeit", "homeoffice",
  "pflegende_angehoerige", "studenten", "reisende", "fitness_ems",
];
export const USER_SEGMENT_LABELS_DE: Record<string, string> = {
  schwangerschaft: "Schwangerschaft",
  buero_arbeit: "Büro-/Schreibtischarbeit",
  sport_aktiv: "Sport / Aktiver Lebensstil",
  senioren: "Senioren / Ältere Erwachsene",
  eltern_baby: "Eltern / Babypflege",
  pendler: "Pendler / Unterwegs",
  schichtarbeit: "Schichtarbeit",
  homeoffice: "Homeoffice",
  pflegende_angehoerige: "Pflegende Angehörige",
  studenten: "Studenten",
  reisende: "Reisende",
  fitness_ems: "Fitness / EMS-Training",
};
export const USER_SEGMENT_LABELS_EN: Record<string, string> = {
  schwangerschaft: "Pregnancy",
  buero_arbeit: "Office/Desk Work",
  sport_aktiv: "Sports / Active Lifestyle",
  senioren: "Seniors / Older Adults",
  eltern_baby: "Parents / Baby Care",
  pendler: "Commuters / On-the-go",
  schichtarbeit: "Shift Work",
  homeoffice: "Home Office",
  pflegende_angehoerige: "Family Caregivers",
  studenten: "Students",
  reisende: "Travelers",
  fitness_ems: "Fitness / EMS Training",
};

// Problem categories (WHAT condition they have) — split from life_situation
export const PROBLEM_CATEGORIES_LIST = [
  "chronisch_krank", "post_op", "uebergewicht", "stress_burnout",
  "frisch_diagnostiziert", "medikamenten_nebenwirkungen_sucher",
  "migraene_patient", "fibromyalgie_patient", "endometriose",
];
export const PROBLEM_CATEGORY_LABELS_DE: Record<string, string> = {
  chronisch_krank: "Chronisch Erkrankte",
  post_op: "Post-OP / Rehabilitation",
  uebergewicht: "Übergewicht / Adipositas",
  stress_burnout: "Stress / Burnout",
  frisch_diagnostiziert: "Frisch diagnostiziert",
  medikamenten_nebenwirkungen_sucher: "Medikamenten-Nebenwirkungen",
  migraene_patient: "Migräne-Patient",
  fibromyalgie_patient: "Fibromyalgie-Patient",
  endometriose: "Endometriose",
};
export const PROBLEM_CATEGORY_LABELS_EN: Record<string, string> = {
  chronisch_krank: "Chronically Ill",
  post_op: "Post-Surgery / Rehabilitation",
  uebergewicht: "Overweight / Obesity",
  stress_burnout: "Stress / Burnout",
  frisch_diagnostiziert: "Newly Diagnosed",
  medikamenten_nebenwirkungen_sucher: "Medication Side Effects",
  migraene_patient: "Migraine Patient",
  fibromyalgie_patient: "Fibromyalgia Patient",
  endometriose: "Endometriosis",
};

export const FRUSTRATION_LABELS_DE: Record<string, string> = {
  keine_besserung: "Keine Besserung trotz Therapie",
  nebenwirkungen_medikamente: "Nebenwirkungen von Medikamenten",
  zu_teuer: "Zu teuer / Kosten",
  keine_langzeitwirkung: "Keine Langzeitwirkung",
  unangenehme_anwendung: "Unangenehme Anwendung",
  widerspruechliche_infos: "Widersprüchliche Informationen",
  arzt_nimmt_nicht_ernst: "Arzt nimmt nicht ernst",
  wartezeit_arzt: "Wartezeit beim Arzt",
  geraet_kompliziert: "Gerät zu kompliziert",
  manschette_problem: "Manschetten-Problem",
  app_verbindung: "App-/Verbindungsprobleme",
  messungenauigkeit: "Mess-Ungenauigkeit",
};

export const PAIN_LOCATION_LABELS_DE: Record<string, string> = {
  ruecken_oberer: "Oberer Rücken",
  ruecken_unterer: "Unterer Rücken / LWS",
  nacken: "Nacken / HWS",
  schulter: "Schulter",
  knie: "Knie",
  huelte: "Hüfte",
  handgelenk: "Handgelenk",
  ellbogen: "Ellbogen",
  fuss: "Fuß / Sprunggelenk",
  unterleib: "Unterleib / Becken",
  ganzer_koerper: "Ganzer Körper / Diffus",
  kopf_migraene: "Kopf / Migräne",
  nerven_ischias: "Nerven / Ischias",
  gelenke_allgemein: "Gelenke (allgemein)",
  muskelverspannung: "Muskelverspannung",
  fibromyalgie: "Fibromyalgie",
};

export const PAIN_SEVERITY_LABELS_DE: Record<string, string> = {
  leicht: "Leicht",
  mittel: "Mittel",
  stark: "Stark",
  chronisch: "Chronisch",
  akut: "Akut",
};

export const PAIN_DURATION_LABELS_DE: Record<string, string> = {
  akut_tage: "Akut (Tage)",
  wochen: "Wochen",
  monate: "Monate",
  jahre_chronisch: "Jahre / Chronisch",
  episodisch: "Episodisch (wiederkehrend)",
};

export const BP_CONCERN_LABELS_DE: Record<string, string> = {
  messgenauigkeit: "Messgenauigkeit",
  schwankende_werte: "Schwankende Werte",
  weisser_kittel: "Weißkittel-Hypertonie",
  medikamenten_kontrolle: "Medikamenten-Kontrolle",
  morgen_abend_unterschied: "Morgen-/Abend-Unterschied",
  arm_unterschied: "Links-/Rechts-Arm-Unterschied",
  geraete_vergleich: "Geräte-Vergleich (Arzt vs. Zuhause)",
  normwerte_frage: "Normwerte-Frage",
  hypertonie_angst: "Hypertonie-Angst",
  monitoring_routine: "Monitoring-Routine",
};

export const BP_SEVERITY_LABELS_DE: Record<string, string> = {
  optimal: "Optimal (<120/80)",
  normal: "Normal (120-129/80-84)",
  hoch_normal: "Hoch-Normal (130-139/85-89)",
  hypertonie_1: "Hypertonie Grad 1 (140-159/90-99)",
  hypertonie_2: "Hypertonie Grad 2+ (≥160/≥100)",
  unspecified: "Unspezifiziert (BP erwähnt, kein Wert)",
};

export const NEGATIVE_ROOT_CAUSE_LABELS_DE: Record<string, string> = {
  produkt_defekt: "Produkt-Defekt / Hardware",
  fehlbedienung: "Fehlbedienung / Anwenderfehler",
  falsche_erwartung: "Falsche Erwartung",
  kompatibilitaet: "Kompatibilitäts-Problem",
  service_mangel: "Service-Mangel",
  preis_leistung: "Preis-Leistung",
  design_ergonomie: "Design / Ergonomie",
};

export const EMOTION_LABELS_DE: Record<string, string> = {
  frustration: "Frustration",
  relief: "Erleichterung",
  anxiety: "Angst/Sorge",
  satisfaction: "Zufriedenheit",
  confusion: "Verwirrung",
  anger: "Ärger/Wut",
  hope: "Hoffnung",
  resignation: "Resignation",
};

export const INTENT_LABELS_DE: Record<string, string> = {
  purchase_question: "Kaufberatung",
  troubleshooting: "Fehlerbehebung",
  experience_sharing: "Erfahrungsbericht",
  recommendation_request: "Empfehlungsanfrage",
  comparison: "Vergleich",
  general_question: "Allgemeine Frage",
  complaint: "Beschwerde",
  advocacy: "Empfehlung/Lob",
};

export const ASPECT_CATEGORIES = [
  "messgenauigkeit", "bedienbarkeit", "verarbeitung",
  "preis_leistung", "app_konnektivitaet", "manschette_elektroden",
  "display_anzeige", "schmerzlinderung", "akku_batterie", "kundenservice",
];

export const ASPECT_LABELS_DE: Record<string, string> = {
  messgenauigkeit: "Messgenauigkeit",
  bedienbarkeit: "Bedienbarkeit",
  verarbeitung: "Verarbeitung/Qualität",
  preis_leistung: "Preis-Leistung",
  app_konnektivitaet: "App/Konnektivität",
  manschette_elektroden: "Manschette/Elektroden",
  display_anzeige: "Display/Anzeige",
  schmerzlinderung: "Schmerzlinderung",
  akku_batterie: "Akku/Batterie",
  kundenservice: "Kundenservice",
};

// =============================================================================
// SENTIMENT CAUSES (9 categories, first-match-wins)
// =============================================================================
export const SENTIMENT_CAUSES: Record<string, {
  label_de: string;
  keywords: string[];
  action_default: string;
  is_actionable: boolean;
}> = {
  geraete_fehler: {
    label_de: "Geräte-Fehler",
    keywords: ["defekt", "kaputt", "funktioniert nicht", "fehler", "broken", "geht nicht",
      "ausgefallen", "stürzt ab", "startet nicht", "schaltet sich ab", "reagiert nicht",
      "display defekt", "fehlermeldung", "error", "eingeschickt", "garantiefall",
      "ersatzgerät", "hält nicht lange", "lebensdauer", "geht nicht mehr",
      "funktioniert nicht mehr", "abgebrochen", "ausfall"],
    action_default: "QA/Support informieren, Fehler dokumentieren",
    is_actionable: true,
  },
  messgenauigkeit: {
    label_de: "Messgenauigkeit",
    keywords: ["ungenau", "falsche werte", "messwerte stimmen nicht", "abweichung", "schwankt",
      "arzt misst anders", "beim arzt anders", "weicht ab", "messfehler", "misst falsch",
      "misst zu hoch", "misst zu niedrig", "unzuverlässig", "kalibrieren", "genauigkeit",
      "messungenauigkeit", "unterschiedliche werte", "werte stimmen nicht",
      "ergebnis stimmt nicht", "nicht genau", "falsch gemessen"],
    action_default: "Produktteam informieren, FAQ zu korrekter Messung erstellen",
    is_actionable: true,
  },
  komfort_anwendung: {
    label_de: "Komfort/Anwendung",
    keywords: ["kompliziert", "verwirrend", "anleitung", "schwierig", "umständlich",
      "nicht intuitiv", "unbequem", "drückt", "manschette zu eng", "manschette rutscht",
      "unangenehm", "zu laut", "display schlecht lesbar", "schrift zu klein",
      "handhabung", "bedienung", "zu groß", "zu schwer", "unpraktisch",
      "schlecht ablesbar", "schwer zu bedienen"],
    action_default: "UX-Feedback an Produktmanagement, Tutorial-Content erstellen",
    is_actionable: true,
  },
  app_konnektivitaet: {
    label_de: "App/Konnektivität",
    keywords: ["bluetooth", " app ", "verbindung", "koppeln", "pairing", "synchronisieren", "sync ",
      "daten übertragen", "app stürzt", "verbindet sich nicht", "healthmanager",
      "health manager", "beurer app", "wlan", "datenübertragung", "kompatibel",
      "app funktioniert", "keine verbindung", "kopplung", "übertragung",
      "smartphone", "handy verbinden", "die app", "der app", "eine app"],
    action_default: "App-Team informieren, Kompatibilitätsliste prüfen",
    is_actionable: true,
  },
  preis_wert: {
    label_de: "Preis/Wert",
    keywords: ["teuer", "preis", "kosten", "zu viel", "billiger", "günstig", "preis-leistung",
      "nicht wert", "überteuert", "lohnt sich nicht", "für den preis", "zu teuer",
      "preislich", "geld", "investition", "preisvergleich"],
    action_default: "Preispositionierung beobachten, Mehrwert-Kommunikation stärken",
    is_actionable: true,
  },
  service_support: {
    label_de: "Service/Support",
    keywords: ["support", "kundenservice", "antwort", "garantie", "reparatur", "hotline",
      "erreichbar", "reaktionszeit", "wartezeit", "keine antwort", "unfreundlich",
      "reklamation", "beschwerde", "rücksendung", "erstattung", "service",
      "kundendienst", "kontakt", "nicht erreichbar", "lange warten"],
    action_default: "Service-Team informieren, Prozesse überprüfen",
    is_actionable: true,
  },
  gesundheitsfrage: {
    label_de: "Gesundheitsfrage",
    keywords: ["sind meine werte normal", "habe ich bluthochdruck", "symptome", "arzt fragen",
      "zum arzt", "diagnose", "angst ", "sorge ", "medikament", "tabletten",
      "nebenwirkung", "therapie", "normwerte", "grenzwerte", "hypertonie",
      "bluthochdruck", "schmerzen", "krankheit", "behandlung", "gesundheit",
      "beim arzt", "mein arzt", "zum arzt", "krank ", "meine werte"],
    action_default: "Kein direkter Handlungsbedarf (Gesundheitsthema)",
    is_actionable: false,
  },
  wettbewerber_bezogen: {
    label_de: "Wettbewerber-bezogen",
    keywords: ["omron", "withings", "sanitas", "medisana", "braun", "boso", "aponorm",
      "auvon", "orthomechanik", "comfytemp", "slimpal", "ghtens",
      "saneotens", "saneo", "saneostore", "axion", "menstruflow",
      "andere marke", "konkurrenz", "wettbewerber"],
    action_default: "Kein direkter Handlungsbedarf (Wettbewerber-Feedback)",
    is_actionable: false,
  },
  sonstiges: {
    label_de: "Sonstiges",
    keywords: [],
    action_default: "Manuell prüfen",
    is_actionable: false,
  },
};

export const COMPETITOR_BRANDS: Record<string, string> = {
  omron: "Omron", withings: "Withings", sanitas: "Sanitas", medisana: "Medisana",
  braun: "Braun", auvon: "AUVON", orthomechanik: "Orthomechanik",
  comfytemp: "Comfytemp", slimpal: "Slimpal", ghtens: "GHTENS",
  saneotens: "SaneoTENS", saneo: "SaneoTENS", saneostore: "SaneoTENS",
  axion: "Axion", menstruflow: "Menstruflow",
};

// =============================================================================
// KEY ACTIONS CONSTANTS
// =============================================================================
export const PRIORITY_LEVELS: Record<string, { label_de: string; color: string; deadline: string }> = {
  urgent: { label_de: "DRINGEND", color: "#FF3B30", deadline: "Sofort" },
  high: { label_de: "HOCH", color: "#FF9500", deadline: "Diese Woche" },
  normal: { label_de: "NORMAL", color: "#34C759", deadline: "Nächste Woche" },
};

export const RESPONSIBLE_PARTIES: Record<string, string> = {
  support: "Support", content: "Content", marketing: "Marketing", qa: "QA", product: "Produkt",
};

// =============================================================================
// SOURCE CATEGORY MAP
// =============================================================================
export const SOURCE_CATEGORY_MAP: Record<string, string[]> = {
  Foren: ["reddit", "gutefrage", "fragen.onmeda.de", "diabetes-forum.de", "seniorentreff.de", "med1.de", "lifeline.de"],
  "Shops & Bewertungen": ["amazon.de", "otto.de", "coolblue.de", "idealo.de", "mediamarkt.de", "saturn.de", "expert.de", "docmorris.de", "shop-apotheke.de"],
  "Testberichte & Medien": ["chip.de", "testberichte.de", "faz.net", "stern.de", "computerbild.de", "techstage.de", "vergleich.org", "test.de", "rtl.de", "focus.de", "ndr.de"],
  Video: ["youtube", "youtube_transcript", "tiktok", "instagram", "twitter"],
  Gesundheitsportale: ["endometriose-vereinigung.de", "rheuma-liga.de", "netdoktor.de", "apotheken-umschau.de", "onmeda.de"],
};

export const RETAILER_LISTING_DOMAINS = new Set([
  "mediamarkt.de", "mediamarkt.at", "saturn.de", "saturn.at", "expert.de",
]);

export function getSourceCategory(source: string): string {
  const lower = source.toLowerCase();
  for (const [category, sources] of Object.entries(SOURCE_CATEGORY_MAP)) {
    if (sources.some(s => lower.includes(s))) return category;
  }
  return "Sonstige";
}

// =============================================================================
// BRIDGE MOMENT TYPES (from stored field)
// =============================================================================
export const BRIDGE_MOMENT_TYPES: Record<string, string> = {
  schmerz_loest_arztbesuch_aus: "Schmerz löst Arztbesuch aus",
  medikament_loest_alternativsuche_aus: "Medikament löst Alternativsuche aus",
  arzt_empfiehlt_geraet: "Arzt empfiehlt Gerät",
  freund_empfiehlt_produkt: "Freund/Familie empfiehlt Produkt",
  online_recherche_loest_kauf_aus: "Online-Recherche löst Kauf aus",
  testbericht_weckt_interesse: "Testbericht weckt Interesse",
  diagnose_loest_monitoring_aus: "Diagnose löst Monitoring aus",
  vergleich_loest_entscheidung_aus: "Vergleich löst Entscheidung aus",
  none_identified: "Kein Bridge-Moment identifiziert",
};

// =============================================================================
// BRIDGE PATTERNS (content-based detection)
// =============================================================================
export const BRIDGE_PATTERNS: Record<string, {
  label_de: string; label_en: string;
  flow_de?: string; flow_en?: string;
  keywords: string[]; keywords_en?: string[];
  coping_signal?: string[];
  stages?: string[];
  categories?: string[];
}> = {
  medication_to_alternative: {
    label_de: "Medikament → Alternative",
    label_en: "Medication → Alternative",
    flow_de: "Medikament versagt → Alternative",
    flow_en: "Medication fails → Alternative",
    keywords: ["nebenwirkung", "abgesetzt", "statt medikament", "ohne medikament",
      "medikamentenfrei", "nicht geholfen", "hilft nicht"],
    keywords_en: ["side effect", "stopped taking", "instead of medication",
      "without medication", "medication free", "didn't help", "does not help", "doesn't work", "off medication"],
    coping_signal: ["tens_geraet", "waermetherapie", "yoga", "massage", "bewegung_sport"],
  },
  pain_triggers_research: {
    label_de: "Schmerz → Lösungssuche",
    label_en: "Pain → Solution Search",
    flow_de: "Schmerz → Lösungssuche",
    flow_en: "Pain → Solution search",
    keywords: ["was hilft", "was kann ich", "was tun", "empfehlung",
      "erfahrung", "hat jemand", "kennt jemand", "tipps"],
    keywords_en: ["what helps", "what can i do", "any recommendation",
      "any experience", "has anyone", "does anyone know", "any tips", "any advice", "looking for help"],
    stages: ["awareness", "consideration"],
  },
  doctor_recommends_device: {
    label_de: "Arzt empfiehlt → Gerätekauf",
    label_en: "Doctor Recommends → Device Purchase",
    flow_de: "Arzt empfiehlt Gerät → Kauf",
    flow_en: "Doctor recommends device → Purchase",
    keywords: ["arzt empfohlen", "arzt empfiehlt", "arzt geraten", "arzt riet",
      "arzt meinte", "verschrieben", "rezept", "verordnet"],
    keywords_en: ["doctor recommended", "doctor suggested", "doctor told me",
      "doctor advised", "prescribed", "physician recommended",
      "my doctor said", "pt recommended", "physio recommended"],
  },
  failed_therapy_triggers_switch: {
    label_de: "Therapie versagt → Wechsel",
    label_en: "Failed Therapy → Switch",
    flow_de: "Therapie versagt → Wechsel",
    flow_en: "Therapy fails → Switch",
    keywords: ["nicht geholfen", "hilft nicht", "keine besserung", "reicht nicht",
      "bringt nichts", "wirkungslos", "erfolglos", "umgestiegen", "gewechselt"],
    keywords_en: ["didn't help", "not helping", "no improvement", "not enough",
      "doesn't work", "ineffective", "no relief", "switched to", "gave up on", "stopped working"],
  },
  research_triggers_purchase: {
    label_de: "Recherche → Kaufentscheidung",
    label_en: "Research → Purchase Decision",
    flow_de: "Testbericht → Kaufinteresse",
    flow_en: "Test report → Purchase interest",
    keywords: ["dann gekauft", "bestellt", "ausprobiert", "probiert", "zugelegt",
      "angeschafft", "lohnt sich", "welches gerät"],
    keywords_en: ["then bought", "ordered", "tried it", "gave it a try",
      "picked up", "purchased", "worth it", "which device", "ended up buying", "decided to get"],
    stages: ["comparison", "purchase"],
  },
  diagnosis_triggers_monitoring: {
    label_de: "Diagnose → Heim-Monitoring",
    label_en: "Diagnosis → Home Monitoring",
    flow_de: "Diagnose → Heim-Monitoring",
    flow_en: "Diagnosis → Home monitoring",
    keywords: ["diagnose", "festgestellt", "diagnostiziert", "bluthochdruck bekommen",
      "zu hause messen", "selbst messen", "regelmäßig messen"],
    keywords_en: ["diagnosed", "found out i have", "told i have",
      "monitor at home", "home monitoring", "check at home", "measure regularly", "track my blood pressure"],
    coping_signal: ["home_monitoring", "bp_medikamente"],
    categories: ["blood_pressure"],
  },
};

export const QA_BRIDGE_OVERRIDES: Record<string, { keywords: string[]; keywords_en: string[] }> = {
  pain_triggers_research: {
    keywords: [
      "welches gerät", "gerät empfehlung", "tens empfehlung",
      "blutdruckmessgerät empfehlung", "welche erfahrung mit",
      "hat jemand erfahrung mit", "kennt jemand ein gerät",
      "gerät empfohlen", "gerät empfehlen",
    ],
    keywords_en: [
      "which device", "device recommendation", "tens recommendation",
      "tens unit recommendation", "blood pressure monitor recommendation",
      "anyone experience with", "has anyone tried", "anyone recommend a device",
      "recommend a tens", "recommend a monitor", "looking for a device",
    ],
  },
};

// =============================================================================
// MEDICATION CLASSES
// =============================================================================
export const MEDICATION_CLASSES: Record<string, string[]> = {
  Schmerzmittel: ["ibuprofen", "paracetamol", "aspirin", "diclofenac", "naproxen",
    "novalgin", "tramadol", "tilidin", "voltaren", "novaminsulfon"],
  "Blutdruck-Medikamente": ["ramipril", "metoprolol", "amlodipin", "candesartan",
    "valsartan", "bisoprolol", "lisinopril", "enalapril", "hct", "ace-hemmer", "betablocker", "sartan"],
  "Entzündungshemmer": ["cortison", "prednisolon", "mtx", "methotrexat",
    "biologikum", "biologika", "sulfasalazin"],
  Naturheilmittel: ["cbd", "magnesium", "baldrian", "johanniskraut",
    "kurkuma", "ingwer", "teufelskralle"],
};

export const GENERIC_MEDICATION_TERMS = new Set([
  "Medikamente", "Schmerzmittel", "Blutdruck-Medikament", "Tabletten",
  "Medikament", "Schmerztabletten", "Blutdrucktabletten", "Medikation",
]);

// =============================================================================
// BEURER DOMAINS (excluded from reports)
// =============================================================================
export const BEURER_DOMAINS = new Set([
  "beurer.com", "www.beurer.com", "beurer.de", "www.beurer.de",
]);

export const REPORT_RELEVANCE_FLOOR = 0.3;

// =============================================================================
// OTHER SUBCATEGORIES (for breaking down "other" category)
// =============================================================================
export const OTHER_SUBCATEGORIES: Record<string, { label_de: string; keywords: string[] }> = {
  general_health: {
    label_de: "Allgemeine Gesundheit",
    keywords: ["gesundheit", "krankheit", "symptom", "diagnose", "therapie", "behandlung", "arzt", "klinik", "hospital", "praxis"],
  },
  wellness_lifestyle: {
    label_de: "Wellness/Lifestyle",
    keywords: ["wellness", "fitness", "ernährung", "abnehmen", "yoga", "meditation", "schlaf", "stress", "entspannung", "sport"],
  },
  medical_professional: {
    label_de: "Medizinische Fachfragen",
    keywords: ["medikament", "tabletten", "nebenwirkung", "dosierung", "rezept", "facharzt", "operation", "chirurg"],
  },
  mental_health: {
    label_de: "Psychische Gesundheit",
    keywords: ["depression", "angst", "panik", "burnout", "psychisch", "therapeut", "psycholog"],
  },
  nutrition_supplements: {
    label_de: "Ernährung/Nahrungsergänzung",
    keywords: ["vitamin", "supplement", "nahrungsergänzung", "mineral", "eiweiß", "protein", "diät"],
  },
  unrelated: {
    label_de: "Nicht zuordenbar",
    keywords: [],
  },
};

// =============================================================================
// ALERT & OPPORTUNITY SCORING WEIGHTS
// =============================================================================

/** Emotion severity weights for alert scoring (0-1 scale) */
export const EMOTION_WEIGHTS: Record<string, number> = {
  anger: 1.0, frustration: 0.8, resignation: 0.6,
  anxiety: 0.5, confusion: 0.4,
  hope: 0.1, satisfaction: 0.0, relief: 0.0,
};

/** Intent multipliers for alert priority */
export const INTENT_ALERT_MULTIPLIERS: Record<string, number> = {
  complaint: 1.5, troubleshooting: 1.3,
  purchase_question: 0.8, recommendation_request: 0.7,
  comparison: 0.6, experience_sharing: 0.5,
  general_question: 0.4, advocacy: 0.3,
};

/** Intent weights for content opportunity relevance (0-1) */
export const INTENT_OPP_WEIGHTS: Record<string, number> = {
  purchase_question: 1.0, recommendation_request: 0.9,
  general_question: 0.7, troubleshooting: 0.6, comparison: 0.5,
};

// =============================================================================
// MEDIA VISIBILITY (Peec AI)
// =============================================================================
export const DOMAIN_TYPE_COLORS: Record<string, string> = {
  Editorial: '#C60050',
  Corporate: '#4A90D9',
  Reference: '#34C759',
  UGC: '#FF9500',
  Institutional: '#8E8E93',
  Competitor: '#FF3B30',
  Other: '#C7C7CC',
};

export const VISIBILITY_BRAND_COLORS: Record<string, string> = {
  Beurer: '#C60050',
  Omron: '#4A90D9',
  Withings: '#34C759',
  Medisana: '#FF9500',
  Braun: '#8E8E93',
};

/** Map LLM bridge_moment DB values → BRIDGE_PATTERNS keys */
export const STORED_BRIDGE_TO_PATTERN: Record<string, string> = {
  schmerz_loest_arztbesuch_aus: "pain_triggers_research",
  medikament_loest_alternativsuche_aus: "medication_to_alternative",
  arzt_empfiehlt_geraet: "doctor_recommends_device",
  freund_empfiehlt_produkt: "research_triggers_purchase",
  online_recherche_loest_kauf_aus: "research_triggers_purchase",
  testbericht_weckt_interesse: "research_triggers_purchase",
  diagnose_loest_monitoring_aus: "diagnosis_triggers_monitoring",
  vergleich_loest_entscheidung_aus: "research_triggers_purchase",
  therapie_versagt_loest_wechsel_aus: "failed_therapy_triggers_switch",
};

// =============================================================================
// KEYWORD → ASPECT KEY mapping (normalizes raw German keywords to aspect keys)
// =============================================================================
export const KEYWORD_TO_ASPECT: Record<string, string> = {
  // messgenauigkeit
  ungenau: "messgenauigkeit", "falsche werte": "messgenauigkeit",
  messwerte: "messgenauigkeit", abweichung: "messgenauigkeit",
  messgenauigkeit: "messgenauigkeit", genauigkeit: "messgenauigkeit",
  kalibrieren: "messgenauigkeit", messfehler: "messgenauigkeit",
  // bedienbarkeit
  kompliziert: "bedienbarkeit", "umständlich": "bedienbarkeit",
  bedienung: "bedienbarkeit", anleitung: "bedienbarkeit",
  bedienbarkeit: "bedienbarkeit", schwierig: "bedienbarkeit",
  // verarbeitung
  verarbeitung: "verarbeitung", "qualität": "verarbeitung",
  defekt: "verarbeitung", kaputt: "verarbeitung",
  billig: "verarbeitung", plastik: "verarbeitung",
  // preis_leistung
  teuer: "preis_leistung", preis: "preis_leistung",
  kosten: "preis_leistung", "preis-leistung": "preis_leistung",
  "günstig": "preis_leistung", "überteuert": "preis_leistung",
  // app_konnektivitaet
  app: "app_konnektivitaet", bluetooth: "app_konnektivitaet",
  verbindung: "app_konnektivitaet", koppeln: "app_konnektivitaet",
  sync: "app_konnektivitaet", "konnektivität": "app_konnektivitaet",
  // manschette_elektroden
  manschette: "manschette_elektroden", elektroden: "manschette_elektroden",
  "drückt": "manschette_elektroden", rutscht: "manschette_elektroden",
  unbequem: "manschette_elektroden", pad: "manschette_elektroden",
  // display_anzeige
  display: "display_anzeige", anzeige: "display_anzeige",
  ablesbar: "display_anzeige", schrift: "display_anzeige",
  bildschirm: "display_anzeige",
  // schmerzlinderung
  schmerzlinderung: "schmerzlinderung", wirkung: "schmerzlinderung",
  "hilft nicht": "schmerzlinderung", "keine besserung": "schmerzlinderung",
  wirkungslos: "schmerzlinderung", linderung: "schmerzlinderung",
  // akku_batterie
  batterie: "akku_batterie", akku: "akku_batterie",
  laufzeit: "akku_batterie", laden: "akku_batterie",
  // kundenservice
  kundenservice: "kundenservice", support: "kundenservice",
  garantie: "kundenservice", reklamation: "kundenservice",
  hotline: "kundenservice", service: "kundenservice",
};

// =============================================================================
// ASPECT → ADVANTAGE MAP (3 variants each for dedup across competitors)
// =============================================================================
export const ASPECT_ADVANTAGE_MAP: Record<string, {
  advantages: string[];
  content_ideas: string[];
}> = {
  messgenauigkeit: {
    advantages: [
      "Klinisch validierte Messgenauigkeit",
      "WHO-konforme Messtechnologie",
      "Arzt-Referenzgenauigkeit für Zuhause",
    ],
    content_ideas: [
      "Genauigkeitsvergleich: Beurer vs. {competitor} — Faktencheck",
      "Warum Messgenauigkeit entscheidend ist — Beurer-Vorteil zeigen",
      "Klinische Validierung erklärt: So schneidet Beurer ab vs. {competitor}",
    ],
  },
  bedienbarkeit: {
    advantages: [
      "Intuitive Ein-Knopf-Bedienung",
      "Benutzerfreundliches Design für alle Altersgruppen",
      "Einfachste Inbetriebnahme am Markt",
    ],
    content_ideas: [
      "Bedienungsvergleich: Beurer vs. {competitor} im Alltagstest",
      "So einfach geht Messen — Beurer-Bedienbarkeit im Fokus",
      "Senioren-freundlich: Warum Beurer einfacher ist als {competitor}",
    ],
  },
  verarbeitung: {
    advantages: [
      "Deutsche Qualitätsstandards in der Verarbeitung",
      "Langlebige Materialien & robustes Design",
      "100 Jahre Beurer Qualitätstradition",
    ],
    content_ideas: [
      "Qualitätsvergleich: Beurer-Verarbeitung vs. {competitor}",
      "Langlebigkeit im Test — warum Beurer länger hält als {competitor}",
      "Made with German engineering: Beurer-Qualität im Detail",
    ],
  },
  preis_leistung: {
    advantages: [
      "Besseres Preis-Leistungs-Verhältnis",
      "Mehr Funktionen zum gleichen Preis",
      "Langfristiger Wert durch Qualität & Service",
    ],
    content_ideas: [
      "Preis-Leistungs-Vergleich: Beurer vs. {competitor}",
      "Was bekommt man für sein Geld? Beurer vs. {competitor} im Detail",
      "Gesamtkosten-Rechnung: Warum Beurer günstiger ist als {competitor}",
    ],
  },
  app_konnektivitaet: {
    advantages: [
      "Beurer HealthManager Pro App-Ökosystem",
      "Nahtlose Bluetooth-Kopplung & Datenexport",
      "Umfassende Gesundheitsdaten-Plattform",
    ],
    content_ideas: [
      "App-Vergleich: Beurer HealthManager vs. {competitor}-App",
      "Konnektivität im Test — Beurer vs. {competitor} Bluetooth-Erfahrung",
      "Datenmanagement leicht gemacht: Beurer-App-Vorteile vs. {competitor}",
    ],
  },
  manschette_elektroden: {
    advantages: [
      "Ergonomische Universalmanschette für jeden Armumfang",
      "Hautfreundliche Elektroden mit optimaler Haftung",
      "Komfort-optimiertes Zubehör-Design",
    ],
    content_ideas: [
      "Manschetten-Vergleich: Beurer-Komfort vs. {competitor}",
      "Elektroden-Qualität im Test — Beurer vs. {competitor}",
      "Tragekomfort entscheidet: Beurer-Zubehör-Vorteile vs. {competitor}",
    ],
  },
  display_anzeige: {
    advantages: [
      "XL-Display mit optimaler Ablesbarkeit",
      "Beleuchtetes Display für jede Lichtsituation",
      "Klare Anzeige mit Ampel-Farbsystem",
    ],
    content_ideas: [
      "Display-Vergleich: Beurer vs. {competitor} Ablesbarkeit",
      "Lesbarkeit im Alltag — Beurer-Display vs. {competitor}",
      "Werte auf einen Blick: Beurer-Anzeige-Vorteile vs. {competitor}",
    ],
  },
  schmerzlinderung: {
    advantages: [
      "Klinisch erprobte TENS-Programme für gezielte Schmerzlinderung",
      "Breites Therapiespektrum mit individuellen Programmen",
      "Medizinprodukt-zertifizierte Schmerztherapie",
    ],
    content_ideas: [
      "Wirksamkeitsvergleich: Beurer-TENS vs. {competitor} Schmerzlinderung",
      "Therapie-Programme im Test — Beurer vs. {competitor}",
      "Effektive Schmerzlinderung: Warum Beurer wirksamer ist als {competitor}",
    ],
  },
  akku_batterie: {
    advantages: [
      "Langlebige Batterie / USB-C Laden",
      "Energieeffizientes Design für lange Nutzungsdauer",
      "Flexible Stromversorgung (Akku + Batterie)",
    ],
    content_ideas: [
      "Akkulaufzeit-Vergleich: Beurer vs. {competitor}",
      "Batterie im Alltag — Beurer vs. {competitor} Laufzeit-Test",
      "Stromversorgung verglichen: Beurer-Vorteile vs. {competitor}",
    ],
  },
  kundenservice: {
    advantages: [
      "Deutscher Kundenservice mit persönlicher Beratung",
      "Schnelle Garantieabwicklung & Ersatzteilversorgung",
      "Umfassendes Service-Netzwerk in DACH",
    ],
    content_ideas: [
      "Service-Vergleich: Beurer-Support vs. {competitor}-Erfahrung",
      "Garantie & Service: Beurer-Vorteile gegenüber {competitor}",
      "Kundenzufriedenheit: Beurer-Service vs. {competitor} im Vergleich",
    ],
  },
};
