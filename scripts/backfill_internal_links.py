"""
Backfill internal links for blog articles missing them.
Runs Stage 5 (internal linking) directly against Supabase + Gemini.
"""
import json
import os
import re
import time
import requests

# Config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://oztcipklrywjmyvfihva.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96dGNpcGtscnl3am15dmZpaHZhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc3MjUxNSwiZXhwIjoyMDg3MzQ4NTE1fQ.QPFjFnmTmfieFIi24qny7rmQb1zomB0_tXNnMhLvZGA")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBdwLCjjzdCIOZBiia3E4YVo1wbS0SohUI")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# Beurer sitemap URLs
LINK_POOL = [
    {"url": "https://www.beurer.com/de/l/blutdruckmessgeraete/", "title": "Blutdruckmessgeräte"},
    {"url": "https://www.beurer.com/de/l/tens-ems/", "title": "TENS & EMS Geräte"},
    {"url": "https://www.beurer.com/de/l/em-50-menstrual-relax-pad/", "title": "Menstrual Relax Pad"},
    {"url": "https://www.beurer.com/de/l/waerme/", "title": "Wärmeprodukte"},
    {"url": "https://www.beurer.com/de/l/massage-guns/", "title": "Massage Guns"},
    {"url": "https://www.beurer.com/de/blog/", "title": "Beurer Blog"},
    {"url": "https://www.beurer.com/de/c/0010101/", "title": "Oberarm-Blutdruckmessgeräte"},
    {"url": "https://www.beurer.com/de/c/0010102/", "title": "Handgelenk-Blutdruckmessgeräte"},
    {"url": "https://www.beurer.com/de/c/0010401/", "title": "TENS-Geräte"},
    {"url": "https://www.beurer.com/de/c/0010402/", "title": "EMS-Geräte"},
    {"url": "https://www.beurer.com/de/c/00201/", "title": "Wärme-Therapie"},
    {"url": "https://www.beurer.com/de/c/0010302/", "title": "Infrarotlampen"},
    {"url": "https://www.beurer.com/de/service/connect/healthmanager-pro/", "title": "HealthManager Pro App"},
    {"url": "https://www.beurer.com/de/service/app-welt/", "title": "Beurer App-Welt"},
    {"url": "https://www.beurer.com/de/l/produktberater-blutdruck/", "title": "Produktberater Blutdruck"},
    {"url": "https://www.beurer.com/de/l/produktberater-tens-ems/", "title": "Produktberater TENS/EMS"},
    {"url": "https://www.beurer.com/de/kontakt/", "title": "Kontakt"},
    {"url": "https://www.beurer.com/de/service/faq/", "title": "FAQ & Hilfe"},
]

VALID_URLS = {l["url"] for l in LINK_POOL}
PROTECTED_TAGS = ["a", "button", "h1", "h2", "h3", "h4", "h5", "h6", "code", "pre"]


def fetch_articles():
    """Fetch all completed articles."""
    url = f"{SUPABASE_URL}/rest/v1/blog_articles?status=eq.completed&select=id,keyword,article_json,article_html"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def needs_links(article):
    """Check if article is missing internal links."""
    html = article.get("article_html") or ""
    return "beurer.com" not in html


def extract_sections(article_json):
    """Extract content sections for Gemini prompt."""
    sections = []
    if article_json.get("Intro"):
        sections.append(f"[Intro]\n{article_json['Intro']}")
    for i in range(1, 10):
        key = f"section_{str(i).zfill(2)}_content"
        if article_json.get(key):
            sections.append(f"[{key}]\n{article_json[key]}")
    return "\n\n".join(sections)


def call_gemini(sections_text, pool):
    """Call Gemini to get link placement suggestions."""
    links_text = "\n".join(f"- {l['title']}: {l['url']}" for l in pool)

    prompt = f"""You are an SEO expert. Embed these internal links naturally into the article sections.

AVAILABLE LINKS:
{links_text}

ARTICLE SECTIONS:
{sections_text}

RULES:
- Add 3-5 links total across all sections
- Use natural German anchor text (NOT "click here", NOT the full URL)
- Spread links across DIFFERENT sections
- Don't link the same URL twice
- The "find" text must be an EXACT, COMPLETE phrase from the section (copy-paste exactly)
- Keep anchor text concise (2-5 words) but COMPLETE (no partial words!)
- Only link phrases that naturally relate to the target page topic

Return JSON array: [{{"field":"section_01_content","find":"exact phrase","replace":"<a href=\\"url\\">exact phrase</a>"}}]"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.3,
        },
    }
    r = requests.post(url, json=body)
    r.raise_for_status()
    data = r.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else parsed.get("embeddings", [])
    except json.JSONDecodeError:
        print(f"  Failed to parse Gemini response: {text[:200]}")
        return []


def is_protected(content, pos):
    """Check if position is inside a protected tag."""
    before = content[:pos].lower()
    for tag in PROTECTED_TAGS:
        last_open = before.rfind(f"<{tag}")
        if last_open == -1:
            continue
        # Verify it's actually the tag (not <aside matching <a)
        char_after = before[last_open + len(tag) + 1] if last_open + len(tag) + 1 < len(before) else ""
        if char_after and char_after not in (">", " ", "\t", "\n"):
            continue
        last_close = before.rfind(f"</{tag}>")
        if last_open > last_close:
            return True
    return False


def apply_embeddings(article_json, embeddings):
    """Apply link embeddings to article content."""
    modified = dict(article_json)
    applied = 0
    used_urls = set()

    for emb in embeddings:
        field = emb.get("field")
        find_text = emb.get("find")
        replace_text = emb.get("replace")
        if not field or not find_text or not replace_text:
            continue

        content = modified.get(field)
        if not isinstance(content, str):
            continue

        # Find text (case-insensitive fallback)
        actual_find = find_text
        if find_text not in content:
            idx = content.lower().find(find_text.lower())
            if idx == -1:
                continue
            actual_find = content[idx : idx + len(find_text)]

        # Validate <a> tag
        a_match = re.match(
            r'^<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>.+</a>$',
            replace_text,
            re.IGNORECASE | re.DOTALL,
        )
        if not a_match:
            continue

        url = a_match.group(1)
        url_norm = url.rstrip("/").lower()

        # Check URL in pool
        found = any(v.rstrip("/").lower() == url_norm for v in VALID_URLS)
        if not found:
            continue
        if url_norm in used_urls:
            continue

        # Find unprotected position
        pos = content.find(actual_find)
        if pos == -1:
            continue
        if is_protected(content, pos):
            continue

        modified[field] = content[:pos] + replace_text + content[pos + len(actual_find) :]
        used_urls.add(url_norm)
        applied += 1

    return modified, applied


def update_article(article_id, new_json):
    """Update article_json in Supabase (HTML will be re-rendered on next view)."""
    url = f"{SUPABASE_URL}/rest/v1/blog_articles?id=eq.{article_id}"
    body = {"article_json": new_json}
    r = requests.patch(url, json=body, headers=HEADERS)
    r.raise_for_status()
    return True


def main():
    print("Fetching articles...")
    articles = fetch_articles()
    print(f"Total articles: {len(articles)}")

    missing = [a for a in articles if needs_links(a)]
    print(f"Articles missing internal links: {len(missing)}")

    if not missing:
        print("All articles have internal links!")
        return

    total_added = 0
    for i, article in enumerate(missing):
        keyword = article.get("keyword", "?")
        print(f"\n[{i+1}/{len(missing)}] {keyword}")

        aj = article.get("article_json")
        if not aj:
            print("  No article_json, skipping")
            continue

        sections = extract_sections(aj)
        if not sections:
            print("  No sections, skipping")
            continue

        # Filter pool to exclude self
        pool = [l for l in LINK_POOL if keyword.lower() not in l["title"].lower()]

        print("  Calling Gemini...")
        embeddings = call_gemini(sections, pool)
        if not embeddings:
            print("  No embeddings returned")
            time.sleep(1.1)
            continue

        print(f"  Got {len(embeddings)} suggestions")
        modified, applied = apply_embeddings(aj, embeddings)
        print(f"  Applied {applied} links")

        if applied > 0:
            # Add pipeline report
            reports = modified.get("_pipeline_reports", {}) or {}
            reports["stage5_backfill"] = {
                "links_added": applied,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            modified["_pipeline_reports"] = reports

            update_article(article["id"], modified)
            print(f"  Saved to Supabase")
            total_added += applied

        time.sleep(1.1)  # Rate limit

    print(f"\nDone! Total links added: {total_added}")
    print("Note: article_html needs re-rendering. Use 'Reset HTML' in dashboard for each updated article.")


if __name__ == "__main__":
    main()
