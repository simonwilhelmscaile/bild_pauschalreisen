# BILD Pauschalreisen · Content Engine (Showcase Fork)

A rebrand of the SCAILE Social Listening / Content Engine platform, tailored for **BILD Pauschalreisen** (Axel Springer Group). This fork demonstrates how the content engine would look if deployed in-house for Bild's package-travel vertical.

> **Status**: Showcase / demo fork. Mock data is pre-baked into `bild_pauschalreisen_demo.html`, which is a fully self-contained standalone dashboard that runs from `file://` — no backend required.

## Live demo

Open `bild_pauschalreisen_demo.html` in a browser. All 11 tabs work with realistic Bild Pauschalreisen mock data:

| Tab | What it shows |
|---|---|
| **Executive Overview** | 2,170 mentions tracked, 61% positive sentiment, 25% Share of Voice vs. TUI/Check24/HolidayCheck |
| **Customer Journey** | Awareness → Consideration → Purchase funnel across 5 stages |
| **Deep Insights** | Top pains per destination category, user segments + avg. budgets |
| **Wettbewerber** | 10-brand competitor panel: TUI, Check24, HolidayCheck, weg.de, ab-in-den-urlaub, Expedia, Booking.com, FTI, DERTOUR, Lidl Reisen |
| **Alerts & Chancen** | Critical (Ägypten +312% WoW, Condor flight cuts), Opportunities (Malediven deals), 12 purchase-intent signals |
| **KI-Sichtbarkeit** | Peec-AI-style panel: Sichtbarkeit 68% / 124 Citations / Rang #3, breakdown by ChatGPT / Perplexity / Gemini / Claude / AI Overview |
| **Content Planung** | **⭐ Hero tab** — full pipeline of 15 ranked article opportunities + 9 fully "generated" articles (Mallorca, Türkei, Ägypten, Kanaren, Malediven, Dubai, Rom, MSC-Kreuzfahrt, Thailand, Paris, Griechenland, Punta Cana, Ferienflieger…) |
| **Q&A & Brückenmomente** | 4 high-engagement community posts ready for Bild-angle content |
| **Nachrichten** | 7 travel-industry news items (TUI Rekord, Check24 Urlaubsreport, AA Ägypten, ChatGPT/Perplexity citations of Bild) |
| **Search Console** | GSC placeholder (expects live connection) |
| **Kundendienst-Insights** | Support-case heatmap across 10 destinations, alerts for Ägypten, Mallorca, Türkei |

## Branding — Bild CI/CD

Extracted via Firecrawl (`www.bild.de`):

- **Primary color**: `#DD0000` (Bild red)
- **Accent**: `#FF0F0F` / `#FF3030`
- **Logo**: Red square with white "BILD" lettering (inline SVG, no external dependency)
- **Fonts**: Gotham XNarrow / Avenir Next Condensed / system sans (the template uses Plus Jakarta Sans + DM Sans as web-safe substitutes)
- **Tone**: bold, high-energy, German-speaking news readership

## Travel categories

The template's original health-device keys are mapped onto travel clusters:

| Original key | Bild Pauschalreisen cluster |
|---|---|
| `blood_pressure` | Strand & All-Inclusive (Mallorca, Türkei, Griechenland, Ägypten, Kanaren) |
| `pain_tens` | Städtereisen & Kultur (Rom, Paris, Barcelona, Wien, Lissabon) |
| `infrarot` | Fernreisen & Exotik (Malediven, Dubai, Thailand, Bali, Karibik) |
| `menstrual` | Kreuzfahrten & Luxus (Mittelmeer, Karibik, Nordland, Donau) |

(Keys are preserved so the full analytics pipeline remains wired end-to-end; only human-facing labels were rebranded.)

## Architecture (unchanged from parent fork)

The underlying platform is preserved end-to-end:

```
Python backend (FastAPI) ─┐
                          ├─► Supabase (PostgreSQL) ─► Next.js dashboard on Vercel
GitHub Actions (weekly) ──┘                              └─► Live (DB) or baked (mock) modes
```

- `blog/` — content engine (article generation pipeline)
- `classification/` — multi-stage LLM classifiers for social-item → opportunity
- `crawlers/` — Reddit, Firecrawl, Apify, Exa, Serper runners
- `dashboard/` — Next.js frontend + single-file HTML template (~13k lines)
- `dashboard/mock_data/build_demo.py` — **the demo baker** that injects Bild Pauschalreisen mock data into the template
- `db/` + `migrations/` — Supabase schema
- `routes/` — FastAPI endpoints

## Rebuilding the demo

```bash
python3 dashboard/mock_data/build_demo.py
# → writes bild_pauschalreisen_demo.html
```

Preview all tabs as PNGs:

```bash
python3 dashboard/mock_data/screenshot.py
# → writes previews/*.png
```

## Source fork

This is a fork of [simonwilhelmscaile/axel_springer](https://github.com/simonwilhelmscaile/axel_springer), which itself forks [scailetech/social_listening_service](https://github.com/scailetech/social_listening_service).

---

© 2026 SCAILE — Showcase built for the 22.04.2026 Axel Springer meeting.
