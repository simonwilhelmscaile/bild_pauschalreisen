/**
 * Article Generator - Generates, regenerates, and inline-edits blog articles
 * using the Gemini API directly (no Python backend required).
 *
 * Port of blog/article_service.py + blog/stage2/blog_writer.py
 */

import { GoogleGenerativeAI } from "@google/generative-ai";
import { getSupabase } from "@/lib/supabase";
import { renderArticleHtml } from "@/lib/html-renderer";
import {
  BEURER_PRODUCTS,
  COMPETITOR_PRODUCTS,
  CATEGORY_LABELS_DE,
  PAIN_CATEGORY_LABELS_DE,
} from "@/lib/constants";

// ---------------------------------------------------------------------------
// Gemini client
// ---------------------------------------------------------------------------

const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-2.5-flash";

function getGeminiKey(): string {
  const key = process.env.GEMINI_API_KEY;
  if (!key) throw new Error("GEMINI_API_KEY environment variable is not set");
  return key;
}

// ---------------------------------------------------------------------------
// Fix spaced URLs injected by LLM in article JSON content fields
// ---------------------------------------------------------------------------

/** Fix URLs with spaces injected by LLM in article JSON content fields */
function fixSpacedUrlsInArticleJson(article: Record<string, any>): void {
  const fieldsToFix = ["Intro", "Direct_Answer", "TLDR"];
  for (let i = 1; i <= 9; i++) {
    fieldsToFix.push(`section_${String(i).padStart(2, "0")}_content`);
  }
  for (let i = 1; i <= 6; i++) {
    fieldsToFix.push(`faq_${String(i).padStart(2, "0")}_answer`);
  }
  for (let i = 1; i <= 4; i++) {
    fieldsToFix.push(`paa_${String(i).padStart(2, "0")}_answer`);
  }
  for (const field of fieldsToFix) {
    const val = article[field];
    if (typeof val === "string" && val.includes("href")) {
      article[field] = val.replace(/href="([^"]+)"/g, (match, url) => {
        const fixed = url.replace(/\s+/g, "");
        return fixed !== url ? `href="${fixed}"` : match;
      });
    }
  }
}

// ---------------------------------------------------------------------------
// Company context (embedded from blog/context.md + blog/persona.md)
// ---------------------------------------------------------------------------

function getCompanyContext(): string {
  const products = BEURER_PRODUCTS.join(", ");
  const competitors = COMPETITOR_PRODUCTS.join(", ");
  const contentThemes = Object.values(CATEGORY_LABELS_DE).join(", ");
  const painPoints = Object.values(PAIN_CATEGORY_LABELS_DE).join("; ");

  return `Company: Beurer
Industry: Gesundheit & Medizintechnik
Target Audience: Gesundheitsbewusste Verbraucher in Deutschland, die nach zuverlässigen Gesundheitsgeräten für den Heimgebrauch suchen
Tone: professional
About: Beurer ist ein traditionsreiches deutsches Unternehmen für Gesundheits- und Wohlbefinden-Produkte. Das Sortiment umfasst Blutdruckmessgeräte, TENS/EMS-Geräte zur Schmerztherapie und Infrarotlampen.
Products/Services: ${products}
Customer Pain Points: ${painPoints}
Value Propositions: Über 100 Jahre Erfahrung in der Gesundheitsbranche; Deutsche Qualität und Präzision; Klinisch validierte Messgenauigkeit; Einfache Bedienung für alle Altersgruppen; Umfangreiches Sortiment für verschiedene Gesundheitsbedürfnisse
COMPETITORS (NEVER mention these): ${competitors}
Common Use Cases: Blutdrucküberwachung zu Hause; Schmerztherapie mit TENS/EMS; Wärmetherapie mit Infrarot; Menstruationsschmerzlinderung
Content Themes: ${contentThemes}

=== VOICE & WRITING STYLE ===
Ideal Reader: Gesundheitsbewusste Erwachsene 35-65, die Gesundheitsthemen online recherchieren
Voice Style: Professionell, einfühlsam und vertrauenswürdig. Verwendet die Du-Form. Verbindet medizinisches Fachwissen mit verständlicher Sprache.
Language Style: Formality: informal, Complexity: accessible, Perspective: second_person_informal, Sentences: medium
DO: Medizinische Fachbegriffe erklären; Quellenangaben und Studien zitieren; Praktische Tipps geben; Empathisch auf Schmerzthemen eingehen; Du-Form konsequent verwenden
DON'T: Keine medizinischen Diagnosen stellen; Keine reißerischen Gesundheitsversprechen; Keine Sie-Form verwenden (NIEMALS 'Sie', 'Ihnen', 'Ihr' als Anrede); Keine unbelegten Behauptungen; Keine Verharmlosung von Symptomen; Niemals behaupten ein Produkt könne Schmerzen stoppen oder heilen; Niemals Heimgeräte als gleichwertig zu professioneller klinischer Ausrüstung darstellen; Immer abschwächen zu "kann unterstützen" / "kann zur Linderung beitragen"; Immer Kontext ergänzen: "in Absprache mit deinem Arzt"; NIEMALS auf Produktberater-Seiten (/produktberater) oder App-Welt (/app-welt/) verlinken — stattdessen auf Kategorie- oder Produktseiten verlinken (z.B. /de/c/0010101/ für Blutdruckmessgeräte)
BANNED WORDS (never use): Wundermittel, garantiert heilen, sofort schmerzfrei, 100% sicher, Ärzte hassen diesen Trick, Schmerzen stoppen, Schmerzen beseitigen, klinische Präzision (im Vergleich zu Arztgeräten), genauso genau wie beim Arzt
Formatting: Use rhetorical questions, Use bullet/numbered lists, Include data/statistics, First person: none`;
}

// ---------------------------------------------------------------------------
// System instruction (from blog/stage2/prompts/system_instruction.txt)
// ---------------------------------------------------------------------------

function getSystemInstruction(): string {
  const currentDate = new Date().toISOString().slice(0, 10);
  return `You are an expert content writer. Write like a skilled human, not AI.

HARD RULES:
- NEVER invent statistics or facts
- NEVER mention competitors by name
- NO em-dashes (—), NO "Here's how", "Key points:", or robotic phrases
- NEVER return an empty "Sources" field - this is a MANDATORY output requirement

NO HEALING PROMISES (Beurer compliance — strictly enforced):
- NEVER claim a product can "stop pain", "eliminate symptoms", "cure", or "heal"
- NEVER claim home devices deliver "equally precise", "just as accurate", or "clinical-grade" results compared to professional medical equipment
- ALWAYS soften claims: use "can support", "may help with relief", "can contribute to", "may alleviate", "designed to assist with"
- ALWAYS add context: "as part of a broader approach", "in consultation with your doctor", "as a complementary measure"
- For TENS/EMS: say "may help relieve pain" or "can support pain management", NEVER "stops pain" or "eliminates pain"
- For blood pressure monitors: say "supports reliable monitoring at home", NEVER "as accurate as your doctor's equipment"
- When citing efficacy studies, frame as "studies suggest" or "research indicates", not as guaranteed outcomes
- When in doubt, understate rather than overstate — regulatory caution always wins

GERMAN ADDRESS FORM (Du-Form):
- ALWAYS use informal "du/dir/dein/deine" — NEVER formal "Sie/Ihnen/Ihr/Ihre" as address
- "Sie" (capitalized) must NEVER appear as a pronoun of address in the article
- At sentence start, "sie" (they/she, third person) stays lowercase "sie" — but NEVER use it as formal "you"
- Example: "Wenn du deinen Blutdruck misst..." NOT "Wenn Sie Ihren Blutdruck messen..."
- Example: "in Absprache mit deinem Arzt" NOT "in Absprache mit Ihrem Arzt"

FRESH DATA:
- Today is ${currentDate}
- Use current year data UNLESS the custom instructions specify a different time period or year
- Prefer sources from the last 12 months UNLESS the custom instructions say otherwise

SOURCE QUALITY:
- NEVER use Reddit, forums, social media, or user-generated content as sources
- Only use professional, authoritative sources: medical associations, health organizations, company websites, research institutions, established health publications
- For German health content, prefer: Deutsche Hochdruckliga, Deutsche Herzstiftung, Beurer.com, Apotheken Umschau, NetDoktor, AOK, BZgA
- CRITICAL: You MUST populate the "Sources" field with 2-3 real URLs. Prefer fewer, high-quality sources.
- Each source REQUIRES ALL THREE fields: "title", "url", AND "description"
- The "description" field is MANDATORY - write 1-2 sentences explaining what insights, data, or analysis this specific source provides
- NEVER leave description empty or use generic text - explain the source's actual contribution to the article

FOOTNOTE FORMAT:
- When referencing a source in article text, use LETTERED superscripts: <sup>A</sup>, <sup>B</sup>, <sup>C</sup> etc.
- Do NOT use numbered superscripts (<sup>1</sup>, <sup>2</sup>) — Beurer uses numbers for campaigns.
- Letter A corresponds to the first source in the Sources list, B to the second, etc.
- Place the superscript immediately after the claim it supports, before any punctuation.

VOICE:
- Match the company's tone and voice persona exactly
- If voice_persona provided, every sentence should sound like that persona wrote it

CONTENT QUALITY:
- Be direct - no filler like "In today's rapidly evolving..."
- Vary section lengths (some long 500+ words, some shorter)
- Include 2+ of: decision frameworks, concrete scenarios, common mistakes, strong opinions
- Cite stats naturally inline: "According to [Source]'s report..."

CONTENT DEDUPLICATION:
- NEVER repeat the same fact, claim, statistic, or piece of advice in multiple sections.
- Each piece of information must appear exactly ONCE, in the most relevant section.
- If a fact is relevant to multiple sections, place it in the most directly applicable section and reference it briefly from others if needed.
- This applies across ALL content: sections, FAQ answers, PAA answers, and Direct_Answer.

FOCUS PRODUCTS (Prioritaet 1 — bevorzugt erwaehnen):
- Blutdruck Oberarm: BM 25, BM 27, BM 81
- TENS/EMS: EM 50 (NUR bei Menstruationsschmerzen), EM 55, EM 59, EM 89
- Infrarot: IL 50, IL 60
When the article topic is relevant to any of these products, prefer mentioning them over non-priority products. These are Beurer's current strategic focus products for the German market.
IMPORTANT: Only link products that match the article topic. The EM 50 is a menstrual pain device — do NOT link it in general back pain or TENS articles. For general pain/TENS articles, prefer EM 55, EM 59, or EM 89.

FORMATTING:
- HTML: <p>, <ul>, <li>, <ol>, <strong>, <em>
- Break up text: after 2-3 short paragraphs, add a list, example, or quote
- Each section needs visual variety - no section should be all paragraphs
- Lists: bullet points for 3+ related items, numbered for steps/rankings
- Tables for comparisons (use the tables field)
- Bold key terms and important phrases naturally`;
}

// ---------------------------------------------------------------------------
// User prompt template
// ---------------------------------------------------------------------------

function getUserPrompt(
  keyword: string,
  language: string,
  wordCount: number,
  customInstructions: string
): string {
  const country = language === "de" ? "Germany" : "United States";
  const companyContext = getCompanyContext();

  return `Write a comprehensive, engaging blog article.

TOPIC: ${keyword}

COMPANY CONTEXT:
${companyContext}

LOCALIZATION:
- Language: ${language}
- Country/Region: ${country}

PARAMETERS:
- Word count: ${wordCount}
- Sections: 4-6 content sections
- PAA: 4 People Also Ask questions with answers
- FAQ: 5-6 FAQ questions with answers
- Takeaways: 3 key takeaways

OPTIONAL (include when it enhances the article):
- tables: comparison tables for topics involving multiple options
- TLDR: 2-3 sentence summary for longer articles
- pros_cons: structured pros/cons for product reviews
- cta_text: specific call-to-action relevant to the topic and company
- related_keywords: secondary keywords naturally covered
- content_type: classify as "listicle", "how-to", "comparison", "guide", or "explainer"
- reading_time_min: estimated reading time

Create the best possible article for this topic, like a skilled human writer would.

${language !== "de" ? `CRITICAL LANGUAGE REQUIREMENT: Write the ENTIRE article in English.
Even if the keyword is in German, ALL output — Headline, Meta_Title, Meta_Description,
Intro, sections, FAQs, PAAs, key takeaways — MUST be in English.
Use only English-language sources (NHS, Mayo Clinic, Healthline, PubMed).
Do NOT cite German-language sources. Do NOT write in German.` : ""}

${customInstructions}

Return ONLY valid JSON matching this exact schema:
{
  "Headline": "Main headline with primary keyword (max 70 chars)",
  "Subtitle": "Optional sub-headline for context",
  "Teaser": "2-3 sentence hook highlighting pain point or benefit",
  "Direct_Answer": "40-60 word direct answer to the primary question (for featured snippets)",
  "Intro": "Opening paragraph (80-120 words) framing the problem",
  "Meta_Title": "SEO title max 55 chars with primary keyword",
  "Meta_Description": "SEO description max 130 chars with CTA",
  "section_01_title": "First section heading",
  "section_01_content": "<p>HTML content...</p>",
  "section_02_title": "Second section heading",
  "section_02_content": "<p>HTML content...</p>",
  "section_03_title": "Third section heading",
  "section_03_content": "<p>HTML content...</p>",
  "section_04_title": "Fourth section heading",
  "section_04_content": "<p>HTML content...</p>",
  "section_05_title": "",
  "section_05_content": "",
  "section_06_title": "",
  "section_06_content": "",
  "section_07_title": "",
  "section_07_content": "",
  "section_08_title": "",
  "section_08_content": "",
  "section_09_title": "",
  "section_09_content": "",
  "key_takeaway_01": "Key insight #1",
  "key_takeaway_02": "Key insight #2",
  "key_takeaway_03": "Key insight #3",
  "paa_01_question": "People Also Ask question #1",
  "paa_01_answer": "Concise answer",
  "paa_02_question": "",
  "paa_02_answer": "",
  "paa_03_question": "",
  "paa_03_answer": "",
  "paa_04_question": "",
  "paa_04_answer": "",
  "faq_01_question": "FAQ question #1",
  "faq_01_answer": "Detailed answer",
  "faq_02_question": "",
  "faq_02_answer": "",
  "faq_03_question": "",
  "faq_03_answer": "",
  "faq_04_question": "",
  "faq_04_answer": "",
  "faq_05_question": "",
  "faq_05_answer": "",
  "faq_06_question": "",
  "faq_06_answer": "",
  "TLDR": "2-3 sentence summary (optional)",
  "tables": [],
  "pros_cons": {"pros": [], "cons": []},
  "cta_text": "",
  "related_keywords": [],
  "content_type": "guide",
  "reading_time_min": 8,
  "Sources": [
    {"title": "Source Name", "url": "https://...", "description": "1-2 sentences explaining what this source provides"}
  ],
  "Search_Queries": "Q1: query used"
}

CRITICAL: The "Sources" field is MANDATORY with 2-3 real URLs, each with title, url, and description.`;
}

// ---------------------------------------------------------------------------
// JSON extraction helper
// ---------------------------------------------------------------------------

function extractJson(text: string): Record<string, any> {
  // Strip markdown code fences
  let cleaned = text.trim();
  if (cleaned.startsWith("```")) {
    cleaned = cleaned.replace(/^```(?:json)?\s*\n?/, "").replace(/\n?```\s*$/, "");
  }
  return JSON.parse(cleaned);
}

// ---------------------------------------------------------------------------
// Build instructions from social context
// ---------------------------------------------------------------------------

function buildInstructionsFromContext(
  socialContext: Record<string, any> | null,
  feedback?: string | null,
  globalRules?: string[]
): string {
  const parts: string[] = [];

  // Global rules from blog_global_rules table (highest priority)
  if (globalRules && globalRules.length > 0) {
    parts.push("KUNDENREGELN (vom Kunden vorgegeben — hoechste Prioritaet):");
    parts.push(...globalRules.map(r => `- ${r}`));
    parts.push("");
  }

  if (socialContext) {
    const contextLines: string[] = [];
    if (socialContext.emotion) contextLines.push(`- Nutzer-Emotion: ${socialContext.emotion}`);
    if (socialContext.intent) contextLines.push(`- Nutzer-Intention: ${socialContext.intent}`);
    if (socialContext.key_insight) contextLines.push(`- Zentrale Erkenntnis: ${socialContext.key_insight}`);
    if (socialContext.llm_opportunity) contextLines.push(`- Content-Chance: ${socialContext.llm_opportunity}`);
    if (socialContext.content_snippet) {
      const snippet = socialContext.content_snippet.slice(0, 200);
      contextLines.push(`- Originale Nutzerfrage: ${snippet}`);
    }
    if (socialContext.products && socialContext.products.length > 0) {
      contextLines.push(`- FOCUS PRODUCTS (mention these specific Beurer products in the article): ${socialContext.products.join(', ')}`);
    }
    if (socialContext.custom_notes) {
      contextLines.push(`- Additional brief/notes: ${socialContext.custom_notes}`);
    }
    if (contextLines.length) {
      parts.push("MANDATORY CUSTOM INSTRUCTIONS (follow these with highest priority):");
      parts.push("Context from social listening data:");
      parts.push(...contextLines);
    }
  }

  if (feedback) {
    parts.push("");
    parts.push(`USER FEEDBACK (incorporate into article): ${feedback}`);
  }

  return parts.join("\n");
}

// ---------------------------------------------------------------------------
// Count words in HTML
// ---------------------------------------------------------------------------

function countWordsInHtml(html: string): number {
  const plain = html.replace(/<[^>]+>/g, " ");
  return plain.split(/\s+/).filter(Boolean).length;
}

// ---------------------------------------------------------------------------
// Fetch author from Supabase
// ---------------------------------------------------------------------------

async function fetchAuthor(authorId: string): Promise<Record<string, any> | null> {
  try {
    const supabase = getSupabase();
    const { data } = await supabase
      .from("blog_authors")
      .select("name, title, bio, image_url, credentials, linkedin_url")
      .eq("id", authorId)
      .single();
    return data;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Generate article
// ---------------------------------------------------------------------------

export async function generateArticle(params: {
  articleId: string;
  sourceItemId: string;
  keyword: string;
  language?: string;
  wordCount?: number;
  socialContext?: Record<string, any> | null;
}): Promise<Record<string, any>> {
  const {
    articleId,
    sourceItemId,
    keyword,
    language = "de",
    wordCount = 1500,
    socialContext = null,
  } = params;

  const supabase = getSupabase();

  // Mark as generating
  await supabase
    .from("blog_articles")
    .update({ status: "generating", error_message: null, updated_at: new Date().toISOString() })
    .eq("id", articleId);

  try {
    const genAI = new GoogleGenerativeAI(getGeminiKey());
    const model = genAI.getGenerativeModel({
      model: GEMINI_MODEL,
      generationConfig: {
        temperature: 0.3,
        maxOutputTokens: 16384,
        responseMimeType: "application/json",
      },
      systemInstruction: getSystemInstruction(),
    });

    const globalRules = await fetchGlobalRules();
    const customInstructions = buildInstructionsFromContext(socialContext, null, globalRules);
    const prompt = getUserPrompt(keyword, language, wordCount, customInstructions);

    const result = await model.generateContent(prompt);
    const responseText = result.response.text();
    let articleJson = extractJson(responseText);

    // Verify source URLs — remove broken links (404s)
    articleJson = await verifySourceUrls(articleJson);

    // Fix LLM-generated spaced URLs (e.g. "https://www. beurer. com/...")
    fixSpacedUrlsInArticleJson(articleJson);

    // Fetch author if assigned
    const { data: articleRow } = await supabase
      .from("blog_articles")
      .select("author_id")
      .eq("id", articleId)
      .single();
    const author = articleRow?.author_id ? await fetchAuthor(articleRow.author_id) : null;

    // Render HTML
    let articleHtml = renderArticleHtml({
      article: articleJson,
      companyName: "Beurer",
      companyUrl: "https://www.beurer.com",
      language,
      category: socialContext?.category || "",
      author,
    });

    // Sanitize blocked internal links (Produktberater, App-Welt)
    articleHtml = sanitizeInternalLinks(articleHtml);
    articleHtml = absolutifyBeurerLinks(articleHtml);

    // Update DB
    const { data, error } = await supabase
      .from("blog_articles")
      .update({
        status: "completed",
        headline: articleJson.Headline || keyword,
        meta_title: articleJson.Meta_Title || "",
        meta_description: articleJson.Meta_Description || "",
        article_html: articleHtml,
        article_json: articleJson,
        word_count: countWordsInHtml(articleHtml),
        html_custom: false,
        error_message: null,
        updated_at: new Date().toISOString(),
      })
      .eq("id", articleId)
      .select()
      .single();

    if (error) throw new Error(error.message);
    return data;
  } catch (err: any) {
    // Mark as failed
    await supabase
      .from("blog_articles")
      .update({
        status: "failed",
        error_message: err.message || "Generation failed",
        updated_at: new Date().toISOString(),
      })
      .eq("id", articleId);
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Regenerate article
// ---------------------------------------------------------------------------

export async function regenerateArticle(params: {
  articleId: string;
  feedback?: string | null;
  fromScratch?: boolean;
}): Promise<Record<string, any>> {
  const { articleId, feedback = null, fromScratch = false } = params;
  const supabase = getSupabase();

  // Fetch existing article
  const { data: existing, error: fetchErr } = await supabase
    .from("blog_articles")
    .select("*")
    .eq("id", articleId)
    .single();
  if (fetchErr || !existing) throw new Error("Article not found");

  // Append to feedback_history — snapshot current HTML before overwriting
  const feedbackHistory = existing.feedback_history || [];
  const snapshotVersion = feedbackHistory.filter((e: any) => e.type === "snapshot").length + 1;
  feedbackHistory.push({
    type: "snapshot",
    version: snapshotVersion,
    headline: existing.headline || existing.keyword || "",
    article_html: existing.article_html || "",
    word_count: existing.word_count || 0,
    created_at: new Date().toISOString(),
  });
  if (feedback) {
    feedbackHistory.push({
      type: "feedback",
      comment: feedback,
      version: feedbackHistory.length,
      created_at: new Date().toISOString(),
    });
  }

  // Mark as regenerating
  await supabase
    .from("blog_articles")
    .update({
      status: "regenerating",
      feedback_history: feedbackHistory,
      error_message: null,
      updated_at: new Date().toISOString(),
    })
    .eq("id", articleId);

  try {
    const genAI = new GoogleGenerativeAI(getGeminiKey());
    const model = genAI.getGenerativeModel({
      model: GEMINI_MODEL,
      generationConfig: {
        temperature: 0.3,
        maxOutputTokens: 16384,
        responseMimeType: "application/json",
      },
      systemInstruction: getSystemInstruction(),
    });

    const globalRules = await fetchGlobalRules();
    const customInstructions = buildInstructionsFromContext(
      existing.social_context,
      feedback,
      globalRules
    );
    const prompt = getUserPrompt(
      existing.keyword,
      existing.language || "de",
      existing.word_count || 1500,
      customInstructions
    );

    const result = await model.generateContent(prompt);
    const responseText = result.response.text();
    let articleJson = extractJson(responseText);

    // Verify source URLs — remove broken links (404s)
    articleJson = await verifySourceUrls(articleJson);

    // Fix LLM-generated spaced URLs (e.g. "https://www. beurer. com/...")
    fixSpacedUrlsInArticleJson(articleJson);

    // Fetch author
    const author = existing.author_id ? await fetchAuthor(existing.author_id) : null;

    // Render HTML
    let articleHtml = renderArticleHtml({
      article: articleJson,
      companyName: "Beurer",
      companyUrl: "https://www.beurer.com",
      language: existing.language || "de",
      category: existing.social_context?.category || "",
      author,
    });

    // Sanitize blocked internal links (Produktberater, App-Welt)
    articleHtml = sanitizeInternalLinks(articleHtml);
    articleHtml = absolutifyBeurerLinks(articleHtml);

    // Update DB
    const { data, error } = await supabase
      .from("blog_articles")
      .update({
        status: "completed",
        headline: articleJson.Headline || existing.keyword,
        meta_title: articleJson.Meta_Title || "",
        meta_description: articleJson.Meta_Description || "",
        article_html: articleHtml,
        article_json: articleJson,
        word_count: countWordsInHtml(articleHtml),
        html_custom: false,
        feedback_history: feedbackHistory,
        error_message: null,
        updated_at: new Date().toISOString(),
      })
      .eq("id", articleId)
      .select()
      .single();

    if (error) throw new Error(error.message);
    return data;
  } catch (err: any) {
    await supabase
      .from("blog_articles")
      .update({
        status: "failed",
        error_message: err.message || "Regeneration failed",
        updated_at: new Date().toISOString(),
      })
      .eq("id", articleId);
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Fetch global content rules from Supabase
// ---------------------------------------------------------------------------

async function fetchGlobalRules(): Promise<string[]> {
  try {
    const supabase = getSupabase();
    const { data } = await supabase
      .from("blog_global_rules")
      .select("rule_text")
      .eq("active", true);
    if (data && data.length > 0) {
      return data.map((r: any) => r.rule_text).filter(Boolean);
    }
  } catch {
    // Table may not exist — non-blocking
  }
  return [];
}

// ---------------------------------------------------------------------------
// Sanitize internal links (block Produktberater / App-Welt)
// ---------------------------------------------------------------------------

const BLOCKED_LINK_PATTERNS = ["/produktberater", "/app-welt/"];

// Map blocked patterns to preferred category page replacements
const PRODUKTBERATER_CATEGORY_MAP: Record<string, string> = {
  blutdruck: "https://www.beurer.com/de/c/0010101/",
  tens: "https://www.beurer.com/de/c/0010401/",
  ems: "https://www.beurer.com/de/c/0010402/",
  infrarot: "https://www.beurer.com/de/c/0010302/",
  waerme: "https://www.beurer.com/de/c/00201/",
};

function sanitizeInternalLinks(html: string): string {
  // Match <a> tags whose href contains a blocked pattern
  return html.replace(
    /<a\s+([^>]*?)href=["']([^"']+)["']([^>]*)>(.*?)<\/a>/gi,
    (fullMatch, before, href, after, linkText) => {
      const hrefLower = href.toLowerCase();
      const isBlocked = BLOCKED_LINK_PATTERNS.some((pat) => hrefLower.includes(pat));
      if (!isBlocked) return fullMatch;

      // Try to find a category replacement based on surrounding text
      const context = (linkText + " " + href).toLowerCase();
      for (const [keyword, categoryUrl] of Object.entries(PRODUKTBERATER_CATEGORY_MAP)) {
        if (context.includes(keyword)) {
          return `<a ${before}href="${categoryUrl}"${after}>${linkText}</a>`;
        }
      }

      // No matching category — strip the link, keep the text
      return linkText.replace(/<[^>]+>/g, "");
    }
  );
}

/**
 * Convert relative /de/... links to absolute https://www.beurer.com/de/... URLs.
 * The LLM sometimes generates relative paths that resolve to localhost in the dashboard.
 */
function absolutifyBeurerLinks(html: string): string {
  return html.replace(
    /href=["'](\/de\/[^"']+)["']/gi,
    (_, path) => `href="https://www.beurer.com${path}"`
  );
}

// ---------------------------------------------------------------------------
// Verify source URLs (filter out 404s)
// ---------------------------------------------------------------------------

async function verifySourceUrls(
  articleJson: Record<string, any>
): Promise<Record<string, any>> {
  const sources: Array<{ title: string; url: string; description?: string }> =
    articleJson.Sources;
  if (!Array.isArray(sources) || sources.length === 0) return articleJson;

  const verified: typeof sources = [];

  for (const source of sources) {
    if (!source.url) continue;
    try {
      const res = await fetch(source.url, {
        method: "HEAD",
        redirect: "follow",
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) {
        verified.push(source);
      } else {
        console.warn(`Source URL returned ${res.status}, removing: ${source.url}`);
      }
    } catch {
      // Network error or timeout — remove the source
      console.warn(`Source URL unreachable, removing: ${source.url}`);
    }
  }

  return { ...articleJson, Sources: verified };
}

// ---------------------------------------------------------------------------
// Inline edits
// ---------------------------------------------------------------------------

export async function applyInlineEdits(params: {
  articleId: string;
  edits: Array<{ passage_text: string; comment: string }>;
}): Promise<Record<string, any>> {
  const { articleId, edits } = params;
  const supabase = getSupabase();

  // Fetch existing article
  const { data: existing, error: fetchErr } = await supabase
    .from("blog_articles")
    .select("article_html, language, feedback_history")
    .eq("id", articleId)
    .single();
  if (fetchErr || !existing) throw new Error("Article not found");
  if (!existing.article_html) throw new Error("Article has no HTML content");

  const html = existing.article_html as string;
  const lang = existing.language || "de";

  // Map passage_text to actual HTML passages
  const plainText = html.replace(/<[^>]+>/g, "");
  const resolvedEdits: Array<{ editNumber: number; passage: string; comment: string }> = [];

  for (let i = 0; i < edits.length; i++) {
    const { passage_text, comment } = edits[i];
    // Find the passage in plain text, then locate it in HTML
    const plainIdx = plainText.indexOf(passage_text);
    if (plainIdx === -1) {
      // Try case-insensitive or partial match
      resolvedEdits.push({ editNumber: i + 1, passage: passage_text, comment });
    } else {
      // Use the passage_text directly since it may span HTML tags
      resolvedEdits.push({ editNumber: i + 1, passage: passage_text, comment });
    }
  }

  // Fetch global rules for tone/voice guidance
  const globalRules = await fetchGlobalRules();
  const rulesBlock = globalRules.length > 0
    ? `\nGLOBAL CONTENT RULES (must follow):\n${globalRules.map((r) => `- ${r}`).join("\n")}\n`
    : "";

  // Build prompt for Gemini — match existing article tone, don't hardcode Sie/du
  const langInstruction =
    lang === "de"
      ? "Write the revised text in German. IMPORTANT: Match the tone and form of address (Sie-Form or du-Form) used in the surrounding article text exactly. Do NOT switch between formal and informal address."
      : "Write the revised text in English.";

  const editsBlock = resolvedEdits
    .map(
      (e) =>
        `Edit #${e.editNumber}:\nOriginal passage: "${e.passage}"\nFeedback: "${e.comment}"`
    )
    .join("\n\n");

  const prompt = `You are editing specific passages in a blog article based on user feedback.
For each edit below, produce a revised version of the passage that addresses the user's comment.
${langInstruction}
${rulesBlock}
RULES:
- Revised text must be approximately the same length as the original (within 30%). Do not truncate or drastically shorten.
- Revised text must be grammatically complete and connect naturally to the surrounding content.
- Preserve ALL HTML tags from the original passage. Do not drop <strong>, <a>, <em>, etc.
- Never return a truncated or partial sentence as the revision.
- Keep the same tone, style, and form of address as the original article.
- Read the surrounding article text carefully to determine the correct tone before writing.

ARTICLE CONTEXT (for tone reference):
${html.replace(/<[^>]+>/g, " ").slice(0, 1500)}

${editsBlock}

Return ONLY a JSON array (no markdown fences) where each element is an object with "edit_number" (int) and "revised" (string).
Example: [{"edit_number": 1, "revised": "The revised passage text."}]`;

  const genAI = new GoogleGenerativeAI(getGeminiKey());
  const model = genAI.getGenerativeModel({
    model: GEMINI_MODEL,
    generationConfig: {
      temperature: 0.3,
      maxOutputTokens: 4096,
      responseMimeType: "application/json",
    },
  });

  const result = await model.generateContent(prompt);
  const responseText = result.response.text();
  const revisions: Array<{ edit_number: number; revised: string }> = JSON.parse(
    responseText.replace(/^```(?:json)?\s*\n?/, "").replace(/\n?```\s*$/, "")
  );

  // Apply replacements
  let updatedHtml = html;
  let appliedCount = 0;

  for (const rev of revisions) {
    const edit = resolvedEdits.find((e) => e.editNumber === rev.edit_number);
    if (!edit) continue;

    // Try direct match first
    if (updatedHtml.includes(edit.passage)) {
      updatedHtml = updatedHtml.replace(edit.passage, rev.revised);
      appliedCount++;
    } else {
      // For multi-paragraph selections: the passage is plain text with newlines,
      // but the HTML has tags between paragraphs. Build a regex that matches
      // the passage text with any HTML tags in between.
      const words = edit.passage.split(/\s+/).filter(Boolean);
      if (words.length >= 2) {
        // Escape regex special chars in each word, allow HTML tags + whitespace between words
        const pattern = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("(?:\\s|<[^>]*>)+");
        const re = new RegExp(pattern);
        const match = updatedHtml.match(re);
        if (match) {
          updatedHtml = updatedHtml.replace(match[0], rev.revised);
          appliedCount++;
        }
      }
    }
  }

  // Build changes array for diff visualization
  const changes: { edit_number: number; original_snippet: string; revised_snippet: string }[] = [];
  for (const rev of revisions) {
    const edit = resolvedEdits.find((e) => e.editNumber === rev.edit_number);
    if (edit) {
      changes.push({
        edit_number: rev.edit_number,
        original_snippet: edit.passage,
        revised_snippet: rev.revised,
      });
    }
  }

  // Sanitize any blocked internal links (Produktberater, App-Welt)
  updatedHtml = sanitizeInternalLinks(updatedHtml);
  updatedHtml = absolutifyBeurerLinks(updatedHtml);

  // Update feedback history
  const feedbackHistory = existing.feedback_history || [];
  feedbackHistory.push({
    type: "inline_edit",
    comment: `Inline edits (${appliedCount}): ${edits.map((e) => `"${e.passage_text.slice(0, 30)}..." → ${e.comment}`).join("; ")}`,
    edits_applied: appliedCount,
    changes,
    old_article_html: existing.article_html || "",
    created_at: new Date().toISOString(),
    version: feedbackHistory.length + 1,
  });

  // Save
  const { data, error } = await supabase
    .from("blog_articles")
    .update({
      article_html: updatedHtml,
      html_custom: true,
      feedback_history: feedbackHistory,
      updated_at: new Date().toISOString(),
    })
    .eq("id", articleId)
    .select()
    .single();

  if (error) throw new Error(error.message);
  return data;
}
