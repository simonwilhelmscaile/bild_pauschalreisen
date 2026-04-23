"""Rewrite sentences containing third-person 'Sie' to avoid ambiguity with formal address.

After the Du-form switch, 'Sie' should never appear in articles. This script finds
all occurrences and uses Gemini to rewrite just the affected sentences, replacing
the pronoun with the actual noun (e.g. 'Sie kombinieren...' -> 'Die Geräte kombinieren...').

Usage: python scripts/fix_sie_sentences.py [--dry-run]
"""
import json
import os
import re
import sys
import time

import google.generativeai as genai
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["BEURER_SUPABASE_URL"]
SUPABASE_KEY = os.environ["BEURER_SUPABASE_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

DRY_RUN = "--dry-run" in sys.argv

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

CONTENT_FIELDS = ["Intro", "Direct_Answer", "TLDR"]
for i in range(1, 10):
    CONTENT_FIELDS.append(f"section_{i:02d}_content")
for i in range(1, 7):
    CONTENT_FIELDS.append(f"faq_{i:02d}_answer")
for i in range(1, 5):
    CONTENT_FIELDS.append(f"paa_{i:02d}_answer")


def find_sie_sentences(html: str) -> list[tuple[str, str]]:
    """Find sentences containing 'Sie' in HTML content.

    Returns list of (original_sentence, surrounding_context) tuples.
    """
    # Strip HTML tags for sentence detection
    plain = re.sub(r"<[^>]+>", "", html)
    results = []
    # Split into sentences (rough but sufficient)
    sentences = re.split(r"(?<=[.!?])\s+", plain)
    for sent in sentences:
        if re.search(r"\bSie\b", sent):
            results.append(sent.strip())
    return results


def rewrite_field(field_value: str, keyword: str) -> tuple[str, int]:
    """Rewrite all 'Sie' occurrences in a field using Gemini.

    Returns (new_field_value, number_of_rewrites).
    """
    sie_sentences = find_sie_sentences(field_value)
    if not sie_sentences:
        return field_value, 0

    prompt = f"""Du bist ein deutscher Lektor. Der folgende HTML-Text enthält das Wort "Sie" als Pronomen der dritten Person (sie/es/they).

AUFGABE: Ersetze jedes "Sie" durch das konkrete Substantiv, auf das es sich bezieht (z.B. "das Gerät", "die Manschette", "die Geräte", "die Infrarotlampe", "Schmerzmittel" etc.).

REGELN:
- Ersetze NUR "Sie" durch das passende Substantiv — ändere NICHTS anderes
- Behalte den Rest des Satzes exakt bei (Grammatik, HTML-Tags, Interpunktion)
- Wenn "Sie" am Satzanfang steht, ersetze es durch das Substantiv mit großem Anfangsbuchstaben
- Gib den KOMPLETTEN HTML-Text zurück, nicht nur die geänderten Sätze
- Antworte NUR mit dem korrigierten HTML, ohne Erklärungen

Artikel-Thema: {keyword}

HTML-TEXT:
{field_value}"""

    try:
        response = model.generate_content(prompt)
        rewritten = response.text.strip()
        # Remove markdown code fences if present
        if rewritten.startswith("```"):
            rewritten = re.sub(r"^```(?:html)?\n?", "", rewritten)
            rewritten = re.sub(r"\n?```$", "", rewritten)
        # Verify no Sie remains and the result isn't empty/garbage
        if not rewritten or len(rewritten) < len(field_value) * 0.5:
            print(f"    WARNING: Gemini returned suspicious output, skipping")
            return field_value, 0
        remaining = len(re.findall(r"\bSie\b", re.sub(r"<[^>]+>", "", rewritten)))
        return rewritten, len(sie_sentences) - remaining
    except Exception as e:
        print(f"    ERROR: Gemini call failed: {e}")
        return field_value, 0


def main():
    print(f"{'DRY RUN — ' if DRY_RUN else ''}Fetching completed articles...")
    result = (
        supabase.table("blog_articles")
        .select("id,keyword,article_json")
        .eq("status", "completed")
        .execute()
    )
    articles = result.data
    print(f"Found {len(articles)} completed articles\n")

    total_rewrites = 0
    articles_fixed = 0

    for a in articles:
        aid = a["id"][:8]
        keyword = a["keyword"]
        art = a["article_json"]

        # Check if this article has any Sie
        has_sie = False
        for field in CONTENT_FIELDS:
            val = art.get(field)
            if isinstance(val, str) and re.search(r"\bSie\b", val):
                has_sie = True
                break

        if not has_sie:
            continue

        print(f"\n  [{aid}] {keyword[:55]}")
        article_rewrites = 0

        for field in CONTENT_FIELDS:
            val = art.get(field)
            if not isinstance(val, str) or not re.search(r"\bSie\b", val):
                continue

            sentences = find_sie_sentences(val)
            print(f"    {field}: {len(sentences)} sentence(s) with 'Sie'")
            for s in sentences:
                print(f"      > {s[:80]}...")

            if not DRY_RUN:
                new_val, count = rewrite_field(val, keyword)
                if count > 0:
                    art[field] = new_val
                    article_rewrites += count
                    print(f"    -> Rewrote {count} occurrence(s)")
                    # Show what changed
                    remaining = re.findall(r"\bSie\b", re.sub(r"<[^>]+>", "", new_val))
                    if remaining:
                        print(f"    WARNING: {len(remaining)} 'Sie' still remain")
                time.sleep(1.5)  # Rate limit

        if not DRY_RUN and article_rewrites > 0:
            supabase.table("blog_articles").update(
                {"article_json": art}
            ).eq("id", a["id"]).execute()
            print(f"    SAVED ({article_rewrites} rewrites)")
            total_rewrites += article_rewrites
            articles_fixed += 1

    print(f"\n{'DRY RUN ' if DRY_RUN else ''}Summary:")
    print(f"  Articles with Sie: {sum(1 for a in articles for f in CONTENT_FIELDS if isinstance(a['article_json'].get(f), str) and re.search(r'\\bSie\\b', a['article_json'].get(f, '')))}")
    print(f"  Articles fixed: {articles_fixed}")
    print(f"  Total rewrites: {total_rewrites}")


if __name__ == "__main__":
    main()
