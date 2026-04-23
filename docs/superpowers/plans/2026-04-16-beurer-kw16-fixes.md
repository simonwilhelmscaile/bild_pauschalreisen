# Beurer KW16 Feedback Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply targeted patches to the 11 client-facing Beurer blog articles (ToC truncation, `/l/` landing-page links, citation order, overview-page external sources) without regenerating content, using a re-render pass to propagate a ToC renderer fix into the stored `article_html`.

**Architecture:** Two-part delivery — (1) a one-line renderer fix in `dashboard/lib/html-renderer.ts`, and (2) three pure TypeScript mutation helpers composed by a `dashboard/scripts/apply-kw16-fixes.ts` orchestrator that reads a triaged CSV produced by a Python audit script, applies mutations, re-renders `article_html` via the dashboard's own renderer, and appends a single snapshot + feedback entry to `feedback_history` per mutated article. See spec: `docs/superpowers/specs/2026-04-16-beurer-kw16-fixes-design.md`.

**Tech Stack:** TypeScript (Node runtime via `tsx`), Next.js 15 dashboard, `@supabase/supabase-js`, Python 3.13 + Firecrawl for the audit, vitest for TS unit tests, pytest not used (matches existing repo convention — smoke tests only for Python).

---

## File Structure

**Create:**
- `dashboard/lib/kw16-fixes/landing-page-links.ts` — pure helper: strip `<a>` tags wrapping `beurer.com/.../l/...` URLs
- `dashboard/lib/kw16-fixes/citations.ts` — pure helper: two-phase rewrite of `<sup>A/B/C>` letters + reorder `Sources[]` to match first-appearance order
- `dashboard/lib/kw16-fixes/external-sources.ts` — pure helper: drop entries from `Sources[]` by URL and remove matching inline `<sup>` tags
- `dashboard/lib/kw16-fixes/__tests__/landing-page-links.test.ts` — vitest unit tests
- `dashboard/lib/kw16-fixes/__tests__/citations.test.ts` — vitest unit tests
- `dashboard/lib/kw16-fixes/__tests__/external-sources.test.ts` — vitest unit tests
- `dashboard/lib/word-count.ts` — shared helper (exports `countWordsInHtml` currently private in `article-generator.ts`)
- `dashboard/scripts/apply-kw16-fixes.ts` — orchestrator (CLI, executed via `tsx`)
- `scripts/audit_external_sources.py` — Python read-only audit producing a CSV
- `scripts/rollback_kw16_batch.py` — Python one-off to undo the batch if needed

**Modify:**
- `dashboard/lib/html-renderer.ts:251-265` — remove 8-word ToC cap
- `dashboard/lib/article-generator.ts:356-359` — re-export `countWordsInHtml` from `lib/word-count.ts` (single source of truth)
- `dashboard/package.json` — add `tsx` dev-dep, `vitest` dev-dep, `"test"` and `"fix:kw16"` scripts
- `dashboard/vitest.config.ts` — new file; minimal config

**Not modified:** existing Python crawler code, `blog/` pipeline, Supabase schema.

---

## Task 1: Fix ToC 8-word truncation in renderer

**Files:**
- Modify: `dashboard/lib/html-renderer.ts:251-265`

- [ ] **Step 1: Apply the one-line change**

Open `dashboard/lib/html-renderer.ts` and replace the TOC block (lines 251-265):

```ts
  // TOC
  const tocItems: string[] = [];
  for (let i = 1; i <= 9; i++) {
    const title = article[`section_${String(i).padStart(2, "0")}_title`] || "";
    if (title) {
      const cleanTitle = stripHtml(title);
      tocItems.push(`<li><a href="#section-${i}">${esc(cleanTitle)}</a></li>`);
    }
  }
  const tocHtml = tocItems.length
    ? `<nav class="toc"><h2>${L(language, 'toc')}</h2><ol>${tocItems.join("")}</ol></nav>`
    : "";
```

(Removes `const words = cleanTitle.split(/\s+/).slice(0, 8)`, the `shortTitle` construction, and the `" ..."` suffix. Uses the full `cleanTitle`.)

- [ ] **Step 2: Smoke-test locally**

```bash
cd dashboard
npm run dev
```

Open any article at `http://localhost:3000` via the content tab. Find a section title longer than 8 words (e.g. article #11 "Reizstromgeräte im Vergleich…"). Verify the ToC entry renders the full title, no trailing "…".

Expected: full title visible in ToC; no truncation; no visual overflow in a 1280px-wide viewport.

- [ ] **Step 3: Commit**

```bash
git add dashboard/lib/html-renderer.ts
git commit -m "fix(toc): render full section titles, remove 8-word cap

Beurer KW16 feedback — ToC sentences were truncated mid-phrase
due to an 8-word cap in the renderer. Removed the cap so full
titles render verbatim. Applies only to future renders; the
orchestrator in a later commit will re-render stored article_html.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Set up vitest test infrastructure in the dashboard

**Files:**
- Modify: `dashboard/package.json`
- Create: `dashboard/vitest.config.ts`
- Create: `dashboard/lib/kw16-fixes/__tests__/smoke.test.ts`

- [ ] **Step 1: Install vitest**

```bash
cd dashboard
npm install --save-dev vitest @vitest/ui tsx
```

- [ ] **Step 2: Add test scripts to `dashboard/package.json`**

In the `"scripts"` block, add:

```json
"test": "vitest run",
"test:watch": "vitest"
```

Final `"scripts"` block should look like (preserving existing entries):

```json
"scripts": {
  "copy-template": "node -e \"...existing...\"",
  "dev": "npm run copy-template && next dev",
  "build": "npm run copy-template && next build",
  "start": "next start",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

- [ ] **Step 3: Create `dashboard/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    include: ["lib/**/__tests__/**/*.test.ts"],
    environment: "node",
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./"),
    },
  },
});
```

- [ ] **Step 4: Write a smoke test to verify wiring**

Create `dashboard/lib/kw16-fixes/__tests__/smoke.test.ts`:

```ts
import { describe, it, expect } from "vitest";

describe("vitest wiring", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 5: Run the smoke test**

```bash
cd dashboard
npm test
```

Expected: 1 test passes. Output includes `✓ vitest wiring > runs`.

- [ ] **Step 6: Commit**

```bash
git add dashboard/package.json dashboard/package-lock.json dashboard/vitest.config.ts dashboard/lib/kw16-fixes/__tests__/smoke.test.ts
git commit -m "chore: add vitest + tsx dev dependencies for kw16-fixes

Introduces minimal test infrastructure for upcoming pure
TypeScript mutation helpers. tsx is also required by the
orchestrator script added in a later commit.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Landing-page-link stripper helper (TDD)

**Files:**
- Create: `dashboard/lib/kw16-fixes/landing-page-links.ts`
- Create: `dashboard/lib/kw16-fixes/__tests__/landing-page-links.test.ts`

**Context:** Stage 5 writes internal links as inline `<a>` tags inside content fields (`Intro`, `Direct_Answer`, `TLDR`, `section_NN_content`, `faq_NN_answer`, `paa_NN_answer`). We must strip only beurer.com landing-page URLs (containing `/l/`) while keeping the anchor text. Third-party URLs that happen to contain `/l/` must not be touched.

- [ ] **Step 1: Write the failing tests**

Create `dashboard/lib/kw16-fixes/__tests__/landing-page-links.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { stripLandingPageLinks, CONTENT_FIELDS } from "../landing-page-links";

describe("stripLandingPageLinks", () => {
  it("strips beurer.com /l/ links and keeps the anchor text", () => {
    const article = {
      section_01_content: 'Mehr zu <a href="https://www.beurer.com/de/l/waerme/">Wärmeprodukten</a> findest du hier.',
    };
    const result = stripLandingPageLinks(article);
    expect(result.articleJson.section_01_content).toBe(
      "Mehr zu Wärmeprodukten findest du hier."
    );
    expect(result.fixesApplied).toBe(1);
    expect(result.affectedFields).toEqual(["section_01_content"]);
  });

  it("leaves non-/l/ beurer.com links untouched", () => {
    const article = {
      section_01_content: '<a href="https://www.beurer.com/de/p/bm-27/">BM 27</a> ist empfehlenswert.',
    };
    const result = stripLandingPageLinks(article);
    expect(result.articleJson.section_01_content).toBe(article.section_01_content);
    expect(result.fixesApplied).toBe(0);
  });

  it("leaves third-party /l/ URLs untouched", () => {
    const article = {
      Intro: 'Siehe <a href="https://example.com/l/page/">Beispiel</a>.',
    };
    const result = stripLandingPageLinks(article);
    expect(result.articleJson.Intro).toBe(article.Intro);
    expect(result.fixesApplied).toBe(0);
  });

  it("strips across multiple fields and counts each", () => {
    const article = {
      Intro: '<a href="https://beurer.com/de/l/a/">A</a>',
      section_01_content: '<a href="https://www.beurer.com/de/l/b/">B</a>',
      section_02_content: 'no links here',
    };
    const result = stripLandingPageLinks(article);
    expect(result.articleJson.Intro).toBe("A");
    expect(result.articleJson.section_01_content).toBe("B");
    expect(result.articleJson.section_02_content).toBe("no links here");
    expect(result.fixesApplied).toBe(2);
    expect(result.affectedFields.sort()).toEqual(["Intro", "section_01_content"]);
  });

  it("preserves nested HTML inside the anchor text", () => {
    const article = {
      Intro: '<a href="https://www.beurer.com/de/l/waerme/"><strong>Wärme</strong></a>',
    };
    const result = stripLandingPageLinks(article);
    expect(result.articleJson.Intro).toBe("<strong>Wärme</strong>");
    expect(result.fixesApplied).toBe(1);
  });

  it("exposes the standard content-field list", () => {
    expect(CONTENT_FIELDS).toContain("Intro");
    expect(CONTENT_FIELDS).toContain("Direct_Answer");
    expect(CONTENT_FIELDS).toContain("TLDR");
    expect(CONTENT_FIELDS).toContain("section_01_content");
    expect(CONTENT_FIELDS).toContain("section_09_content");
    expect(CONTENT_FIELDS).toContain("faq_06_answer");
    expect(CONTENT_FIELDS).toContain("paa_04_answer");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd dashboard
npm test -- landing-page-links
```

Expected: all tests fail with "Cannot find module '../landing-page-links'".

- [ ] **Step 3: Implement the helper**

Create `dashboard/lib/kw16-fixes/landing-page-links.ts`:

```ts
/**
 * Strip <a> tags whose href points to a beurer.com landing page (/l/ path).
 * Keeps the inner HTML/text. Scoped to beurer.com hosts only.
 *
 * See spec: docs/superpowers/specs/2026-04-16-beurer-kw16-fixes-design.md § Item 2.
 */

export const CONTENT_FIELDS = [
  "Intro",
  "Direct_Answer",
  "TLDR",
  ...Array.from({ length: 9 }, (_, i) => `section_${String(i + 1).padStart(2, "0")}_content`),
  ...Array.from({ length: 6 }, (_, i) => `faq_${String(i + 1).padStart(2, "0")}_answer`),
  ...Array.from({ length: 4 }, (_, i) => `paa_${String(i + 1).padStart(2, "0")}_answer`),
];

const BEURER_LANDING_LINK = /<a\s+[^>]*href="[^"]*?\/\/[^"]*?beurer\.com[^"]*?\/l\/[^"]*?"[^>]*>([\s\S]*?)<\/a>/gi;

export interface StripResult {
  articleJson: Record<string, any>;
  fixesApplied: number;
  affectedFields: string[];
}

export function stripLandingPageLinks(articleJson: Record<string, any>): StripResult {
  const out = { ...articleJson };
  let fixesApplied = 0;
  const affectedFields: string[] = [];

  for (const field of CONTENT_FIELDS) {
    const val = out[field];
    if (typeof val !== "string" || !val.includes("<a")) continue;

    let localFixes = 0;
    const replaced = val.replace(BEURER_LANDING_LINK, (_match, inner) => {
      localFixes += 1;
      return inner;
    });

    if (localFixes > 0) {
      out[field] = replaced;
      fixesApplied += localFixes;
      affectedFields.push(field);
    }
  }

  return { articleJson: out, fixesApplied, affectedFields };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd dashboard
npm test -- landing-page-links
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/kw16-fixes/landing-page-links.ts dashboard/lib/kw16-fixes/__tests__/landing-page-links.test.ts
git commit -m "feat(kw16): add landing-page-link stripper helper

Pure helper that removes <a> wrappers around beurer.com /l/
URLs and keeps the inner text. Scoped to beurer.com hosts so
third-party links containing /l/ are untouched.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Citation re-alignment helper (TDD)

**Files:**
- Create: `dashboard/lib/kw16-fixes/citations.ts`
- Create: `dashboard/lib/kw16-fixes/__tests__/citations.test.ts`

**Context:** The renderer shows `Sources[]` as `<ol type="A">` so index 0 = letter A. Stage 5 places inline `<sup>X</sup>` letters that may not match the `Sources[]` order (Beurer complaint: "we start at B and have A second"). Re-align so the first-encountered `<sup>` in the canonical reading order (`Direct_Answer` → `Intro` → `section_01..09_content`) is A, and `Sources[]` matches. Uses a two-phase rewrite via placeholder tokens to avoid cascade bugs (e.g. A→B then B→A collapsing to A→A).

- [ ] **Step 1: Write the failing tests**

Create `dashboard/lib/kw16-fixes/__tests__/citations.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { realignCitations } from "../citations";

describe("realignCitations", () => {
  it("remaps B->A and A->B when B appears first", () => {
    const article = {
      Direct_Answer: "Blood pressure monitors<sup>B</sup>.",
      Intro: "Some studies<sup>A</sup> agree.",
      Sources: [
        { title: "Source A-orig", url: "https://a.example" },
        { title: "Source B-orig", url: "https://b.example" },
      ],
    };
    const result = realignCitations(article);
    expect(result.changed).toBe(true);
    expect(result.articleJson.Direct_Answer).toBe("Blood pressure monitors<sup>A</sup>.");
    expect(result.articleJson.Intro).toBe("Some studies<sup>B</sup> agree.");
    // Sources reordered so first-encountered B-orig now at index 0 (letter A)
    expect(result.articleJson.Sources[0].title).toBe("Source B-orig");
    expect(result.articleJson.Sources[1].title).toBe("Source A-orig");
  });

  it("is a no-op when order is already A, B, C", () => {
    const article = {
      Intro: "X<sup>A</sup> and Y<sup>B</sup> and Z<sup>C</sup>.",
      Sources: [
        { title: "S1", url: "https://1.example" },
        { title: "S2", url: "https://2.example" },
        { title: "S3", url: "https://3.example" },
      ],
    };
    const result = realignCitations(article);
    expect(result.changed).toBe(false);
    expect(result.articleJson.Sources).toEqual(article.Sources);
  });

  it("handles repeated citations (same letter used twice)", () => {
    const article = {
      Intro: "One<sup>B</sup>, two<sup>A</sup>, three<sup>B</sup>.",
      Sources: [
        { title: "A-orig", url: "https://a.example" },
        { title: "B-orig", url: "https://b.example" },
      ],
    };
    const result = realignCitations(article);
    expect(result.articleJson.Intro).toBe("One<sup>A</sup>, two<sup>B</sup>, three<sup>A</sup>.");
    expect(result.articleJson.Sources[0].title).toBe("B-orig");
    expect(result.articleJson.Sources[1].title).toBe("A-orig");
  });

  it("drops orphan <sup>X</sup> with no matching Sources entry and warns", () => {
    const article = {
      Intro: "Known<sup>A</sup> and orphan<sup>C</sup>.",
      Sources: [{ title: "Only one", url: "https://1.example" }],
    };
    const result = realignCitations(article);
    expect(result.articleJson.Intro).toBe("Known<sup>A</sup> and orphan.");
    expect(result.droppedOrphanSups).toEqual(["C"]);
    expect(result.warnings.length).toBeGreaterThanOrEqual(1);
  });

  it("keeps uncited Source entries and places them after cited ones", () => {
    const article = {
      Intro: "Only<sup>A</sup> appears.",
      Sources: [
        { title: "Cited", url: "https://cited.example" },
        { title: "Uncited", url: "https://uncited.example" },
      ],
    };
    const result = realignCitations(article);
    expect(result.articleJson.Sources[0].title).toBe("Cited");
    expect(result.articleJson.Sources[1].title).toBe("Uncited");
    // No warning about the uncited one — not an error, just uncited
  });

  it("returns unchanged when no <sup> tags present", () => {
    const article = {
      Intro: "No citations here.",
      Sources: [{ title: "S", url: "https://x.example" }],
    };
    const result = realignCitations(article);
    expect(result.changed).toBe(false);
  });

  it("walks sections in numerical order for first-appearance", () => {
    const article = {
      Direct_Answer: "",
      Intro: "",
      section_01_content: "First<sup>C</sup>",
      section_02_content: "Second<sup>A</sup>",
      section_03_content: "Third<sup>B</sup>",
      Sources: [
        { title: "S1", url: "https://1.example" },
        { title: "S2", url: "https://2.example" },
        { title: "S3", url: "https://3.example" },
      ],
    };
    const result = realignCitations(article);
    // C was first → becomes A
    expect(result.articleJson.section_01_content).toBe("First<sup>A</sup>");
    expect(result.articleJson.section_02_content).toBe("Second<sup>B</sup>");
    expect(result.articleJson.section_03_content).toBe("Third<sup>C</sup>");
    // Sources reordered: old index 2 (C) -> new 0, old 0 (A) -> new 1, old 1 (B) -> new 2
    expect(result.articleJson.Sources[0].title).toBe("S3");
    expect(result.articleJson.Sources[1].title).toBe("S1");
    expect(result.articleJson.Sources[2].title).toBe("S2");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd dashboard
npm test -- citations
```

Expected: all tests fail with "Cannot find module '../citations'".

- [ ] **Step 3: Implement the helper**

Create `dashboard/lib/kw16-fixes/citations.ts`:

```ts
/**
 * Realign <sup>A/B/C/…</sup> letters in article content to first-appearance
 * reading order and reorder Sources[] to match.
 *
 * Canonical reading order: Direct_Answer → Intro → section_01..09_content.
 * FAQ/PAA answers are esc()'d at render time so no citations live there.
 *
 * Uses two-phase placeholder rewrite to avoid cascade bugs.
 *
 * See spec: docs/superpowers/specs/2026-04-16-beurer-kw16-fixes-design.md § Item 3.
 */

const READING_ORDER_FIELDS = [
  "Direct_Answer",
  "Intro",
  ...Array.from({ length: 9 }, (_, i) => `section_${String(i + 1).padStart(2, "0")}_content`),
];

const SUP_RE = /<sup>([A-Z])<\/sup>/g;

export interface RealignResult {
  articleJson: Record<string, any>;
  changed: boolean;
  remap: Record<string, string> | null;
  droppedOrphanSups: string[];
  warnings: Array<{ message: string }>;
}

function letterToIndex(letter: string): number {
  return letter.charCodeAt(0) - 65;
}
function indexToLetter(index: number): string {
  return String.fromCharCode(65 + index);
}

export function realignCitations(articleJson: Record<string, any>): RealignResult {
  const out = { ...articleJson };
  const sources: any[] = Array.isArray(out.Sources) ? [...out.Sources] : [];
  const warnings: Array<{ message: string }> = [];

  // 1. Find first-appearance order of letters across the reading order
  const firstAppearance: string[] = [];
  const seen = new Set<string>();
  for (const field of READING_ORDER_FIELDS) {
    const val = out[field];
    if (typeof val !== "string") continue;
    for (const match of val.matchAll(SUP_RE)) {
      const letter = match[1];
      if (!seen.has(letter)) {
        seen.add(letter);
        firstAppearance.push(letter);
      }
    }
  }

  // 2. Identify orphans (cited letters whose source index doesn't exist)
  const droppedOrphanSups: string[] = [];
  const citedValid: string[] = [];
  for (const letter of firstAppearance) {
    if (letterToIndex(letter) >= sources.length) {
      droppedOrphanSups.push(letter);
      warnings.push({ message: `Dropping orphan <sup>${letter}</sup> — no matching Sources[${letterToIndex(letter)}] entry` });
    } else {
      citedValid.push(letter);
    }
  }

  // 3. If nothing to do, return unchanged
  if (firstAppearance.length === 0) {
    return { articleJson: out, changed: false, remap: null, droppedOrphanSups: [], warnings: [] };
  }
  const alreadyAligned =
    droppedOrphanSups.length === 0 &&
    citedValid.every((l, i) => l === indexToLetter(i));
  if (alreadyAligned) {
    return { articleJson: out, changed: false, remap: null, droppedOrphanSups: [], warnings: [] };
  }

  // 4. Build remap: each valid cited letter → its new letter (by first-appearance order)
  const remap: Record<string, string> = {};
  citedValid.forEach((letter, i) => {
    remap[letter] = indexToLetter(i);
  });

  // 5. Two-phase rewrite of every content field (including FAQ/PAA, in case any slipped through — safe no-op if not)
  const allFields = [
    ...READING_ORDER_FIELDS,
    ...Array.from({ length: 6 }, (_, i) => `faq_${String(i + 1).padStart(2, "0")}_answer`),
    ...Array.from({ length: 4 }, (_, i) => `paa_${String(i + 1).padStart(2, "0")}_answer`),
  ];

  for (const field of allFields) {
    const val = out[field];
    if (typeof val !== "string" || !val.includes("<sup>")) continue;

    // Phase 1: replace <sup>X</sup> with <sup>__X__</sup> placeholder, dropping orphans
    let phase1 = val.replace(SUP_RE, (_m, letter) => {
      if (droppedOrphanSups.includes(letter)) return ""; // drop orphan
      return `<sup>__${letter}__</sup>`;
    });
    // Phase 2: swap placeholders to final letters
    const phase2 = phase1.replace(/<sup>__([A-Z])__<\/sup>/g, (_m, letter) => {
      const newLetter = remap[letter];
      return newLetter ? `<sup>${newLetter}</sup>` : "";
    });
    out[field] = phase2;
  }

  // 6. Rebuild Sources[] — cited valid letters first (in first-appearance order), uncited entries appended
  const citedOldIndices = new Set(citedValid.map(letterToIndex));
  const newSources: any[] = [];
  for (const letter of citedValid) {
    newSources.push(sources[letterToIndex(letter)]);
  }
  sources.forEach((src, idx) => {
    if (!citedOldIndices.has(idx)) newSources.push(src);
  });
  out.Sources = newSources;

  return { articleJson: out, changed: true, remap, droppedOrphanSups, warnings };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd dashboard
npm test -- citations
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/kw16-fixes/citations.ts dashboard/lib/kw16-fixes/__tests__/citations.test.ts
git commit -m "feat(kw16): add citation realignment helper

Two-phase placeholder rewrite remaps <sup>X</sup> letters to
first-appearance order and reorders Sources[] to match. Drops
orphan <sup> tags whose source index is out of range; keeps
uncited Source entries after the cited ones.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: External-source drop helper (TDD)

**Files:**
- Create: `dashboard/lib/kw16-fixes/external-sources.ts`
- Create: `dashboard/lib/kw16-fixes/__tests__/external-sources.test.ts`

**Context:** Given a set of URLs to drop (from the triaged audit CSV), remove matching entries from `Sources[]` and strip every `<sup>LETTER</sup>` that referenced them from the content. Does NOT renumber — that's Task 4's job, run after this one.

- [ ] **Step 1: Write the failing tests**

Create `dashboard/lib/kw16-fixes/__tests__/external-sources.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { dropExternalSources } from "../external-sources";

describe("dropExternalSources", () => {
  it("drops matching source and removes its <sup> from content", () => {
    const article = {
      Intro: "First<sup>A</sup>, second<sup>B</sup>, third<sup>C</sup>.",
      Sources: [
        { title: "A-src", url: "https://a.example" },
        { title: "B-src", url: "https://b.example" },
        { title: "C-src", url: "https://c.example" },
      ],
    };
    const drops = new Set(["https://b.example"]);
    const result = dropExternalSources(article, drops);
    expect(result.articleJson.Sources).toHaveLength(2);
    expect(result.articleJson.Sources.map((s: any) => s.title)).toEqual(["A-src", "C-src"]);
    expect(result.articleJson.Intro).toBe("First<sup>A</sup>, second, third<sup>C</sup>.");
    expect(result.droppedSources).toEqual([{ letter: "B", url: "https://b.example", title: "B-src" }]);
  });

  it("removes all repeated <sup>B</sup> occurrences", () => {
    const article = {
      Intro: "<sup>B</sup> here and <sup>B</sup> again.",
      section_01_content: "section: <sup>B</sup>",
      Sources: [
        { title: "A", url: "https://a.example" },
        { title: "B", url: "https://b.example" },
      ],
    };
    const result = dropExternalSources(article, new Set(["https://b.example"]));
    expect(result.articleJson.Intro).toBe(" here and  again.");
    expect(result.articleJson.section_01_content).toBe("section: ");
  });

  it("warns when a drop URL is not found in Sources[]", () => {
    const article = {
      Intro: "Nothing to drop.",
      Sources: [{ title: "A", url: "https://a.example" }],
    };
    const result = dropExternalSources(article, new Set(["https://missing.example"]));
    expect(result.articleJson.Sources).toHaveLength(1);
    expect(result.droppedSources).toEqual([]);
    expect(result.warnings.length).toBe(1);
  });

  it("normalises trailing slash when matching URLs", () => {
    const article = {
      Intro: "<sup>A</sup>",
      Sources: [{ title: "A", url: "https://a.example/path/" }],
    };
    const result = dropExternalSources(article, new Set(["https://a.example/path"]));
    expect(result.articleJson.Sources).toHaveLength(0);
    expect(result.droppedSources[0].url).toBe("https://a.example/path/");
  });

  it("handles empty drops set", () => {
    const article = {
      Intro: "<sup>A</sup>",
      Sources: [{ title: "A", url: "https://a.example" }],
    };
    const result = dropExternalSources(article, new Set());
    expect(result.articleJson).toEqual(article);
    expect(result.droppedSources).toEqual([]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd dashboard
npm test -- external-sources
```

Expected: all tests fail with "Cannot find module '../external-sources'".

- [ ] **Step 3: Implement the helper**

Create `dashboard/lib/kw16-fixes/external-sources.ts`:

```ts
/**
 * Drop Sources[] entries whose URL is in the drop set, and strip
 * all <sup>LETTER</sup> occurrences that referenced them from content.
 * Does NOT renumber — caller should run realignCitations afterwards.
 *
 * See spec: docs/superpowers/specs/2026-04-16-beurer-kw16-fixes-design.md § Item 4b.
 */

const ALL_FIELDS = [
  "Direct_Answer",
  "Intro",
  "TLDR",
  ...Array.from({ length: 9 }, (_, i) => `section_${String(i + 1).padStart(2, "0")}_content`),
  ...Array.from({ length: 6 }, (_, i) => `faq_${String(i + 1).padStart(2, "0")}_answer`),
  ...Array.from({ length: 4 }, (_, i) => `paa_${String(i + 1).padStart(2, "0")}_answer`),
];

function normaliseUrl(u: string): string {
  return u.replace(/\/+$/, "");
}

export interface DropResult {
  articleJson: Record<string, any>;
  droppedSources: Array<{ letter: string; url: string; title: string }>;
  warnings: Array<{ message: string }>;
}

export function dropExternalSources(
  articleJson: Record<string, any>,
  dropUrls: Set<string>
): DropResult {
  const out = { ...articleJson };
  const sources: any[] = Array.isArray(out.Sources) ? [...out.Sources] : [];
  const droppedSources: Array<{ letter: string; url: string; title: string }> = [];
  const warnings: Array<{ message: string }> = [];

  if (dropUrls.size === 0) {
    return { articleJson: out, droppedSources, warnings };
  }

  const normDrops = new Set([...dropUrls].map(normaliseUrl));
  const dropIndices = new Set<number>();

  sources.forEach((src, idx) => {
    if (src && typeof src.url === "string" && normDrops.has(normaliseUrl(src.url))) {
      dropIndices.add(idx);
      droppedSources.push({
        letter: String.fromCharCode(65 + idx),
        url: src.url,
        title: src.title || "",
      });
    }
  });

  // Warn on drops that didn't match anything
  const matchedUrls = new Set(droppedSources.map((d) => normaliseUrl(d.url)));
  for (const target of normDrops) {
    if (!matchedUrls.has(target)) {
      warnings.push({ message: `Drop URL not found in Sources[]: ${target}` });
    }
  }

  if (dropIndices.size === 0) {
    return { articleJson: out, droppedSources, warnings };
  }

  // Strip matching <sup>LETTER</sup> from every content field
  const lettersToStrip = new Set([...dropIndices].map((i) => String.fromCharCode(65 + i)));
  const supRe = /<sup>([A-Z])<\/sup>/g;
  for (const field of ALL_FIELDS) {
    const val = out[field];
    if (typeof val !== "string" || !val.includes("<sup>")) continue;
    out[field] = val.replace(supRe, (match, letter) => (lettersToStrip.has(letter) ? "" : match));
  }

  // Remove entries from Sources[]
  out.Sources = sources.filter((_, idx) => !dropIndices.has(idx));

  return { articleJson: out, droppedSources, warnings };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd dashboard
npm test -- external-sources
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/kw16-fixes/external-sources.ts dashboard/lib/kw16-fixes/__tests__/external-sources.test.ts
git commit -m "feat(kw16): add external-source drop helper

Drops Sources[] entries by URL and strips matching <sup> tags
from content. Does not renumber — realignCitations handles that
when called afterwards in the orchestrator.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Python audit script — external sources

**Files:**
- Create: `scripts/audit_external_sources.py`

**Context:** Read-only script that fetches every external (non-beurer.com) source URL from every completed article, classifies each URL as `specific_article` / `likely_overview` / `unclear` using Firecrawl + heuristics, and writes a CSV for human triage. The human fills the `keep_or_drop` column; the orchestrator consumes that CSV.

Follows the existing `scripts/fix_existing_articles.py` convention (argparse-like flag parsing via `sys.argv`, no pytest, stdout progress logging, `--dry-run` supported).

- [ ] **Step 1: Check Firecrawl client location**

```bash
grep -r "from firecrawl\|import firecrawl" services/ crawlers/ | head -5
```

Note the exact import path — you'll reuse it.

- [ ] **Step 2: Write the script**

Create `scripts/audit_external_sources.py`:

```python
"""Audit external source URLs across client-facing Beurer articles.

Classifies each external (non-beurer.com) source URL as specific_article,
likely_overview, or unclear using Firecrawl + simple HTML heuristics.
Writes docs/kw16_external_sources_audit.csv for human triage.

The human fills the `keep_or_drop` column (pre-filled as a suggestion)
and the orchestrator (dashboard/scripts/apply-kw16-fixes.ts) consumes it.

Usage:
  python scripts/audit_external_sources.py [--dry-run] [--article-id UUID]
"""

from __future__ import annotations

import csv
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from supabase import create_client

# Reuse the Firecrawl client used across crawlers/
from crawlers.firecrawl_runner import get_firecrawl_client  # type: ignore

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
OUT_CSV = REPO_ROOT / "docs" / "kw16_external_sources_audit.csv"

DRY_RUN = "--dry-run" in sys.argv
ARTICLE_ID_FILTER: str | None = None
for i, arg in enumerate(sys.argv):
    if arg == "--article-id" and i + 1 < len(sys.argv):
        ARTICLE_ID_FILTER = sys.argv[i + 1]

OVERVIEW_H1_RE = re.compile(r"^(Ratgeber|Übersicht|Themen|Kategorie|Magazin|News|Blog)\b", re.IGNORECASE)


def classify(body_word_count: int, article_link_count: int, h1_text: str, og_type: str) -> str:
    if og_type == "article":
        return "specific_article"
    if body_word_count > 400 and article_link_count < 10:
        return "specific_article"
    if body_word_count < 200 or article_link_count > 30 or OVERVIEW_H1_RE.match(h1_text or ""):
        return "likely_overview"
    return "unclear"


def extract_signals(html: str, host: str) -> tuple[int, int, str, str]:
    """Return (body_word_count, article_link_count, h1_text, og_type)."""
    # Strip nav/footer/aside to approximate the body region
    body = re.sub(r"<(nav|footer|aside|header|script|style)[\s\S]*?</\1>", " ", html, flags=re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", " ", body)
    body_word_count = len([w for w in plain.split() if w.strip()])

    # Count same-host <a> links in body
    anchor_hrefs = re.findall(r'<a\s+[^>]*href="([^"]+)"', body, flags=re.IGNORECASE)
    article_link_count = sum(1 for h in anchor_hrefs if host and host in h)

    # Extract first <h1>
    h1_match = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, flags=re.IGNORECASE)
    h1_text = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip() if h1_match else ""

    # Extract og:type
    og_match = re.search(r'<meta[^>]*property="og:type"[^>]*content="([^"]*)"', html, flags=re.IGNORECASE)
    og_type = og_match.group(1).lower() if og_match else ""

    return body_word_count, article_link_count, h1_text, og_type


def pre_fill_keep_or_drop(verdict: str) -> str:
    if verdict == "likely_overview":
        return "drop"
    if verdict == "specific_article":
        return "keep"
    return ""  # unclear → force human decision


def main() -> int:
    url = os.environ["BEURER_SUPABASE_URL"]
    key = os.environ["BEURER_SUPABASE_KEY"]
    sb = create_client(url, key)
    fc = get_firecrawl_client()

    query = sb.table("blog_articles").select("id, keyword, article_json").eq("status", "completed")
    if ARTICLE_ID_FILTER:
        query = query.eq("id", ARTICLE_ID_FILTER)
    resp = query.execute()
    articles = resp.data or []
    print(f"Auditing {len(articles)} articles...", flush=True)

    rows: list[dict] = []
    for art in articles:
        aj = art.get("article_json") or {}
        sources = aj.get("Sources") or []
        keyword = art.get("keyword") or ""
        for idx, src in enumerate(sources):
            src_url = (src or {}).get("url") or ""
            if not src_url:
                continue
            parsed = urlparse(src_url)
            host = parsed.netloc.lower()
            if "beurer.com" in host:
                continue  # internal, skip

            letter = chr(65 + idx)
            title = (src or {}).get("title") or ""
            verdict = "unclear"
            body_wc = 0
            link_count = 0
            h1 = ""
            og_type = ""

            try:
                print(f"  [{art['id'][:8]}] {letter}: {src_url}", flush=True)
                result = fc.scrape_url(src_url, params={"formats": ["html"]})
                html = (result or {}).get("html") or ""
                body_wc, link_count, h1, og_type = extract_signals(html, host)
                verdict = classify(body_wc, link_count, h1, og_type)
            except Exception as e:
                print(f"    ERROR: {e}", flush=True)
                verdict = "unclear"

            rows.append({
                "article_id": art["id"],
                "article_keyword": keyword,
                "source_letter": letter,
                "source_title": title,
                "source_url": src_url,
                "body_word_count": body_wc,
                "article_link_count": link_count,
                "h1_text": h1,
                "og_type": og_type,
                "verdict": verdict,
                "keep_or_drop": pre_fill_keep_or_drop(verdict),
            })
            time.sleep(2.0)  # match existing crawler rate limit

    if DRY_RUN:
        print(f"\nDRY RUN — would write {len(rows)} rows to {OUT_CSV}")
        for r in rows[:5]:
            print(f"  {r['article_keyword'][:30]:30s} | {r['source_letter']} | {r['verdict']:18s} | {r['source_url']}")
        return 0

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [
            "article_id", "article_keyword", "source_letter", "source_title", "source_url",
            "body_word_count", "article_link_count", "h1_text", "og_type", "verdict", "keep_or_drop",
        ])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {OUT_CSV}")
    print("Triage the CSV — edit `keep_or_drop` column, save.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Verify the Firecrawl import name**

```bash
cd C:/Users/yousi/scaile/social_listening_service
grep -n "def get_firecrawl_client\|firecrawl_client = \|FirecrawlApp" crawlers/firecrawl_runner.py | head -5
```

If the function name differs (e.g. `_get_firecrawl()`), update the import in `scripts/audit_external_sources.py` line 19 accordingly, AND the single call site `fc.scrape_url(...)` to match the actual client API (some Firecrawl versions use `app.scrape_url(url, ...)` returning `{"html": ...}`, others return `{"data": {"html": ...}}`).

- [ ] **Step 4: Dry-run against one article**

```bash
cd C:/Users/yousi/scaile/social_listening_service
python scripts/audit_external_sources.py --dry-run --article-id <id-of-article-11-Reizstromgeraete>
```

Pick the article id by running:

```bash
python -c "import os; from dotenv import load_dotenv; from supabase import create_client; load_dotenv(); sb=create_client(os.environ['BEURER_SUPABASE_URL'], os.environ['BEURER_SUPABASE_KEY']); r=sb.table('blog_articles').select('id,keyword').ilike('keyword', '%reizstrom%').execute(); print(r.data)"
```

Expected in dry-run: prints up to 5 summary rows to stdout; no CSV written.

- [ ] **Step 5: Full run against all articles**

```bash
python scripts/audit_external_sources.py
```

Expected: `docs/kw16_external_sources_audit.csv` written with one row per external source across all 11 articles (typical total: 20-40 rows).

- [ ] **Step 6: Commit**

```bash
git add scripts/audit_external_sources.py
git commit -m "feat(kw16): add external-source audit script

Classifies every external source URL across the 11 client-facing
articles as specific_article | likely_overview | unclear and writes
docs/kw16_external_sources_audit.csv for human triage. Pre-fills
keep_or_drop per verdict; unclear rows force human decision.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

Do NOT commit `docs/kw16_external_sources_audit.csv` yet — the human triage in Task 7 modifies it.

---

## Task 7: Triage the CSV (human)

**Files:**
- Modify: `docs/kw16_external_sources_audit.csv` (the human edits `keep_or_drop` column)

- [ ] **Step 1: Open the CSV**

Open `docs/kw16_external_sources_audit.csv` in a spreadsheet (Excel / LibreOffice Calc / Numbers). Preserve UTF-8 encoding on save.

- [ ] **Step 2: Review each row**

For each row, spot-check the `source_url` in a browser. Update `keep_or_drop`:
- `drop` — URL lands on a category/overview/listing page (matches Beurer's complaint)
- `keep` — URL lands on a specific article
- leave empty (default for `unclear` rows) to keep the source — the orchestrator only drops on explicit `drop`

- [ ] **Step 3: Save the CSV**

Save as UTF-8 CSV. Keep the same column order and the header row.

- [ ] **Step 4: Commit the triaged CSV**

```bash
git add docs/kw16_external_sources_audit.csv
git commit -m "docs(kw16): triage external-source audit results

Human triage of the audit CSV. `keep_or_drop` column reflects
per-URL decisions. Orchestrator consumes this in the next step.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Extract shared `countWordsInHtml` helper

**Files:**
- Create: `dashboard/lib/word-count.ts`
- Modify: `dashboard/lib/article-generator.ts:356-359`

**Context:** The orchestrator needs to recompute `word_count` after re-rendering HTML. The existing `countWordsInHtml` is a private function inside `article-generator.ts`. Extract it so both places use one definition.

- [ ] **Step 1: Create the shared helper**

Create `dashboard/lib/word-count.ts`:

```ts
/**
 * Count words in an HTML string by stripping tags and splitting on whitespace.
 * Shared by article-generator.ts and dashboard/scripts/apply-kw16-fixes.ts.
 */
export function countWordsInHtml(html: string): number {
  const plain = html.replace(/<[^>]+>/g, " ");
  return plain.split(/\s+/).filter(Boolean).length;
}
```

- [ ] **Step 2: Replace the private definition in `article-generator.ts`**

Open `dashboard/lib/article-generator.ts`. Delete lines 352-359 (the comment block and the `function countWordsInHtml`) and add an import at the top of the file (after existing imports):

```ts
import { countWordsInHtml } from "./word-count";
```

- [ ] **Step 3: Run all tests + build to confirm no regression**

```bash
cd dashboard
npm test
npm run build
```

Expected: all tests pass; build succeeds (no TypeScript errors).

- [ ] **Step 4: Commit**

```bash
git add dashboard/lib/word-count.ts dashboard/lib/article-generator.ts
git commit -m "refactor(dashboard): extract countWordsInHtml to lib/word-count

Enables the upcoming kw16 orchestrator to reuse the same word-count
logic as the edit flow. Single source of truth; no behavior change.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Orchestrator — `apply-kw16-fixes.ts`

**Files:**
- Create: `dashboard/scripts/apply-kw16-fixes.ts`
- Modify: `dashboard/package.json` (add `"fix:kw16"` script entry)

**Context:** Composes the three pure helpers, reads the triaged CSV, fetches each completed article, applies mutations in memory, re-renders `article_html` via `renderArticleHtml`, and writes back with one snapshot + one feedback entry per mutated article. Articles touched only by the ToC re-render (no data mutations) update `article_html` alone without a snapshot.

- [ ] **Step 1: Add npm script entry**

Open `dashboard/package.json`, extend `"scripts"`:

```json
"fix:kw16": "tsx scripts/apply-kw16-fixes.ts"
```

Final `"scripts"` block:

```json
"scripts": {
  "copy-template": "node -e \"...existing...\"",
  "dev": "npm run copy-template && next dev",
  "build": "npm run copy-template && next build",
  "start": "next start",
  "test": "vitest run",
  "test:watch": "vitest",
  "fix:kw16": "tsx scripts/apply-kw16-fixes.ts"
}
```

- [ ] **Step 2: Create the orchestrator script**

Create `dashboard/scripts/apply-kw16-fixes.ts`:

```ts
#!/usr/bin/env tsx
/**
 * KW16 batch fix orchestrator.
 *
 * Reads the triaged external-source audit CSV, applies three mutations
 * (landing-page link strip, external-source drop, citation realign) to
 * each completed article, re-renders article_html via the dashboard
 * renderer, and writes back with one snapshot + one feedback entry per
 * mutated article.
 *
 * Usage (from dashboard/):
 *   npm run fix:kw16 -- --flagged-csv=../docs/kw16_external_sources_audit.csv [--dry-run] [--article-id=UUID]
 *
 * See spec: docs/superpowers/specs/2026-04-16-beurer-kw16-fixes-design.md.
 */

import fs from "fs";
import path from "path";
import { getSupabase } from "../lib/supabase";
import { renderArticleHtml } from "../lib/html-renderer";
import { countWordsInHtml } from "../lib/word-count";
import { stripLandingPageLinks } from "../lib/kw16-fixes/landing-page-links";
import { realignCitations } from "../lib/kw16-fixes/citations";
import { dropExternalSources } from "../lib/kw16-fixes/external-sources";

// --- CLI parsing -----------------------------------------------------------

const args = process.argv.slice(2);
function argValue(name: string): string | null {
  const eq = args.find((a) => a.startsWith(`--${name}=`));
  if (eq) return eq.slice(name.length + 3);
  const i = args.indexOf(`--${name}`);
  if (i >= 0 && i + 1 < args.length) return args[i + 1];
  return null;
}
const dryRun = args.includes("--dry-run");
const csvPath = argValue("flagged-csv");
const articleIdFilter = argValue("article-id");

if (!csvPath) {
  console.error("Missing --flagged-csv=PATH");
  process.exit(2);
}

// --- CSV loader ------------------------------------------------------------

interface CsvRow {
  article_id: string;
  source_url: string;
  keep_or_drop: string;
}

function loadDropsByArticle(fullPath: string): Map<string, Set<string>> {
  const content = fs.readFileSync(fullPath, "utf-8");
  const lines = content.split(/\r?\n/).filter(Boolean);
  const header = lines[0].split(",").map((h) => h.trim().replace(/^"|"$/g, ""));
  const idxArticle = header.indexOf("article_id");
  const idxUrl = header.indexOf("source_url");
  const idxDecision = header.indexOf("keep_or_drop");
  if (idxArticle < 0 || idxUrl < 0 || idxDecision < 0) {
    throw new Error(`CSV missing required columns. Found: ${header.join(", ")}`);
  }
  const out = new Map<string, Set<string>>();
  for (let i = 1; i < lines.length; i++) {
    const cells = parseCsvLine(lines[i]);
    if (cells.length <= idxDecision) continue;
    const decision = cells[idxDecision].trim().toLowerCase();
    if (decision !== "drop") continue;
    const articleId = cells[idxArticle].trim();
    const url = cells[idxUrl].trim();
    if (!articleId || !url) continue;
    if (!out.has(articleId)) out.set(articleId, new Set());
    out.get(articleId)!.add(url);
  }
  return out;
}

function parseCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuote = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQuote) {
      if (c === '"' && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else if (c === '"') {
        inQuote = false;
      } else {
        cur += c;
      }
    } else {
      if (c === ",") {
        out.push(cur);
        cur = "";
      } else if (c === '"') {
        inQuote = true;
      } else {
        cur += c;
      }
    }
  }
  out.push(cur);
  return out;
}

// --- Main ------------------------------------------------------------------

async function main() {
  const csvAbs = path.resolve(csvPath!);
  console.log(`Loading CSV: ${csvAbs}`);
  const dropsByArticle = loadDropsByArticle(csvAbs);
  console.log(`Drop instructions for ${dropsByArticle.size} articles`);

  const sb = getSupabase();
  const query = sb.from("blog_articles")
    .select("id, keyword, headline, article_json, article_html, word_count, language, author_id, social_context, feedback_history")
    .eq("status", "completed");
  const { data, error } = articleIdFilter
    ? await query.eq("id", articleIdFilter)
    : await query;
  if (error) throw new Error(`Supabase fetch failed: ${error.message}`);
  const articles = data ?? [];
  console.log(`Fetched ${articles.length} completed articles`);

  let touched = 0;
  let refreshed = 0;
  let skipped = 0;

  for (const art of articles) {
    const idShort = String(art.id).slice(0, 8);
    const keyword = art.keyword || "";
    const working = JSON.parse(JSON.stringify(art.article_json || {}));
    const currentHtml: string = art.article_html || "";
    const dropUrls = dropsByArticle.get(art.id) || new Set<string>();

    const stripResult = stripLandingPageLinks(working);
    const dropResult = dropExternalSources(stripResult.articleJson, dropUrls);
    const realignResult = realignCitations(dropResult.articleJson);
    const mutated = realignResult.articleJson;

    const mutationsChanged =
      stripResult.fixesApplied > 0 ||
      dropResult.droppedSources.length > 0 ||
      realignResult.changed;

    // Fetch author if present (renderer uses it for the author card)
    let author: any = null;
    if (art.author_id) {
      const { data: authorRow } = await sb
        .from("blog_authors")
        .select("*")
        .eq("id", art.author_id)
        .single();
      author = authorRow || null;
    }

    // Call must mirror the edit-flow render (article-generator.ts:443) so re-render
    // output only differs when data changed, not because of missing render options.
    const newHtml = renderArticleHtml({
      article: mutated,
      companyName: "Beurer",
      companyUrl: "https://www.beurer.com",
      language: art.language || "de",
      category: (art as any).social_context?.category || "",
      author,
    });
    const htmlChanged = newHtml !== currentHtml;

    // Log per-article warnings (stripLandingPageLinks produces no warnings)
    for (const w of [...dropResult.warnings, ...realignResult.warnings]) {
      console.warn(`  [${idShort}] WARN: ${w.message}`);
    }

    if (!mutationsChanged && !htmlChanged) {
      console.log(`[${idShort}] ${keyword.slice(0, 40)} — skipped (no change)`);
      skipped++;
      continue;
    }

    if (!mutationsChanged && htmlChanged) {
      console.log(`[${idShort}] ${keyword.slice(0, 40)} — html-only refresh (ToC renderer fix)`);
      refreshed++;
      if (!dryRun) {
        const { error: upErr } = await sb
          .from("blog_articles")
          .update({
            article_html: newHtml,
            word_count: countWordsInHtml(newHtml),
            updated_at: new Date().toISOString(),
          })
          .eq("id", art.id);
        if (upErr) throw new Error(`Refresh update failed for ${art.id}: ${upErr.message}`);
      }
      continue;
    }

    // Full fix path
    const summary = [
      `${stripResult.fixesApplied} /l/ links stripped`,
      `${dropResult.droppedSources.length} sources dropped`,
      realignResult.changed ? "citations realigned" : null,
    ].filter(Boolean).join(", ");
    console.log(`[${idShort}] ${keyword.slice(0, 40)} — ${summary}`);
    touched++;

    if (dryRun) continue;

    const history = Array.isArray(art.feedback_history) ? [...art.feedback_history] : [];
    const snapshotVersion = history.filter((e: any) => e?.type === "snapshot").length + 1;
    history.push({
      type: "snapshot",
      version: snapshotVersion,
      headline: art.headline || keyword,
      article_html: currentHtml,
      word_count: art.word_count || countWordsInHtml(currentHtml),
      created_at: new Date().toISOString(),
    });
    history.push({
      type: "feedback",
      version: history.length,
      comment: `KW16 batch fix: ${summary}`,
      created_at: new Date().toISOString(),
    });

    const { error: upErr } = await sb
      .from("blog_articles")
      .update({
        article_json: mutated,
        article_html: newHtml,
        word_count: countWordsInHtml(newHtml),
        feedback_history: history,
        updated_at: new Date().toISOString(),
      })
      .eq("id", art.id);
    if (upErr) throw new Error(`Update failed for ${art.id}: ${upErr.message}`);
  }

  console.log(`\nSummary: ${touched} mutated, ${refreshed} html-refreshed, ${skipped} skipped`);
  if (dryRun) console.log("(dry-run — no database writes performed)");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
```

- [ ] **Step 3: Build to verify the orchestrator compiles**

```bash
cd dashboard
npx tsx --no-warnings scripts/apply-kw16-fixes.ts --help 2>&1 | head
```

This will error with "Missing --flagged-csv=PATH" (exit code 2) — that's expected and proves the file parses.

Alternative, stricter: `npx tsc --noEmit scripts/apply-kw16-fixes.ts` (may surface missing config but verifies type-check).

- [ ] **Step 4: Commit**

```bash
git add dashboard/scripts/apply-kw16-fixes.ts dashboard/package.json
git commit -m "feat(kw16): add orchestrator for batch article fixes

Composes landing-page-links, external-sources, and citations
helpers. Re-renders article_html via renderArticleHtml.
Writes one snapshot + one feedback entry per mutated article;
html-only refreshes (ToC renderer fix propagation) update
article_html alone without a snapshot.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Orchestrator smoke test (dry-run, one article)

**Files:** none (operational task)

- [ ] **Step 1: Pick an article ID to dry-run against**

```bash
cd C:/Users/yousi/scaile/social_listening_service
python -c "import os; from dotenv import load_dotenv; from supabase import create_client; load_dotenv(); sb=create_client(os.environ['BEURER_SUPABASE_URL'], os.environ['BEURER_SUPABASE_KEY']); r=sb.table('blog_articles').select('id,keyword').ilike('keyword', '%reizstrom%').execute(); print(r.data)"
```

Note the id — this is Anika's specifically-cited article #11.

- [ ] **Step 2: Dry-run orchestrator on that article**

```bash
cd dashboard
npm run fix:kw16 -- --flagged-csv=../docs/kw16_external_sources_audit.csv --dry-run --article-id=<paste-id>
```

Expected output (shape, not exact numbers):

```
Loading CSV: .../docs/kw16_external_sources_audit.csv
Drop instructions for N articles
Fetched 1 completed articles
[xxxxxxxx] reizstrom... — 2 /l/ links stripped, 1 sources dropped, citations realigned
Summary: 1 mutated, 0 html-refreshed, 0 skipped
(dry-run — no database writes performed)
```

If output says `0 mutated` for this article but Anika cited it specifically, something's wrong — check that the CSV actually has `drop` entries for this article_id, and that the `/l/` links exist in the stored `article_json`.

- [ ] **Step 3: Dry-run against all articles**

```bash
npm run fix:kw16 -- --flagged-csv=../docs/kw16_external_sources_audit.csv --dry-run
```

Expected: per-article summary lines for all 11 articles. Mix of mutations, html-only refreshes, and skips. No errors.

- [ ] **Step 4: Real run on the single article (confidence check)**

```bash
npm run fix:kw16 -- --flagged-csv=../docs/kw16_external_sources_audit.csv --article-id=<same-id>
```

- [ ] **Step 5: Spot-check in the dashboard**

Start the dashboard dev server:

```bash
npm run dev
```

Open `http://localhost:3000`, navigate to the content tab, find the Reizstromgeräte article. Verify:
- ToC shows full section titles (no "..." truncation)
- No `/l/` landing-page links remain
- Citations read A, B, C, ... in order
- Version modal shows a new snapshot labeled "KW16 batch fix: ..."

If any check fails, stop and debug before proceeding.

- [ ] **Step 6: Real run on all articles**

Only after the single-article smoke test passes:

```bash
npm run fix:kw16 -- --flagged-csv=../docs/kw16_external_sources_audit.csv
```

Spot-check 2-3 more articles in the dashboard afterwards.

- [ ] **Step 7: Commit a runbook note (no code)**

```bash
cd C:/Users/yousi/scaile/social_listening_service
cat >> docs/superpowers/plans/2026-04-16-beurer-kw16-fixes.md <<'EOF'

---

## Execution log

- Dry-run: YYYY-MM-DD HH:MM — all 11 articles, N mutated / M refreshed / K skipped
- Real run: YYYY-MM-DD HH:MM — same counts
- Spot-checks: articles [..., ..., ...] verified in dashboard
EOF
git add docs/superpowers/plans/2026-04-16-beurer-kw16-fixes.md
git commit -m "docs(kw16): record execution log

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

(Fill in the actual timestamps/counts when you run; replace placeholders.)

---

## Task 11: Rollback script (safety net, optional until needed)

**Files:**
- Create: `scripts/rollback_kw16_batch.py`

**Context:** Undo the batch by restoring the most recent KW16 snapshot for every article that was mutated. Only touches articles whose `feedback_history` contains a `{type: "feedback"}` entry with `comment` starting with `KW16 batch fix:`.

- [ ] **Step 1: Write the rollback script**

Create `scripts/rollback_kw16_batch.py`:

```python
"""Roll back the KW16 batch fix by restoring each mutated article's
most recent pre-KW16 snapshot.

Only touches articles whose feedback_history contains a feedback entry
whose comment starts with 'KW16 batch fix:'.

Usage:
  python scripts/rollback_kw16_batch.py [--dry-run] [--article-id UUID]
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

DRY_RUN = "--dry-run" in sys.argv
ARTICLE_ID_FILTER: str | None = None
for i, arg in enumerate(sys.argv):
    if arg == "--article-id" and i + 1 < len(sys.argv):
        ARTICLE_ID_FILTER = sys.argv[i + 1]


def find_kw16_snapshot(history: list[dict]) -> dict | None:
    """Return the snapshot entry immediately preceding the most recent
    KW16 feedback entry, or None."""
    latest_feedback_idx = None
    for i in range(len(history) - 1, -1, -1):
        e = history[i]
        if e.get("type") == "feedback" and str(e.get("comment") or "").startswith("KW16 batch fix:"):
            latest_feedback_idx = i
            break
    if latest_feedback_idx is None:
        return None
    for j in range(latest_feedback_idx - 1, -1, -1):
        if history[j].get("type") == "snapshot":
            return history[j]
    return None


def main() -> int:
    sb = create_client(os.environ["BEURER_SUPABASE_URL"], os.environ["BEURER_SUPABASE_KEY"])
    query = sb.table("blog_articles").select("id, keyword, article_html, feedback_history").eq("status", "completed")
    if ARTICLE_ID_FILTER:
        query = query.eq("id", ARTICLE_ID_FILTER)
    articles = (query.execute().data) or []

    restored = 0
    for art in articles:
        history = art.get("feedback_history") or []
        snap = find_kw16_snapshot(history)
        if not snap:
            continue
        old_html = snap.get("article_html") or ""
        old_wc = snap.get("word_count") or 0
        kw = (art.get("keyword") or "")[:40]
        idshort = art["id"][:8]
        print(f"[{idshort}] {kw} — restoring snapshot v{snap.get('version')}")
        restored += 1
        if DRY_RUN:
            continue
        # Append a rollback feedback entry so history is auditable
        new_history = list(history) + [{
            "type": "feedback",
            "version": len(history) + 1,
            "comment": "KW16 rollback: restored pre-KW16 snapshot",
            "created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        }]
        sb.table("blog_articles").update({
            "article_html": old_html,
            "word_count": old_wc,
            "feedback_history": new_history,
            "updated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        }).eq("id", art["id"]).execute()

    print(f"\n{'DRY RUN ' if DRY_RUN else ''}Restored {restored} articles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Note: this restore path writes `article_html` + `word_count` only (not `article_json`) — the snapshot contract in `article-generator.ts:514-521` only stores the HTML. This is consistent with the existing dashboard version-restore flow at `blog-article/route.ts:545-555`. `article_json` stays at the post-KW16 state; since renders come from `article_html`, Beurer's view reverts immediately. A full JSON revert is not feasible from the snapshot shape — flag this limitation to the user if they actually need to roll back.

- [ ] **Step 2: Dry-run**

```bash
cd C:/Users/yousi/scaile/social_listening_service
python scripts/rollback_kw16_batch.py --dry-run
```

Expected: prints `[id] keyword — restoring snapshot vN` for each mutated article; ends with `DRY RUN Restored N articles.` No DB writes.

- [ ] **Step 3: Commit**

```bash
git add scripts/rollback_kw16_batch.py
git commit -m "feat(kw16): add rollback script

One-off restore of article_html + word_count from the pre-KW16
snapshot for every article whose feedback_history shows a KW16
batch fix. article_json is NOT reverted because snapshots only
preserve HTML — document this limitation in the script header.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Post-implementation checklist

- [ ] All 11 articles spot-checked in the dashboard content tab
- [ ] ToC shows full section titles on every article
- [ ] Articles in the CSV with `keep_or_drop = drop` no longer have those external sources
- [ ] Citations read A, B, C, … (no B-before-A)
- [ ] No more `beurer.com/.../l/...` hrefs in article bodies
- [ ] Version modal in the dashboard shows the new KW16 snapshot for mutated articles
- [ ] Rollback script dry-run lists the mutated articles correctly
- [ ] Execution log appended to this plan document

Out of scope (handled by other workstreams):
- Hero/product/Bildsprache image fixes — separate image agent
- Dashboard UI for manual internal-link editing — future UI work (also covers "wrong internal product link within correct category")
- PIM integration (STIBO GraphQL) — separate workstream
- Magazine-article update workflow — separate workstream
