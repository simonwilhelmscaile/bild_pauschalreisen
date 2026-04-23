# hreflang Implementation Recommendation for Beurer CMS (Makaria)

## What is hreflang?

hreflang tags tell Google which language/region version of a page exists, preventing duplicate content penalties when the same content appears on multiple domains or language paths.

## Our Pipeline Output

When articles are generated in multiple languages (DE + EN), our pipeline outputs hreflang link tags in the article HTML head:

```html
<link rel="alternate" hreflang="de" href="https://www.beurer.com/de/ratgeber/article-slug">
<link rel="alternate" hreflang="en" href="https://www.beurer.com/en/ratgeber/article-slug">
<link rel="alternate" hreflang="en-US" href="https://www.beurer-us.com/ratgeber/article-slug">
<link rel="alternate" hreflang="x-default" href="https://www.beurer.com/de/ratgeber/article-slug">
```

## CMS Implementation Options

### Option A: Preserve pipeline hreflang tags (recommended)
If Makaria can preserve the head content from our HTML output, the hreflang tags will be included automatically. No CMS-side changes needed.

### Option B: CMS-managed hreflang
If Makaria strips custom head tags, implement hreflang server-side:
1. Create a mapping table: article_slug to {de_url, en_url, us_url}
2. On each page render, inject hreflang tags from this mapping
3. Each language version must reference ALL other versions (including itself)

## Key Rules

1. **Self-referencing:** Each page must include an hreflang tag pointing to itself
2. **Bidirectional:** If page A links to page B, page B must link back to page A
3. **x-default:** Points to the fallback version (German, as primary market)
4. **Canonical:** Each language version uses its own URL as canonical (no cross-domain canonicals)
5. **URL format:** Use absolute URLs with protocol (https://)

## US Site

For the US subsidiary domain:
- Use hreflang="en-US" with the full US domain URL
- The US page should also include hreflang tags pointing to the DE and EN versions
- If content is identical to the EN version, still use separate hreflang values (en vs en-US)

## Testing

Verify implementation with:
- Google Search Console > International Targeting
- Ahrefs Site Audit > hreflang report
- Manual check: view page source and verify all hreflang tags are present and bidirectional
