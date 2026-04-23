"""Deep insights classification — pain details, coping, aspects, entity sentiment."""
import json
import logging
import time
from typing import Any, Dict, List

from services.gemini import get_classification_model
from report.constants import (
    PAIN_LOCATIONS, PAIN_SEVERITIES, PAIN_DURATIONS,
    BP_CONCERN_TYPES, BP_SEVERITIES, LIFE_SITUATIONS,
    USER_SEGMENTS, PROBLEM_CATEGORIES_LIST,
    SOLUTION_FRUSTRATIONS, NEGATIVE_ROOT_CAUSES, COPING_STRATEGIES,
    BRIDGE_MOMENT_TYPES, ASPECT_CATEGORIES,
)

logger = logging.getLogger(__name__)

_valid_pain_locations = PAIN_LOCATIONS
_valid_pain_severities = PAIN_SEVERITIES
_valid_pain_durations = PAIN_DURATIONS
_valid_bp_concerns = BP_CONCERN_TYPES
_valid_bp_severities = BP_SEVERITIES
_valid_life_situations = LIFE_SITUATIONS
_valid_user_segments = USER_SEGMENTS
_valid_problem_categories = PROBLEM_CATEGORIES_LIST
_valid_frustrations = SOLUTION_FRUSTRATIONS
_valid_root_causes = NEGATIVE_ROOT_CAUSES
_valid_coping = COPING_STRATEGIES
_valid_bridge_moments = list(BRIDGE_MOMENT_TYPES.keys())

_DEEP_INSIGHTS_BASE = """Analysiere diesen deutschen Gesundheitsbeitrag und extrahiere tiefgehende Insights.
Kategorie des Beitrags: {category}

WICHTIG: Sei GROSSZÜGIG beim Zuweisen von Werten. Nutze Kontext-Hinweise und leite Werte ab, auch wenn
sie nicht wörtlich genannt werden. Beispiele:
- Jemand erwähnt "Büro" oder "am Schreibtisch" → life_situation: "buero_arbeit"
- Jemand nimmt Blutdruck-Medikamente → bp_severity: mindestens "hypertonie_1"
- Schmerzen seit "Jahren" oder "schon lange" → pain_duration: "jahre_chronisch", pain_severity: "chronisch"
- Jemand erwähnt "Rente" oder "Enkel" → life_situation: "senioren"
- Sportler/Training erwähnt → life_situation: "sport_aktiv"
- Jemand hat Übergewicht/BMI/Abnehmen erwähnt → life_situation: "uebergewicht"
- Student/Uni/Studium → life_situation: "studenten"
- Schwangerschaft/schwanger/Baby → life_situation: "schwangerschaft"
- Jemand beschreibt chronische Krankheit → life_situation: "chronisch_krank"
- Negativer Beitrag über ein Produkt → IMMER eine negative_root_cause zuweisen
Setze Felder nur dann auf null, wenn wirklich KEIN Hinweis im Text zu finden ist.

Antworte NUR mit validem JSON mit diesen Feldern:

{category_fields}

- coping_strategies: Array der erwähnten oder angedeuteten Bewältigungsstrategien (leeres Array NUR wenn gar keine):
  Erlaubte Werte: "ibuprofen", "paracetamol", "physiotherapie", "tens_geraet", "waermetherapie",
  "yoga", "arztbesuch", "bp_medikamente", "home_monitoring", "ernaehrung_diaet",
  "meditation", "massage", "bewegung_sport", "entspannung",
  "kaltetherapie", "osteopathie", "chiropraktik", "akupunktur"
  Hinweis: Auch indirekte Erwähnungen zählen — "war beim Orthopäden" → "arztbesuch",
  "nehme Tabletten" → "ibuprofen" oder "paracetamol" je nach Kontext.
  "Kälte"/"Eisbeutel"/"Kühlpack" → "kaltetherapie". "Osteopath" → "osteopathie".
  "Chiropraktiker" → "chiropraktik". "Akupunktur"/"Nadeln" → "akupunktur".

- medications_mentioned: Array der erwähnten Medikamente/Wirkstoffe als Freitext (leeres Array wenn keine)
  WICHTIG: Extrahiere SPEZIFISCHE Medikamentennamen (Ramipril, Metoprolol, Ibuprofen 600, Voltaren Gel,
  Novalgin, Tilidin, Amlodipin, Bisoprolol) — NICHT generische Begriffe wie "Medikamente" oder "Tabletten".
  Z.B.: ["Ramipril 5mg", "Ibuprofen 600", "Voltaren Gel"]
  Nur wenn KEIN spezifischer Name erkennbar: ["Schmerzmittel"] oder ["Blutdruck-Medikament"]

- user_segment: Nutzer-Segment (WER ist die Person?) — IMMER versuchen zuzuweisen, auch bei schwachen Hinweisen:
  Erlaubte Werte: "schwangerschaft", "buero_arbeit", "sport_aktiv", "senioren", "eltern_baby",
  "pendler", "schichtarbeit", "homeoffice", "pflegende_angehoerige", "studenten", "reisende", "fitness_ems"
  "Büro"/"am Schreibtisch" → "buero_arbeit". "Rente"/"Enkel" → "senioren".
  Sportler/Training → "sport_aktiv". Student/Uni/Studium → "studenten".
  Schwangerschaft/schwanger/Baby → "schwangerschaft". "EMS Training"/"Fitness EMS" → "fitness_ems".
  Nur null wenn wirklich KEIN Hinweis auf die Person vorhanden.

- problem_category: Gesundheitliche Problemkategorie (WAS hat die Person?) — IMMER versuchen zuzuweisen:
  Erlaubte Werte: "chronisch_krank", "post_op", "uebergewicht", "stress_burnout",
  "frisch_diagnostiziert", "medikamenten_nebenwirkungen_sucher",
  "migraene_patient", "fibromyalgie_patient", "endometriose"
  Wenn jemand über langanhaltende Beschwerden berichtet → "chronisch_krank"
  "Gerade erst Diagnose erhalten"/"neu diagnostiziert" → "frisch_diagnostiziert"
  "Nebenwirkungen"/"vertrage Medikament nicht" → "medikamenten_nebenwirkungen_sucher"
  Übergewicht/BMI/Abnehmen → "uebergewicht". Stress/Burnout → "stress_burnout".
  "Migräne-Patient"/"regelmäßig Migräne" → "migraene_patient"
  "Fibromyalgie" → "fibromyalgie_patient". "Endometriose" → "endometriose"
  Nur null wenn wirklich KEIN Hinweis auf gesundheitliches Problem vorhanden.

  WICHTIG: Ein Beitrag kann SOWOHL ein user_segment ALS AUCH eine problem_category haben.
  Beispiel: Ein Student mit Stress → user_segment: "studenten", problem_category: "stress_burnout"

- bridge_moment: Welcher Auslöser hat den Nutzer zum nächsten Schritt in der Customer Journey gebracht?
  Erlaubte Werte: "schmerz_loest_arztbesuch_aus", "medikament_loest_alternativsuche_aus",
  "arzt_empfiehlt_geraet", "freund_empfiehlt_produkt", "online_recherche_loest_kauf_aus",
  "testbericht_weckt_interesse", "diagnose_loest_monitoring_aus", "vergleich_loest_entscheidung_aus",
  "none_identified"
  Beispiele: "Mein Arzt hat mir ein TENS empfohlen" → "arzt_empfiehlt_geraet"
  "Weil meine Tabletten nicht mehr wirken, suche ich Alternativen" → "medikament_loest_alternativsuche_aus"
  "Nach der Diagnose will ich jetzt regelmäßig messen" → "diagnose_loest_monitoring_aus"
  "Habe einen Test gelesen" → "testbericht_weckt_interesse"
  Wenn kein klarer Auslöser erkennbar → "none_identified" (NICHT null)

- solution_frustrations: Array der Frustrationen mit bisherigen Lösungen (leeres Array nur wenn keine):
  Erlaubte Werte: "keine_besserung", "nebenwirkungen_medikamente", "zu_teuer",
  "keine_langzeitwirkung", "unangenehme_anwendung", "widerspruechliche_infos",
  "arzt_nimmt_nicht_ernst", "wartezeit_arzt", "geraet_kompliziert",
  "manschette_problem", "app_verbindung", "messungenauigkeit"

- negative_root_cause: Hauptursache für Unzufriedenheit — bei JEDEM negativen oder gemischten Beitrag zuweisen:
  Erlaubte Werte: "produkt_defekt", "fehlbedienung", "falsche_erwartung",
  "kompatibilitaet", "service_mangel", "preis_leistung", "design_ergonomie"
  Nur null wenn Beitrag eindeutig positiv oder neutral ist.

- key_insight: Ein kurzer Satz (max 20 Wörter, Deutsch) — was ist das wichtigste Insight aus diesem Beitrag für Beurer?
  Z.B.: "Nutzer wünscht sich TENS-Gerät mit Programm speziell für Nackenschmerzen am Arbeitsplatz"

- content_opportunity: Ein kurzer Satz (max 20 Wörter, Deutsch) — welchen Content könnte Beurer daraus ableiten?
  Sei SPEZIFISCH — schlage konkrete Artikel-Titel vor, nicht generische Beschreibungen.
  GUT: "Ratgeber: Blutdruckmessung in der Schwangerschaft — richtig messen und Werte verstehen"
  GUT: "Video: TENS-Elektroden richtig platzieren bei Ischias-Schmerzen"
  SCHLECHT: "Content über Blutdruck erstellen" (zu vage)
  SCHLECHT: "Informationen bereitstellen" (zu generisch)
  Oder null wenn keine Content-Chance erkennbar.

- aspects: Array of product/service aspects discussed in this post. Only include aspects ACTUALLY discussed.
  Each element: {{"aspect": "one_of_10", "sentiment": "positive/neutral/negative", "intensity": 1-5, "evidence": "short quote from text"}}
  Allowed aspect values: messgenauigkeit, bedienbarkeit, verarbeitung, preis_leistung, app_konnektivitaet, manschette_elektroden, display_anzeige, schmerzlinderung, akku_batterie, kundenservice
  Only include aspects that are explicitly or clearly implicitly discussed. Empty array if no product aspects are discussed.
  Examples:
  - "Die Werte schwanken ständig" -> [{{"aspect": "messgenauigkeit", "sentiment": "negative", "intensity": 4, "evidence": "Werte schwanken ständig"}}]
  - "App verbindet sich nicht" -> [{{"aspect": "app_konnektivitaet", "sentiment": "negative", "intensity": 4, "evidence": "App verbindet sich nicht"}}]
  - "Super einfach zu bedienen" -> [{{"aspect": "bedienbarkeit", "sentiment": "positive", "intensity": 4, "evidence": "Super einfach zu bedienen"}}]

- entity_sentiments: Array of per-entity sentiment for EACH product or brand mentioned in the text.
  Each element: {{"entity": "exact product/brand name", "sentiment": "positive/neutral/negative", "intensity": 1-5, "reason": "short German phrase"}}
  WICHTIG: Verschiedene Produkte im selben Beitrag können UNTERSCHIEDLICHE Sentiments haben.
  Only include entities actually mentioned. Empty array if no products/brands mentioned.
  Examples:
  - "Beurer BM 27 zeigt falsche Werte, Omron ist besser" ->
    [{{"entity": "BM 27", "sentiment": "negative", "intensity": 4, "reason": "falsche Messwerte"}},
     {{"entity": "Omron", "sentiment": "positive", "intensity": 3, "reason": "als besser bewertet"}}]
  - "Mein EM 59 ist super" -> [{{"entity": "EM 59", "sentiment": "positive", "intensity": 4, "reason": "sehr zufrieden"}}]

Beitrag:
{content}

Antworte mit NUR dem JSON-Objekt, kein Markdown oder Erklärung."""

_PAIN_FIELDS = """- pain_location: Schmerzort — IMMER zuweisen wenn irgendein Körperteil erwähnt wird:
  Erlaubte Werte: "ruecken_oberer", "ruecken_unterer", "nacken", "schulter", "knie",
  "huelte", "handgelenk", "ellbogen", "fuss", "unterleib", "ganzer_koerper",
  "kopf_migraene", "nerven_ischias", "gelenke_allgemein", "muskelverspannung", "fibromyalgie"
  "Rücken" allgemein → "ruecken_unterer" (häufigster). "Regelschmerzen"/"Periode" → "unterleib".
  "Migräne"/"Kopfschmerzen" → "kopf_migraene". "Ischias"/"Ischiasnerv" → "nerven_ischias".
  "Gelenke" allgemein → "gelenke_allgemein". "Verspannung"/"verspannt" → "muskelverspannung".
  "Fibromyalgie" → "fibromyalgie".
  Wenn mehrere Orte → den am meisten betroffenen wählen.

- pain_severity: Schmerzstärke — aus dem Kontext ableiten, auch wenn nicht explizit gesagt:
  Erlaubte Werte: "leicht", "mittel", "stark", "chronisch", "akut"
  "Ich kann nicht mehr"/"unerträglich" → "stark". "Ab und zu" → "leicht".
  "Seit Jahren"/"chronisch" → "chronisch". "Plötzlich"/"gerade" → "akut".
  Standard wenn unklar aber Beschwerden vorhanden: "mittel"

- pain_duration: Schmerzdauer — aus Zeitangaben und Kontext ableiten:
  Erlaubte Werte: "akut_tage", "wochen", "monate", "jahre_chronisch", "episodisch"
  "Seit gestern"/"seit ein paar Tagen" → "akut_tage". "Seit Wochen" → "wochen".
  "Schon lange"/"seit Monaten" → "monate". "Seit Jahren"/"chronisch" → "jahre_chronisch".
  Regelschmerzen/Migräneattacken → "episodisch" (wiederkehrend, nicht dauerhaft).
  Schübe die kommen und gehen → "episodisch".
"""

_BP_FIELDS = """- bp_concern_type: Art der Blutdruck-Sorge — IMMER zuweisen bei Blutdruck-Beiträgen:
  Erlaubte Werte: "messgenauigkeit", "schwankende_werte", "weisser_kittel",
  "medikamenten_kontrolle", "morgen_abend_unterschied", "arm_unterschied",
  "geraete_vergleich", "normwerte_frage", "hypertonie_angst", "monitoring_routine"
  Geräte-Frage/Kaufberatung → "geraete_vergleich". "Werte zu hoch" → "hypertonie_angst".
  "Welches Gerät?" → "geraete_vergleich". Allgemeine Messung → "monitoring_routine".

- bp_severity: Blutdruck-Schweregrad — aus KONTEXT ableiten, nicht nur aus expliziten Werten:
  Erlaubte Werte: "optimal", "normal", "hoch_normal", "hypertonie_1", "hypertonie_2", "unspecified"
  Schwellenwerte: optimal <120/<80, normal 120-129/80-84, hoch_normal 130-139/85-89,
  hypertonie_1 140-159/90-99, hypertonie_2 ≥160/≥100.
  Nimmt BP-Medikamente → mindestens "hypertonie_1". "Bluthochdruck diagnostiziert" → "hypertonie_1".
  "Werte waren 160/100" → "hypertonie_1". "180 oder höher" → "hypertonie_2".
  "Blutdruck ist ok/normal" → "normal". "Leicht erhöht" → "hoch_normal".
  WICHTIG: Wenn Blutdruck diskutiert wird aber KEINE konkreten Werte genannt werden → "unspecified", NICHT null.
  Nur null wenn der Beitrag NICHT über Blutdruck handelt.
"""

_NO_CATEGORY_FIELDS = """(Keine kategorie-spezifischen Felder für diese Kategorie — nur die allgemeinen Felder unten ausfüllen.)
"""


def classify_deep_insights(content: str, title: str = "", category: str = "") -> Dict[str, Any]:
    """Classify a single item for deep insights.

    Args:
        content: The main content text
        title: Optional title for context
        category: Item category (blood_pressure, pain_tens, menstrual, etc.)

    Returns:
        Dict with all deep insight fields including aspects
    """
    model = get_classification_model()

    full_text = f"{title}\n\n{content}" if title else content
    if len(full_text) > 10000:
        full_text = full_text[:10000]

    # Select category-specific fields
    if category in ("pain_tens", "menstrual"):
        category_fields = _PAIN_FIELDS
    elif category == "blood_pressure":
        category_fields = _BP_FIELDS
    else:
        category_fields = _NO_CATEGORY_FIELDS

    prompt = _DEEP_INSIGHTS_BASE.format(
        category=category or "unknown",
        category_fields=category_fields,
        content=full_text,
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        result = json.loads(text)

        # Validate enum fields — invalid → None
        if result.get("pain_location") not in _valid_pain_locations:
            result["pain_location"] = None
        if result.get("pain_severity") not in _valid_pain_severities:
            result["pain_severity"] = None
        if result.get("pain_duration") not in _valid_pain_durations:
            result["pain_duration"] = None
        if result.get("bp_concern_type") not in _valid_bp_concerns:
            result["bp_concern_type"] = None
        if result.get("bp_severity") not in _valid_bp_severities:
            result["bp_severity"] = None
        if result.get("user_segment") not in _valid_user_segments:
            result["user_segment"] = None
        if result.get("problem_category") not in _valid_problem_categories:
            result["problem_category"] = None
        # Backward compat: derive life_situation from the two new fields
        result["life_situation"] = result.get("user_segment") or result.get("problem_category")
        if result.get("negative_root_cause") not in _valid_root_causes:
            result["negative_root_cause"] = None
        if result.get("bridge_moment") not in _valid_bridge_moments:
            result["bridge_moment"] = None

        # Validate array fields — filter invalid elements
        if isinstance(result.get("coping_strategies"), list):
            result["coping_strategies"] = [s for s in result["coping_strategies"] if s in _valid_coping]
        else:
            result["coping_strategies"] = []

        if not isinstance(result.get("medications_mentioned"), list):
            result["medications_mentioned"] = []
        else:
            result["medications_mentioned"] = [str(m)[:100] for m in result["medications_mentioned"] if m]

        if isinstance(result.get("solution_frustrations"), list):
            result["solution_frustrations"] = [f for f in result["solution_frustrations"] if f in _valid_frustrations]
        else:
            result["solution_frustrations"] = []

        # Validate free-text fields
        if not isinstance(result.get("key_insight"), str) or not result["key_insight"].strip():
            result["key_insight"] = None
        else:
            result["key_insight"] = result["key_insight"][:200]

        if not isinstance(result.get("content_opportunity"), str) or not result["content_opportunity"].strip():
            result["content_opportunity"] = None
        else:
            result["content_opportunity"] = result["content_opportunity"][:200]

        # Validate aspects array
        if isinstance(result.get("aspects"), list):
            valid_aspects = []
            for aspect_entry in result["aspects"]:
                if not isinstance(aspect_entry, dict):
                    continue
                aspect_name = aspect_entry.get("aspect")
                aspect_sentiment = aspect_entry.get("sentiment")
                if aspect_name not in ASPECT_CATEGORIES:
                    continue
                if aspect_sentiment not in ["positive", "neutral", "negative"]:
                    continue
                # Validate intensity
                aspect_intensity = aspect_entry.get("intensity", 3)
                if not isinstance(aspect_intensity, int) or aspect_intensity < 1 or aspect_intensity > 5:
                    aspect_intensity = 3
                valid_aspects.append({
                    "aspect": aspect_name,
                    "sentiment": aspect_sentiment,
                    "intensity": aspect_intensity,
                    "evidence": str(aspect_entry.get("evidence", ""))[:500],
                })
            result["aspects"] = valid_aspects
        else:
            result["aspects"] = []

        # Validate entity_sentiments array
        if isinstance(result.get("entity_sentiments"), list):
            valid_entity_sents = []
            for es_entry in result["entity_sentiments"]:
                if not isinstance(es_entry, dict):
                    continue
                entity_name = es_entry.get("entity")
                es_sentiment = es_entry.get("sentiment")
                if not entity_name or not isinstance(entity_name, str):
                    continue
                if es_sentiment not in ["positive", "neutral", "negative"]:
                    es_sentiment = "neutral"
                es_intensity = es_entry.get("intensity", 3)
                if not isinstance(es_intensity, int) or es_intensity < 1 or es_intensity > 5:
                    es_intensity = 3
                valid_entity_sents.append({
                    "entity": entity_name.strip()[:100],
                    "sentiment": es_sentiment,
                    "intensity": es_intensity,
                    "reason": str(es_entry.get("reason", ""))[:200],
                })
            result["entity_sentiments"] = valid_entity_sents
        else:
            result["entity_sentiments"] = []

        # Defense-in-depth: null out fields that don't belong to the item's category
        if category == "blood_pressure":
            result["pain_location"] = None
            result["pain_severity"] = None
            result["pain_duration"] = None
        elif category in ("pain_tens", "menstrual"):
            result["bp_concern_type"] = None
            result["bp_severity"] = None
        elif category in ("other", "infrarot"):
            result["pain_location"] = None
            result["pain_severity"] = None
            result["pain_duration"] = None
            result["bp_concern_type"] = None
            result["bp_severity"] = None

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse deep insights JSON: {e}")
        return _empty_deep_insights()
    except Exception as e:
        logger.error(f"Deep insights classification failed: {e}")
        raise


def _empty_deep_insights() -> Dict[str, Any]:
    """Return empty deep insights result."""
    return {
        "pain_location": None,
        "pain_severity": None,
        "pain_duration": None,
        "bp_concern_type": None,
        "bp_severity": None,
        "coping_strategies": [],
        "medications_mentioned": [],
        "life_situation": None,
        "user_segment": None,
        "problem_category": None,
        "solution_frustrations": [],
        "negative_root_cause": None,
        "key_insight": None,
        "content_opportunity": None,
        "bridge_moment": None,
        "aspects": [],
        "entity_sentiments": [],
    }


def _safe_update_dict(current_row: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build update dict that never overwrites non-null values with null.

    Only includes fields where the new value is non-null, or where the current
    value is already null/empty. Prevents regressions during re-backfills.
    """
    safe = {}
    for field, new_value in new_data.items():
        current_value = current_row.get(field)
        current_is_filled = (
            current_value is not None
            and str(current_value).strip() != ''
            and str(current_value).strip().lower() not in ('null', 'none')
            and current_value != []
        )
        new_is_filled = (
            new_value is not None
            and str(new_value).strip() != ''
            and str(new_value).strip().lower() not in ('null', 'none')
            and new_value != []
        )

        if new_is_filled:
            # New value exists — always update
            safe[field] = new_value
        elif not current_is_filled:
            # Both empty — include to keep consistent
            safe[field] = new_value
        # else: current is filled but new is null — SKIP (preserve old value)

    return safe


def _match_entity_sentiment_to_entities(entity_sentiments: List[Dict], item_entities: List[Dict]) -> List[Dict]:
    """Cross-reference LLM entity names with item_entities canonical names.

    Returns list of dicts: {entity_id, sentiment} for matched entities.
    Uses substring matching to handle variations like "BM 27" vs "Beurer BM 27".
    """
    matched = []
    used_entity_ids = set()

    for es in entity_sentiments:
        entity_name_lower = (es.get("entity") or "").lower().strip()
        if not entity_name_lower:
            continue

        for entity_row in item_entities:
            entity_id = entity_row.get("entity_id")
            if entity_id in used_entity_ids:
                continue
            entity_info = entity_row.get("entities") or {}
            canonical = (entity_info.get("canonical_name") or "").lower()
            if not canonical:
                continue
            # Substring match in either direction
            if entity_name_lower in canonical or canonical in entity_name_lower:
                matched.append({
                    "entity_id": entity_id,
                    "sentiment": es.get("sentiment", "neutral"),
                })
                used_entity_ids.add(entity_id)
                break

    return matched


def backfill_deep_insights(batch_size: int = 50, category_filter: str = None, force: bool = False, after_id: str = None) -> dict:
    """Backfill deep insights for items missing them.

    Args:
        batch_size: Number of items to process per run
        category_filter: Optional category to prioritize (e.g. "blood_pressure")
        force: If True, re-classify ALL items (not just those with NULL key_insight)
        after_id: Process items with id > this value (for pagination in force mode)

    Returns:
        Dict with stats: {processed, failed, by_category: {cat: count}, last_id, aspects_saved, entity_sentiments_saved}
    """
    from db.client import get_beurer_supabase, save_item_aspects

    client = get_beurer_supabase()
    stats = {"processed": 0, "failed": 0, "by_category": {}, "last_id": None, "aspects_saved": 0, "entity_sentiments_saved": 0}

    # Query items: force=True reclassifies all, otherwise only NULL key_insight
    _deep_fields = ("id, title, content, category, sentiment, "
                    "pain_location, pain_severity, pain_duration, bp_concern_type, bp_severity, "
                    "coping_strategies, medications_mentioned, life_situation, user_segment, problem_category, "
                    "solution_frustrations, negative_root_cause, key_insight, content_opportunity, bridge_moment")
    query = client.table("social_items") \
        .select(_deep_fields) \
        .not_.is_("category", "null") \
        .order("id") \
        .limit(batch_size)

    if not force:
        query = query.is_("key_insight", "null")

    if category_filter:
        query = query.eq("category", category_filter)

    if after_id:
        query = query.gt("id", after_id)

    result = query.execute()

    if not result.data:
        logger.info("No items need deep insights backfill")
        return stats

    items = result.data
    logger.info(f"Processing {len(items)} items for deep insights classification")

    # Batch-fetch item_entities for all items in this batch
    item_ids = [i["id"] for i in items]
    entities_by_item: Dict[str, List[Dict]] = {}
    try:
        for batch_start in range(0, len(item_ids), 100):
            batch_ids = item_ids[batch_start:batch_start + 100]
            ent_result = client.table("item_entities") \
                .select("social_item_id, entity_id, sentiment, entities(canonical_name, entity_type)") \
                .in_("social_item_id", batch_ids) \
                .execute()
            for row in (ent_result.data or []):
                sid = row["social_item_id"]
                if sid not in entities_by_item:
                    entities_by_item[sid] = []
                entities_by_item[sid].append(row)
    except Exception as e:
        logger.warning(f"Could not fetch item_entities for deep insights batch: {e}")

    for item in items:
        try:
            classification = classify_deep_insights(
                content=item.get("content", ""),
                title=item.get("title", ""),
                category=item.get("category", ""),
            )

            # Extract aspects and entity_sentiments before building the DB update dict
            aspects = classification.pop("aspects", [])
            entity_sentiments = classification.pop("entity_sentiments", [])

            new_data = {
                "pain_location": classification.get("pain_location"),
                "pain_severity": classification.get("pain_severity"),
                "pain_duration": classification.get("pain_duration"),
                "bp_concern_type": classification.get("bp_concern_type"),
                "bp_severity": classification.get("bp_severity"),
                "coping_strategies": classification.get("coping_strategies", []),
                "medications_mentioned": classification.get("medications_mentioned", []),
                "life_situation": classification.get("life_situation"),
                "user_segment": classification.get("user_segment"),
                "problem_category": classification.get("problem_category"),
                "solution_frustrations": classification.get("solution_frustrations", []),
                "negative_root_cause": classification.get("negative_root_cause"),
                "key_insight": classification.get("key_insight") or "classified",
                "content_opportunity": classification.get("content_opportunity"),
                "bridge_moment": classification.get("bridge_moment"),
            }

            # Use safe update to prevent overwriting non-null with null
            update_data = _safe_update_dict(item, new_data) if force else new_data

            client.table("social_items") \
                .update(update_data) \
                .eq("id", item["id"]) \
                .execute()

            # Save aspects to item_aspects table
            if aspects:
                aspects_for_db = []
                for a in aspects:
                    aspects_for_db.append({
                        "aspect": a["aspect"],
                        "sentiment": a["sentiment"],
                        "intensity": a.get("intensity", 3),
                        "evidence_snippet": a.get("evidence", ""),
                    })
                saved_count = save_item_aspects(client, item["id"], aspects_for_db)
                stats["aspects_saved"] += saved_count

            # Update entity sentiments in item_entities
            item_ents = entities_by_item.get(item["id"], [])
            if entity_sentiments and item_ents:
                matched = _match_entity_sentiment_to_entities(entity_sentiments, item_ents)
                for m in matched:
                    try:
                        client.table("item_entities").update({
                            "sentiment": m["sentiment"],
                        }).eq("social_item_id", item["id"]).eq("entity_id", m["entity_id"]).execute()
                        stats["entity_sentiments_saved"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to update entity sentiment for item {item['id']}: {e}")

            stats["processed"] += 1
            cat = item.get("category", "unknown")
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            logger.debug(f"Deep insights classified item {item['id']}: {cat}")

            # Rate limiting - Gemini free tier is 60 RPM
            time.sleep(1.1)

        except Exception as e:
            logger.error(f"Failed deep insights for item {item['id']}: {e}")
            stats["failed"] += 1

    if items:
        stats["last_id"] = items[-1]["id"]

    logger.info(f"Deep insights backfill complete: {stats}")
    return stats
