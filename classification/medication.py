"""Medication name normalization."""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Medication normalization map
MEDICATION_NORMALIZATION = {
    'gabapentin': 'Gabapentin',
    'amlodipine': 'Amlodipin',
    'amlodipine 5mg': 'Amlodipin 5mg',
    'amlodipine 10mg': 'Amlodipin 10mg',
    'ramipril 5mg': 'Ramipril 5mg',
    'oxycodone': 'Oxycodon',
    'morphine': 'Morphin',
    'codeine': 'Codein',
    'pregablin': 'Pregabalin',
    'pregabalin': 'Pregabalin',
    'fentanyl': 'Fentanyl',
    'muscle relaxers': 'Muskelrelaxantien',
    'antibiotics': 'Antibiotika',
    'buscopan plus': 'Buscopan Plus',
    'propanol 50mg': 'Propranolol 50mg',
    'norethisterone': 'Norethisteron',
    'flexeril': 'Cyclobenzaprin',
    'zanaflex': 'Tizanidin',
    'tylenol': 'Paracetamol',
    'schmerzmittel': 'Schmerzmittel (unspezifisch)',
    'blutdruck-medikament': 'Blutdrucksenker (unspezifisch)',
    'medikamente': 'Medikamente (unspezifisch)',
    'schmerztabletten': 'Schmerzmittel (unspezifisch)',
    'blutdrucktabletten': 'Blutdrucksenker (unspezifisch)',
    'medikament': 'Medikamente (unspezifisch)',
    'tabletten': 'Tabletten (unspezifisch)',
    'medikation': 'Medikamente (unspezifisch)',
    'amlodipin 5mg': 'Amlodipin 5mg',
    'ozempic': 'Ozempic',
}

# Build case-insensitive lookup
_MED_NORM_LOWER = {k.lower(): v for k, v in MEDICATION_NORMALIZATION.items()}


def normalize_medications() -> dict:
    """Normalize medication names across all items in the database."""
    from db.client import get_beurer_supabase

    client = get_beurer_supabase()
    stats = {"checked": 0, "updated": 0}

    # Paginate through all items with medications
    last_id = None
    while True:
        query = client.table("social_items") \
            .select("id, medications_mentioned") \
            .not_.is_("medications_mentioned", "null") \
            .order("id") \
            .limit(200)

        if last_id:
            query = query.gt("id", last_id)

        result = query.execute()
        if not result.data:
            break

        for item in result.data:
            meds = item.get("medications_mentioned") or []
            if not isinstance(meds, list) or not meds:
                continue

            normalized = []
            changed = False
            for med in meds:
                med_str = str(med).strip()
                med_lower = med_str.lower()
                if med_lower in _MED_NORM_LOWER:
                    norm = _MED_NORM_LOWER[med_lower]
                    normalized.append(norm)
                    if norm != med_str:
                        changed = True
                else:
                    # Normalize casing for unknown meds:
                    # all-lowercase or ALL-CAPS or mixed oddities → Title Case
                    if len(med_str) > 2 and (med_str.islower() or med_str.isupper() or med_str != med_str.title()):
                        # Check if title case would be appropriate
                        # Keep dosage parts intact (e.g. "5mg", "10mg")
                        parts = med_str.split()
                        norm_parts = []
                        for p in parts:
                            if any(c.isdigit() for c in p):
                                # Dosage part — lowercase the unit
                                norm_parts.append(p.lower())
                            else:
                                norm_parts.append(p.capitalize())
                        norm = " ".join(norm_parts)
                        normalized.append(norm)
                        if norm != med_str:
                            changed = True
                    else:
                        normalized.append(med_str)

            if changed:
                client.table("social_items") \
                    .update({"medications_mentioned": normalized}) \
                    .eq("id", item["id"]) \
                    .execute()
                stats["updated"] += 1

            stats["checked"] += 1

        last_id = result.data[-1]["id"]

    logger.info(f"Medication normalization: {stats}")
    return stats
