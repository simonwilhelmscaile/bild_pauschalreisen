"""
Backfill internal links for blog articles via the dashboard API.
Fetches articles, uses Gemini to add links to article_html, saves back via PATCH.
"""
import json
import re
import time
import requests

DASHBOARD_URL = "https://social-listening-service.vercel.app"
DASHBOARD_PASSWORD = "beurer2026"
GEMINI_KEY = "AIzaSyBdwLCjjzdCIOZBiia3E4YVo1wbS0SohUI"

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

session = requests.Session()
session.cookies.set("dashboard_token", DASHBOARD_PASSWORD)


def fetch_articles():
    """Fetch all articles from dashboard API."""
    r = session.get(f"{DASHBOARD_URL}/api/blog-article")
    r.raise_for_status()
    data = r.json()
    return data.get("articles", data) if isinstance(data, dict) else data


def needs_links(article):
    """Check if article has no internal beurer links."""
    html = article.get("article_html") or ""
    return "beurer.com" not in html


def extract_text_sections(html):
    """Extract readable text sections from article HTML for Gemini."""
    # Find paragraph and list content
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    lists = re.findall(r'<li[^>]*>(.*?)</li>', html, re.DOTALL)
    sections = paragraphs + lists
    # Strip inner HTML tags but keep text
    clean = []
    for s in sections:
        text = re.sub(r'<[^>]+>', '', s).strip()
        if len(text) > 30:
            clean.append(text)
    return clean


def call_gemini(text_sections, pool, keyword):
    """Ask Gemini to suggest link placements in article text."""
    links_text = "\n".join(f"- {l['title']}: {l['url']}" for l in pool)
    sections_text = "\n\n".join(f"[{i+1}] {s}" for i, s in enumerate(text_sections[:20]))

    prompt = f"""You are an SEO expert working on a German health article about "{keyword}".

Below are text paragraphs from the article and available internal links. Your job is to find 3-5 exact phrases in the paragraphs that should become internal links.

AVAILABLE LINKS:
{links_text}

ARTICLE PARAGRAPHS:
{sections_text}

RULES:
- Find 3-5 EXACT phrases (copy-paste from paragraphs above) that relate to available links
- Each phrase should be 2-5 words, a natural anchor text
- Spread across different paragraphs
- Don't link the same URL twice
- The "find" text MUST appear EXACTLY as written in the paragraphs (case-sensitive match)
- Only use URLs from the AVAILABLE LINKS list above

Return a JSON array:
[{{"find": "exact phrase from paragraph", "url": "https://www.beurer.com/de/...", "anchor": "exact phrase from paragraph"}}]"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
    }
    r = requests.post(url, json=body)
    r.raise_for_status()
    data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        print(f"  Parse error: {text[:200]}")
        return []


def is_protected(html, pos):
    """Check if position is inside a protected tag."""
    before = html[:pos].lower()
    for tag in PROTECTED_TAGS:
        last_open = before.rfind(f"<{tag}")
        if last_open == -1:
            continue
        char_idx = last_open + len(tag) + 1
        if char_idx < len(before):
            ch = before[char_idx]
            if ch not in (">", " ", "\t", "\n", "/"):
                continue
        last_close = before.rfind(f"</{tag}>")
        if last_open > last_close:
            return True
    return False


def apply_links_to_html(html, suggestions):
    """Apply link suggestions directly to article HTML."""
    modified = html
    applied = 0
    used_urls = set()

    for s in suggestions:
        find = s.get("find") or s.get("anchor", "")
        url = s.get("url", "")
        anchor = s.get("anchor", find)

        if not find or not url or len(find) < 3:
            continue

        # Validate URL
        url_norm = url.rstrip("/").lower()
        if not any(v.rstrip("/").lower() == url_norm for v in VALID_URLS):
            continue
        if url_norm in used_urls:
            continue

        # Find in HTML
        pos = modified.find(find)
        if pos == -1:
            # Case-insensitive
            idx = modified.lower().find(find.lower())
            if idx == -1:
                continue
            find = modified[idx:idx + len(find)]
            pos = idx

        if is_protected(modified, pos):
            continue

        replacement = f'<a href="{url}">{anchor}</a>'
        modified = modified[:pos] + replacement + modified[pos + len(find):]
        used_urls.add(url_norm)
        applied += 1

    return modified, applied


def save_html(article_id, html):
    """Save updated HTML via dashboard PATCH API."""
    r = session.patch(
        f"{DASHBOARD_URL}/api/blog-article",
        json={"article_id": article_id, "action": "save_html", "article_html": html},
    )
    r.raise_for_status()
    return r.json()


def main():
    print("Fetching articles from dashboard...")
    articles = fetch_articles()
    print(f"Total articles: {len(articles)}")

    missing = [a for a in articles if needs_links(a) and a.get("article_html")]
    print(f"Missing internal links: {len(missing)}")

    if not missing:
        print("All articles have internal links!")
        return

    total = 0
    for i, art in enumerate(missing):
        kw = art.get("keyword", "?")
        aid = art["id"]
        print(f"\n[{i+1}/{len(missing)}] {kw}")

        html = art["article_html"]
        sections = extract_text_sections(html)
        if not sections:
            print("  No text sections found")
            continue

        pool = [l for l in LINK_POOL if kw.lower() not in l["title"].lower()]

        print(f"  Calling Gemini ({len(sections)} sections, {len(pool)} links)...")
        suggestions = call_gemini(sections, pool, kw)
        if not suggestions:
            print("  No suggestions")
            time.sleep(1.1)
            continue

        print(f"  Got {len(suggestions)} suggestions")
        new_html, applied = apply_links_to_html(html, suggestions)
        print(f"  Applied {applied} links")

        if applied > 0:
            save_html(aid, new_html)
            print(f"  Saved!")
            total += applied

        time.sleep(1.1)

    print(f"\nDone! Total links added: {total}")


if __name__ == "__main__":
    main()
