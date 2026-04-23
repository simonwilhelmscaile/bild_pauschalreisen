# Beurer Article Requirements Checklist

**Purpose:** Complete list of all article quality requirements from Beurer client feedback, meeting notes, and developer briefings. Use this document to audit any generated article.

**Last updated:** 2026-04-13

---

## 1. Language & Tone

| # | Requirement | Source | Check |
|---|-------------|--------|-------|
| 1.1 | **Du-Form only** — use du/dir/dein/deine throughout. Never Sie/Ihnen/Ihr/Ihre as address form. Third-person "sie" (they) referring to objects is acceptable. | KW12 meeting, Mar 19 | Count of formal Sie address forms = 0 |
| 1.2 | **No healing promises** — never claim products "stop pain", "eliminate symptoms", "cure", or "heal". Use softened language: "kann unterstützen", "kann zur Linderung beitragen", "kann helfen" | KW12 meeting, Mar 19 | Search for banned phrases |
| 1.3 | **Medical context required** — add "in Absprache mit deinem Arzt", "als ergänzende Maßnahme" where appropriate | KW12 meeting, Mar 19 | Spot check |
| 1.4 | **Approachable but medically serious tone** — modeled on existing Beurer Ratgeber articles. Not too formal, not too casual. | Anika feedback, Mar 24 | Editorial judgment |
| 1.5 | **No AI filler phrases** — no "In today's rapidly evolving...", "Let's dive into...", "It's important to note...", "Key takeaways:" | Stage 3 quality check | Search for common AI phrases |
| 1.6 | **No repetitive content** across sections within the same article. Each fact, stat, or advice appears exactly once. | Anika feedback, Mar 24 | Read through for duplicates |
| 1.7 | **Banned words:** "Wundermittel", "garantiert heilen", "sofort schmerzfrei", "100% sicher", "Schmerzen stoppen", "Schmerzen beseitigen", "klinische Präzision", "genauso genau wie beim Arzt" | System prompt | Search for banned terms |

## 2. Product Rules

| # | Requirement | Source | Check |
|---|-------------|--------|-------|
| 2.1 | **Category isolation** — articles must only mention products from their own category | Apr 9 meeting (Anika) | See category rules below |
| 2.2 | **EM 50 / EM 55 are menstrual-only** — must NEVER appear in general TENS, back pain, or TENS comparison articles, not even with a disclaimer | Apr 9 meeting (Kevin) | Search for "EM 50", "EM 55" in non-menstrual articles |
| 2.3 | **No HealthManager Pro for TENS/EMS/infrarot** — HealthManager Pro is ONLY for blood pressure monitors (BM series) and scales | Apr 8 email (Anika) | Search for "HealthManager Pro" in non-BP articles |
| 2.4 | **No Insektenstichheiler** in TENS or blood pressure articles | Apr 9 meeting (Simon Schwoerer) | Search for "Insektenstichheiler", "BR 60", "BR 20" |
| 2.5 | **Product specs must be accurate** — program count, channels, electrodes must match product catalog | Apr 9 briefing | Cross-check mentioned specs against `product_catalog.json` |
| 2.6 | **Only products from product_catalog.json** — no invented products (BC 87, ME 90, BM 49, etc.) | Hallucination audit, Apr 9 | Search for SKU pattern `(BM\|BC\|EM\|IL)\s?\d{2,3}` and verify each against catalog |
| 2.7 | **No discontinued products** — e.g., EM 80 is no longer in the shop | Anika feedback, Mar 30 | Cross-check against catalog |

### Category Isolation Rules

```
Blood pressure articles:    ONLY BM*, BC* devices
TENS/Schmerztherapie:       EM* (non-menstrual) + IL* — CAN be combined
Menstruation articles:      ONLY EM 50, EM 55
Infrarot articles:          FOCUS on IL* products. May briefly reference EM* (1-2 sentences max)
NEVER cross:                No Insektenstichheiler (BR*) in TENS/BP articles
                            No HealthManager Pro for any non-BP device
                            No EM 50/55 outside menstrual context
                            No BM/BC devices in TENS/infrarot articles
                            No EM/IL devices in blood pressure articles
```

**Anika's exact words:** "Blutdruckmessgeräte können einfach nur Blutdruckmessgeräte bleiben. Da braucht kein anderes Gerät mit rein."

## 3. Sources

| # | Requirement | Source | Check |
|---|-------------|--------|-------|
| 3.1 | **2-3 external sources per article** | Anika email, Mar 24; Apr 2 briefing | Count sources |
| 3.2 | **All source URLs must be reachable** — no 404s, no homepage redirects | Anika feedback, Mar 24 | HTTP HEAD check each URL |
| 3.3 | **No social media sources** for medical topics — no Reddit, forums, Facebook, TikTok, Instagram, YouTube | Apr 2 briefing | Check source domains |
| 3.4 | **No beurer.com as external source** — the company's own site is not an independent reference | Pipeline rule | Check source URLs for "beurer.com" |
| 3.5 | **Preferred German sources:** Deutsche Hochdruckliga, Deutsche Herzstiftung, Apotheken Umschau, NetDoktor, AOK, BZgA, Mayo Clinic | System prompt | Check source quality |
| 3.6 | **Each source must have a description** explaining its specific contribution, not a generic placeholder | Pipeline rule | Check for "Source: X — relevant to Y" pattern |

## 4. Internal Links

| # | Requirement | Source | Check |
|---|-------------|--------|-------|
| 4.1 | **At least 3 internal beurer.com links per article** | Pipeline rule | Count `href="...beurer.com..."` |
| 4.2 | **Category page links preferred** over individual product links | Anika email, Mar 24; Apr 9 meeting | Check that category overview URL is included |
| 4.3 | **Category-scoped links only** — BP articles link to BP pages, TENS to TENS pages | Apr 9 meeting (Kevin, Anika) | Verify no cross-category product links |
| 4.4 | **No App Welt links** (`/app-welt/`) | Anika email, Mar 24 | Search for "app-welt" |
| 4.5 | **No Produktberater links** (`/produktberater`) | Anika email, Mar 24 | Search for "produktberater" |
| 4.6 | **Links spread across different sections** — not clustered in one paragraph | Stage 5 prompt | Visual check |

### Category Overview URLs

| Article Category | Default Internal Link |
|---|---|
| Schmerztherapie / TENS / EMS | `https://www.beurer.com/de/l/tens-ems/` |
| Blutdruck | `https://www.beurer.com/de/l/blutdruckmessgeraete/` |
| Menstruation | `https://www.beurer.com/de/l/em-50-menstrual-relax-pad/` |
| Infrarot | `https://www.beurer.com/de/l/tens-ems/` (no dedicated IR page exists) |

**Simon confirmed:** "Kategorieseiten können wir mit 100% Sicherheit gewährleisten."

## 5. Formatting

| # | Requirement | Source | Check |
|---|-------------|--------|-------|
| 5.1 | **Footnotes use letters** (A, B, C) not numbers (1, 2, 3) — numbers conflict with Beurer campaign numbering | Anika email, Mar 24 | Search for `<sup>\d+</sup>` (should be 0) |
| 5.2 | **"Das Wichtigste in Kürze"** label, not "Kurze Antwort" or "Kurz Antwort" | Anika email, Mar 24 | Search for label text |
| 5.3 | **No spacing errors around formatted text** — especially after punctuation before bold/linked text | Anika feedback, Mar 24 | Visual check |
| 5.4 | **No em-dashes** (—) — use comma, period, or regular hyphen instead | Stage 3 quality check | Search for `—` |
| 5.5 | **No garbled Unicode** — no zero-width characters, BOM markers | Hallucination audit | Search for `\u200b`, `\ufeff` etc. |

## 6. Images

| # | Requirement | Source | Check |
|---|-------------|--------|-------|
| 6.1 | **Hero image present** — lifestyle photograph matching the article theme | Pipeline rule | Check `image_01_url` is not empty |
| 6.2 | **No products/devices in hero image** — hero images are pure mood/lifestyle/atmosphere | Beurer Bildsprache guidelines | Visual inspection |
| 6.3 | **No text, logos, or graphic elements** in hero image | Pipeline rule | Visual inspection |
| 6.4 | **Match Beurer's Sep 2025 Bildsprache** — warm, approachable, realistic settings; not old white-background style | Anika, image briefing | Visual inspection |
| 6.5 | **Product cutout images** (inline) should match the products discussed in the article | Pipeline rule | Check `image_02_url`, `image_03_url` alt text |

## 7. Structure

| # | Requirement | Source | Check |
|---|-------------|--------|-------|
| 7.1 | **Word count ~2,000-3,500 words** | Pipeline default | Check word count |
| 7.2 | **4-6 content sections** with headings | Pipeline default | Count H2 headings |
| 7.3 | **4 PAA questions** (People Also Ask) | Pipeline default | Count PAA fields |
| 7.4 | **5-6 FAQ questions** | Pipeline default | Count FAQ fields |
| 7.5 | **3 key takeaways** | Pipeline default | Check key_takeaway fields |
| 7.6 | **Meta title** present and under 60 characters | Pipeline default | Check meta_title |
| 7.7 | **Meta description** present | Pipeline default | Check meta_description |
| 7.8 | **Direct Answer** present (for featured snippets) | Pipeline default | Check Direct_Answer field |

---

## Quick Audit Script

Run this against any article to check all automated requirements:

```python
import re

def audit_article(html, article_json, keyword):
    """Returns list of issues found. Empty list = all checks pass."""
    issues = []
    cat = detect_article_category(keyword)  # from blog.product_catalog
    
    # 1. Language
    sie = re.findall(r'\b(Sie|Ihnen|Ihrem|Ihrer|Ihres)\b', html)
    # Filter out object references (contextual check needed)
    if len(sie) > 5:
        issues.append(f"1.1 Sie-Form: {len(sie)} instances")
    
    for banned in ["Schmerzen stoppen", "Schmerzen beseitigen", "klinische Präzision", 
                    "genauso genau wie beim Arzt", "garantiert heilen", "sofort schmerzfrei"]:
        if banned.lower() in html.lower():
            issues.append(f"1.7 Banned phrase: {banned}")
    
    # 2. Products
    if cat == "pain_therapy":
        if re.search(r'HealthManager\s*Pro', html, re.IGNORECASE):
            issues.append("2.3 HealthManager Pro in pain_therapy article")
        if re.search(r'\bEM\s*50\b', html):
            issues.append("2.2 EM 50 in non-menstrual article")
        if re.search(r'\bEM\s*55\b', html):
            issues.append("2.2 EM 55 in non-menstrual article")
    
    if cat == "blood_pressure":
        for prefix in ["EM", "IL"]:
            if re.search(rf'\b{prefix}\s*\d{{2,3}}\b', html):
                issues.append(f"2.1 Cross-category: {prefix} product in BP article")
    
    # 3. Sources
    sources = article_json.get("Sources", [])
    if len(sources) < 2:
        issues.append(f"3.1 Only {len(sources)} sources (need 2-3)")
    for s in sources:
        url = (s.get("url") or "").lower()
        if "beurer.com" in url:
            issues.append(f"3.4 Beurer.com as external source: {url}")
        for domain in ["reddit.com", "facebook.com", "tiktok.com", "instagram.com"]:
            if domain in url:
                issues.append(f"3.3 Social media source: {url}")
    
    # 4. Internal links
    links = re.findall(r'href="[^"]*beurer\.com[^"]*"', html)
    if len(links) < 3:
        issues.append(f"4.1 Only {len(links)} internal links (need 3+)")
    if "produktberater" in html.lower():
        issues.append("4.5 Produktberater link found")
    if "app-welt" in html.lower():
        issues.append("4.4 App Welt link found")
    
    # 5. Formatting
    if re.search(r'<sup>\d+</sup>', html):
        issues.append("5.1 Numeric footnotes (should be letters)")
    if "Kurze Antwort" in html or "Kurz Antwort" in html:
        issues.append("5.2 Wrong label (should be Das Wichtigste in Kürze)")
    
    # 6. Images
    if not article_json.get("image_01_url"):
        issues.append("6.1 No hero image")
    
    # 7. Structure
    word_count = len(re.sub(r'<[^>]+>', '', html).split())
    if word_count < 2000:
        issues.append(f"7.1 Word count too low: {word_count}")
    
    return issues
```

---

## Revision History

| Date | Change | Source |
|------|--------|-------|
| Mar 19 | Du-Form, no healing promises | KW12 meeting |
| Mar 24 | Footnote letters, source limits, category links, App Welt/Produktberater ban, content repetition, "Das Wichtigste" label | Anika email |
| Apr 2 | 2-3 external sources max, no social media sources, internal links emphasis | Apr 2 briefing |
| Apr 8 | No HealthManager Pro for TENS/EMS/infrarot | Anika email |
| Apr 9 | Category isolation rules, EM 50/55 restriction, no Insektenstichheiler, accurate product specs, category page linking | Apr 9 meeting (Anika, Kevin, Simon) |
| Apr 13 | No beurer.com as external source, minimum 3 internal links, infrarot articles focus on IL products, hero image no-products rule | Pipeline improvements |
