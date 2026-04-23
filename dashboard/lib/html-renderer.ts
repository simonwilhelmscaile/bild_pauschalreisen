/**
 * HTML Renderer - Port of blog/shared/html_renderer.py
 *
 * Renders ArticleOutput JSON to semantic HTML5 page with Beurer CI styling.
 */

const GERMAN_MONTHS = [
  "", "Januar", "Februar", "März", "April", "Mai", "Juni",
  "Juli", "August", "September", "Oktober", "November", "Dezember",
];

const ENGLISH_MONTHS = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const ARTICLE_LABELS: Record<string, Record<string, string>> = {
  de: {
    toc: "Inhaltsverzeichnis",
    takeaways: "Das Wichtigste in Kürze",
    faq: "Häufig gestellte Fragen",
    paa: "Weitere Fragen",
    sources: "Quellen",
    direct_answer: "Das Wichtigste in Kürze:",
    reading_time: "Min. Lesezeit",
    last_updated: "Zuletzt aktualisiert:",
    medical_review: "Medizinisch geprüft von:",
    image_placeholder: "Bild-Platzhalter",
  },
  en: {
    toc: "Table of Contents",
    takeaways: "Key Takeaways",
    faq: "Frequently Asked Questions",
    paa: "Related Questions",
    sources: "Sources",
    direct_answer: "Short Answer:",
    reading_time: "min read",
    last_updated: "Last updated:",
    medical_review: "Medically reviewed by:",
    image_placeholder: "Image placeholder",
  },
};

function L(language: string, key: string): string {
  return (ARTICLE_LABELS[language] || ARTICLE_LABELS.de)[key] || ARTICLE_LABELS.de[key];
}

const ICON_CALENDAR = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`;
const ICON_CLOCK = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
const ICON_AUTHOR = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>`;

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function stripHtml(text: string): string {
  if (!text) return "";
  return text.replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#039;/g, "'").trim();
}

function sanitizeHtml(html: string): string {
  if (!html) return "";
  let s = html;
  s = s.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "");
  s = s.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "");
  s = s.replace(/<iframe[^>]*>[\s\S]*?<\/iframe>/gi, "");
  s = s.replace(/<iframe[^>]*\/>/gi, "");
  s = s.replace(/<object[^>]*>[\s\S]*?<\/object>/gi, "");
  s = s.replace(/<embed[^>]*\/?>/gi, "");
  s = s.replace(/<form[^>]*>[\s\S]*?<\/form>/gi, "");
  s = s.replace(/\s*on\w+\s*=\s*["'][^"']*["']/gi, "");
  s = s.replace(/\s*on\w+\s*=\s*\S+/gi, "");
  s = s.replace(/href\s*=\s*["']javascript:[^"']*["']/gi, 'href="#"');
  s = s.replace(/src\s*=\s*["']javascript:[^"']*["']/gi, 'src=""');
  return s;
}

/** Fix URLs with spaces injected by LLM (e.g. "https://www. beurer. com/") */
function fixSpacedUrls(html: string): string {
  return html.replace(/href="([^"]+)"/g, (match, url) => {
    const fixed = url.replace(/\s+/g, "");
    return fixed !== url ? `href="${fixed}"` : match;
  });
}

function estimateReadingTime(article: Record<string, any>): number {
  const parts: string[] = [];
  parts.push(article.Intro || "");
  parts.push(article.Direct_Answer || "");
  for (let i = 1; i <= 9; i++) {
    parts.push(article[`section_${String(i).padStart(2, "0")}_content`] || "");
  }
  for (let i = 1; i <= 3; i++) {
    parts.push(article[`key_takeaway_${String(i).padStart(2, "0")}`] || "");
  }
  for (let i = 1; i <= 6; i++) {
    parts.push(article[`faq_${String(i).padStart(2, "0")}_answer`] || "");
  }
  for (let i = 1; i <= 4; i++) {
    parts.push(article[`paa_${String(i).padStart(2, "0")}_answer`] || "");
  }
  const combined = parts.filter(Boolean).join(" ");
  const plain = combined.replace(/<[^>]+>/g, "");
  const wordCount = plain.split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(wordCount / 200));
}

interface Source {
  title?: string;
  url?: string;
  description?: string;
}

interface Author {
  name?: string;
  title?: string;
  bio?: string;
  image_url?: string;
  credentials?: string[];
  linkedin_url?: string;
}

interface RenderOptions {
  article: Record<string, any>;
  companyName?: string;
  companyUrl?: string;
  authorName?: string;
  language?: string;
  category?: string;
  author?: Author | null;
  lastUpdated?: string;
}

export function renderArticleHtml(opts: RenderOptions): string {
  const {
    article,
    companyName = "Beurer",
    companyUrl = "https://www.beurer.com",
    authorName = "",
    language = "de",
    category = "",
    author = null,
    lastUpdated,
  } = opts;

  const headline = stripHtml(article.Headline || "Untitled");
  const teaser = stripHtml(article.Teaser || "");
  const intro = article.Intro || "";
  const metaTitle = stripHtml(article.Meta_Title || headline);
  const metaDesc = stripHtml(article.Meta_Description || teaser);
  const directAnswer = article.Direct_Answer || "";
  const sources: Source[] = article.Sources || [];

  const authorDisplay = authorName || author?.name || companyName || "Author";

  // Images
  const heroImage = article.image_01_url || "";
  let defaultAlt = `Image for ${headline}`;
  if (defaultAlt.length > 125) defaultAlt = defaultAlt.slice(0, 122) + "...";
  const heroAlt = article.image_01_alt_text || defaultAlt;
  const midImage = article.image_02_url || "";
  const midAlt = article.image_02_alt_text || "";
  const bottomImage = article.image_03_url || "";
  const bottomAlt = article.image_03_alt_text || "";

  // Date
  const months = language === 'de' ? GERMAN_MONTHS : ENGLISH_MONTHS;
  const now = new Date();
  const pubDate = now.toISOString().slice(0, 10);
  const displayDate = language === 'de'
    ? `${now.getDate()}. ${months[now.getMonth() + 1]} ${now.getFullYear()}`
    : `${months[now.getMonth() + 1]} ${now.getDate()}, ${now.getFullYear()}`;

  let lastUpdatedDisplay = displayDate;
  if (lastUpdated) {
    try {
      const lu = new Date(lastUpdated);
      lastUpdatedDisplay = language === 'de'
        ? `${lu.getDate()}. ${months[lu.getMonth() + 1]} ${lu.getFullYear()}`
        : `${months[lu.getMonth() + 1]} ${lu.getDate()}, ${lu.getFullYear()}`;
    } catch {
      lastUpdatedDisplay = lastUpdated;
    }
  }

  const readingMin = estimateReadingTime(article);

  // Category badge
  const CATEGORY_LABELS: Record<string, string> = {
    blood_pressure: "Blutdruck",
    pain_tens: "Schmerz/TENS",
    infrarot: "Infrarot/Wärme",
    menstrual: "Menstruation",
    other: "Sonstige",
  };
  const categoryLabel = CATEGORY_LABELS[category] || "";
  const categoryHtml = categoryLabel ? `<span class="category-badge">${esc(categoryLabel)}</span>` : "";

  // Sections
  const sectionsParts: string[] = [];
  for (let i = 1; i <= 9; i++) {
    const idx = String(i).padStart(2, "0");
    const title = article[`section_${idx}_title`] || "";
    const content = article[`section_${idx}_content`] || "";
    if (!title && !content) continue;
    if (title) {
      const cleanTitle = stripHtml(title);
      sectionsParts.push(`<h2 id="section-${i}">${esc(cleanTitle)}</h2>`);
    }
    if (content && content.trim()) {
      let sanitized = sanitizeHtml(content);
      sanitized = sanitized.replace(/(?<!comparison-table">)(<table[\s\S]*?<\/table>)/g, '<div class="comparison-table">$1</div>');
      sectionsParts.push(sanitized);
    }
    if (i === 3 && midImage) {
      const cap = midAlt ? `<figcaption>${esc(midAlt)}</figcaption>` : "";
      sectionsParts.push(`<figure><img src="${esc(midImage)}" alt="${esc(midAlt)}" class="inline-image">${cap}</figure>`);
    }
  }
  const sectionsHtml = sectionsParts.join("\n");

  // Hero image
  let heroFigure = "";
  if (heroImage) {
    const cap = heroAlt && heroAlt !== defaultAlt ? `<figcaption>${esc(heroAlt)}</figcaption>` : "";
    heroFigure = `<figure><img src="${esc(heroImage)}" alt="${esc(heroAlt)}" class="hero-image">${cap}</figure>`;
  } else {
    heroFigure = renderImagePlaceholder(heroAlt || headline, true);
  }

  // Bottom image
  let bottomImageHtml = "";
  if (bottomImage) {
    const cap = bottomAlt ? `<figcaption>${esc(bottomAlt)}</figcaption>` : "";
    bottomImageHtml = `<figure><img src="${esc(bottomImage)}" alt="${esc(bottomAlt || defaultAlt)}" class="inline-image">${cap}</figure>`;
  }

  // Direct answer
  const directHtml = directAnswer
    ? `<div class="direct-answer"><strong>${L(language, 'direct_answer')}</strong> ${sanitizeHtml(directAnswer)}</div>`
    : "";

  // Intro
  const introHtml = intro ? `<div class="intro">${sanitizeHtml(intro)}</div>` : "";

  // TOC
  const tocItems: string[] = [];
  for (let i = 1; i <= 9; i++) {
    const title = article[`section_${String(i).padStart(2, "0")}_title`] || "";
    if (title) {
      const cleanTitle = stripHtml(title);
      const words = cleanTitle.split(/\s+/).slice(0, 8);
      let shortTitle = words.join(" ");
      if (words.length < cleanTitle.split(/\s+/).length) shortTitle += " ...";
      tocItems.push(`<li><a href="#section-${i}">${esc(shortTitle)}</a></li>`);
    }
  }
  const tocHtml = tocItems.length
    ? `<nav class="toc"><h2>${L(language, 'toc')}</h2><ol>${tocItems.join("")}</ol></nav>`
    : "";

  // Takeaways
  const takeawayItems: string[] = [];
  for (let i = 1; i <= 3; i++) {
    const t = article[`key_takeaway_${String(i).padStart(2, "0")}`] || "";
    if (t) takeawayItems.push(`<li>${esc(t)}</li>`);
  }
  const takeawaysHtml = takeawayItems.length
    ? `<section class="takeaways"><h2>${L(language, 'takeaways')}</h2><ul>${takeawayItems.join("")}</ul></section>`
    : "";

  // FAQ
  const faqItems: string[] = [];
  for (let i = 1; i <= 6; i++) {
    const idx = String(i).padStart(2, "0");
    const q = article[`faq_${idx}_question`] || "";
    const a = article[`faq_${idx}_answer`] || "";
    if (q && a) faqItems.push(`<div class="faq-item"><h3>${esc(q)}</h3><p>${esc(a)}</p></div>`);
  }
  const faqHtml = faqItems.length
    ? `<section class="faq"><h2>${L(language, 'faq')}</h2>${faqItems.join("")}</section>`
    : "";

  // PAA
  const paaItems: string[] = [];
  for (let i = 1; i <= 4; i++) {
    const idx = String(i).padStart(2, "0");
    const q = article[`paa_${idx}_question`] || "";
    const a = article[`paa_${idx}_answer`] || "";
    if (q && a) paaItems.push(`<div class="paa-item"><h3>${esc(q)}</h3><p>${esc(a)}</p></div>`);
  }
  const paaHtml = paaItems.length
    ? `<section class="paa"><h2>${L(language, 'paa')}</h2>${paaItems.join("")}</section>`
    : "";

  // Sources
  let sourcesHtml = "";
  if (Array.isArray(sources) && sources.length > 0) {
    const sourceItems = sources
      .filter((s) => s.url)
      .map((s) => {
        const displayTitle = s.title && s.title.length > 2 ? s.title : s.url!;
        const descHtml = s.description ? `<div class="source-description">${esc(s.description)}</div>` : "";
        return `<li><a href="${esc(s.url!)}" target="_blank" rel="noopener noreferrer">${esc(displayTitle)}</a>${descHtml}</li>`;
      });
    if (sourceItems.length) {
      sourcesHtml = `<section class="sources"><h2>${L(language, 'sources')}</h2><ol class="sources-list" type="A">${sourceItems.join("")}</ol></section>`;
    }
  }

  // Tables
  let tablesHtml = "";
  const tables = article.tables || [];
  if (Array.isArray(tables) && tables.length > 0) {
    const tableParts = tables
      .filter((t: any) => t.headers?.length && t.rows?.length)
      .map((t: any) => {
        const headerHtml = t.headers.map((h: string) => `<th>${esc(h)}</th>`).join("");
        const rowsHtml = t.rows
          .map((row: string[]) => `<tr>${row.map((c: string) => `<td>${esc(String(c))}</td>`).join("")}</tr>`)
          .join("");
        return `<div class="comparison-table"><h3>${esc(t.title || "")}</h3><table><thead><tr>${headerHtml}</tr></thead><tbody>${rowsHtml}</tbody></table></div>`;
      });
    tablesHtml = tableParts.join("\n");
  }

  // Meta bar
  const metaHtml = `<div class="meta"><span class="meta-item">${ICON_CALENDAR} ${displayDate}</span><span class="meta-item">${ICON_CLOCK} ${readingMin} ${L(language, 'reading_time')}</span><span class="meta-item">${ICON_AUTHOR} ${esc(authorDisplay)}</span></div>`;

  // Last updated
  let lastUpdatedHtml = `<div class="last-updated"><strong>${L(language, 'last_updated')}</strong> ${lastUpdatedDisplay}`;
  if (author?.name) {
    lastUpdatedHtml += ` &middot; <strong>${L(language, 'medical_review')}</strong> ${esc(author.name)}`;
  }
  lastUpdatedHtml += "</div>";

  // Author card
  const authorCardHtml = renderAuthorCard(author);

  return fixSpacedUrls(`<!DOCTYPE html>
<html lang="${esc(language)}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${esc(metaTitle)}</title>
    <meta name="description" content="${esc(metaDesc)}">
    <meta name="author" content="${esc(authorDisplay)}">
    <meta property="og:title" content="${esc(metaTitle)}">
    <meta property="og:description" content="${esc(metaDesc)}">
    <meta property="og:type" content="article">
    ${heroImage ? `<meta property="og:image" content="${esc(heroImage)}">` : ""}
    <link href="https://fonts.cdnfonts.com/css/nexa-bold" rel="stylesheet">
    <style>
        :root {
            --primary: #C50050;
            --text: #212529;
            --text-light: #737373;
            --bg: #ffffff;
            --bg-light: #F7F7F7;
            --border: #E5E5E5;
            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-sm: 8px;
            --shadow: 0 4px 20px rgba(0,0,0,0.08);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: "Nexa", "Inter", "Helvetica Neue", Arial, system-ui, sans-serif;
            font-weight: 300; font-size: 17px; line-height: 1.7;
            color: var(--text); background: var(--bg);
            -webkit-font-smoothing: antialiased;
        }
        strong, b { font-weight: 700; }
        a { color: inherit; }
        .container { max-width: 820px; margin: 0 auto; padding: clamp(24px, 4vw, 48px) 20px; }
        .category-badge { display: inline-block; color: #C50050; font-size: .8rem; font-weight: 800; text-transform: uppercase; letter-spacing: .03em; margin-bottom: 8px; }
        h1 { font-size: clamp(2.2rem, 3vw + 1rem, 3.2rem); font-weight: 700; line-height: 1.1; letter-spacing: -0.02em; margin-bottom: 20px; }
        .direct-answer { font-size: 1.05em; line-height: 1.7; margin-bottom: 32px; }
        .direct-answer p { margin-bottom: 0; display: inline; }
        figure { margin: 0 0 32px; }
        figure img { width: 100%; height: auto; display: block; }
        .hero-image { border-radius: var(--radius-md); }
        figcaption { font-size: 0.85em; color: var(--text-light); margin-top: 10px; line-height: 1.4; }
        .takeaways { margin: 32px 0; padding: 28px 32px; background: var(--bg-light); border: 1px solid var(--border); border-radius: var(--radius-md); }
        .takeaways h2 { font-size: 0.8em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 20px; }
        .takeaways ul { list-style: none; }
        .takeaways li { margin: 14px 0; padding-left: 22px; position: relative; line-height: 1.6; }
        .takeaways li::before { content: ""; position: absolute; left: 0; top: 10px; width: 8px; height: 8px; background: var(--text-light); border-radius: 50%; }
        .meta { display: flex; align-items: center; flex-wrap: wrap; gap: 20px; padding: 16px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); margin: 32px 0; font-size: 0.88em; color: var(--text-light); }
        .meta-item { display: inline-flex; align-items: center; gap: 6px; }
        .meta-item svg { flex-shrink: 0; opacity: 0.7; }
        .toc { margin: 0 0 40px; padding-bottom: 32px; border-bottom: 1px solid var(--border); }
        .toc h2 { font-size: 1em; font-weight: 700; font-style: italic; margin-bottom: 16px; }
        .toc ol { list-style: decimal; padding-left: 24px; margin: 0; }
        .toc li { padding: 5px 0; font-size: 1.05em; font-weight: 600; }
        .toc li::marker { font-weight: 700; }
        .toc a { color: var(--text); text-decoration: none; }
        .intro { font-size: 1.05em; margin-bottom: 32px; padding: 24px 28px; background: var(--bg-light); border: 1px solid var(--border); border-radius: var(--radius-md); }
        .intro p { margin-bottom: 12px; }
        .intro p:last-child { margin-bottom: 0; }
        article { margin-top: 0; }
        article h2 { font-size: clamp(1.7rem, 1.5vw + 1rem, 2.2rem); font-weight: 700; line-height: 1.15; letter-spacing: -0.01em; margin: 48px 0 12px; }
        article h2:first-child { margin-top: 0; }
        article h3 { font-size: clamp(1.15rem, 0.8vw + 0.9rem, 1.45rem); font-weight: 700; margin: 28px 0 8px; }
        article p { margin-bottom: 12px; }
        article ul, article ol { margin: 12px 0 12px 24px; }
        article li { margin: 6px 0; line-height: 1.6; }
        article a { color: var(--primary); text-decoration: underline; text-underline-offset: 2px; text-decoration-color: rgba(197,0,80,0.3); text-decoration-thickness: 1px; }
        article a:hover { text-decoration-color: var(--primary); }
        article sup { font-size: 0.7em; line-height: 0; position: relative; vertical-align: baseline; top: -0.5em; }
        .inline-image { width: 100%; height: auto; border-radius: var(--radius-md); }
        blockquote { margin: 24px 0; padding: 20px 24px; background: var(--bg-light); border-left: 4px solid var(--primary); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
        blockquote p { margin-bottom: 8px; }
        blockquote p:last-child { margin-bottom: 0; }
        .sources { margin: 48px 0 0; padding-top: 24px; border-top: 1px solid var(--border); }
        .sources h2 { font-size: 1em; font-weight: 700; margin-bottom: 12px; }
        .sources ol { margin: 0 0 0 20px; font-size: 0.88em; color: var(--text-light); }
        .sources li { margin: 8px 0; line-height: 1.5; }
        .sources a { color: var(--text-light); text-decoration: underline; text-underline-offset: 2px; }
        .source-description { color: var(--text-light); font-size: 0.92em; margin-top: 2px; }
        .faq, .paa { margin: 40px 0; }
        .faq h2, .paa h2 { font-size: 1.4em; font-weight: 700; margin-bottom: 20px; }
        .faq-item, .paa-item { margin: 12px 0; padding: 20px 24px; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-md); }
        .faq-item h3, .paa-item h3 { font-size: 1.02em; font-weight: 700; margin-bottom: 8px; color: var(--text); }
        .faq-item p, .paa-item p { color: var(--text-light); font-size: 0.95em; line-height: 1.6; }
        .image-placeholder { display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 12px; background: var(--bg-light); border: 2px dashed var(--border); border-radius: var(--radius-md); padding: 48px 24px; margin: 0 0 32px; color: var(--text-light); font-size: 0.9em; min-height: 200px; }
        .image-placeholder.hero { min-height: 320px; border-radius: var(--radius-lg); }
        .image-placeholder svg { opacity: 0.4; }
        .image-placeholder span { max-width: 400px; text-align: center; line-height: 1.4; }
        .last-updated { font-size: 0.85em; color: var(--text-light); padding: 12px 0; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
        .author-card { display: flex; gap: 20px; margin: 48px 0 0; padding: 28px; background: var(--bg-light); border: 1px solid var(--border); border-radius: var(--radius-md); }
        .author-card-image { flex-shrink: 0; width: 80px; height: 80px; border-radius: 50%; overflow: hidden; background: var(--border); display: flex; align-items: center; justify-content: center; }
        .author-card-image img { width: 100%; height: 100%; object-fit: cover; }
        .author-card-image svg { opacity: 0.4; }
        .author-card-info { flex: 1; min-width: 0; }
        .author-card-info h4 { font-size: 1.05em; font-weight: 700; margin-bottom: 2px; }
        .author-card-title { font-size: 0.88em; color: var(--text-light); margin-bottom: 8px; }
        .author-card-bio { font-size: 0.92em; line-height: 1.5; color: var(--text); margin-bottom: 12px; }
        .author-credentials { display: flex; flex-wrap: wrap; gap: 8px; }
        .credential-badge { display: inline-block; font-size: 0.78em; font-weight: 600; padding: 4px 10px; background: var(--bg); border: 1px solid var(--border); border-radius: 20px; color: var(--text-light); }
        .author-card-links { display: flex; gap: 12px; margin-top: 8px; }
        .author-card-links a { color: var(--text-light); text-decoration: none; display: inline-flex; align-items: center; gap: 4px; font-size: 0.85em; }
        .comparison-table { margin: 32px 0; border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; }
        .comparison-table h3 { font-size: 1.05em; font-weight: 700; padding: 16px 20px 8px; }
        .comparison-table table { width: 100%; border-collapse: collapse; font-size: 0.92em; }
        .comparison-table th, .comparison-table td { padding: 12px 16px; text-align: left; }
        .comparison-table th { background: #FAFAFA; font-weight: 700; border-bottom: 2px solid var(--border); }
        .comparison-table td { border-bottom: 1px solid var(--border); }
        .comparison-table tr:last-child td { border-bottom: none; }
    </style>
</head>
<body>
    <header class="container">
        ${categoryHtml}
        <h1>${esc(headline)}</h1>
        ${directHtml}
    </header>
    <main class="container">
        ${heroFigure}
        ${takeawaysHtml}
        ${metaHtml}
        ${lastUpdatedHtml}
        ${tocHtml}
        ${introHtml}
        <article>${sectionsHtml}</article>
        ${bottomImageHtml}
        ${tablesHtml}
        ${paaHtml}
        ${faqHtml}
        ${sourcesHtml}
        ${authorCardHtml}
    </main>
</body>
</html>`);
}

function renderImagePlaceholder(altText: string, isHero = false): string {
  const heroClass = isHero ? " hero" : "";
  const icon = `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>`;
  const label = altText ? esc(altText) : "Bild-Platzhalter";
  return `<div class="image-placeholder${heroClass}">${icon}<span>${label}</span></div>`;
}

function renderAuthorCard(author: Author | null | undefined): string {
  if (!author?.name) return "";
  const name = esc(author.name);
  const imageHtml = author.image_url
    ? `<img src="${esc(author.image_url)}" alt="${name}">`
    : `<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;
  const titleHtml = author.title ? `<div class="author-card-title">${esc(author.title)}</div>` : "";
  const bioHtml = author.bio ? `<p class="author-card-bio">${esc(author.bio)}</p>` : "";
  const credsHtml = author.credentials?.length
    ? `<div class="author-credentials">${author.credentials.map((c) => `<span class="credential-badge">${esc(c)}</span>`).join("")}</div>`
    : "";
  const linksHtml = author.linkedin_url
    ? `<div class="author-card-links"><a href="${esc(author.linkedin_url)}" target="_blank" rel="noopener noreferrer">LinkedIn</a></div>`
    : "";
  return `<div class="author-card"><div class="author-card-image">${imageHtml}</div><div class="author-card-info"><h4>${name}</h4>${titleHtml}${bioHtml}${credsHtml}${linksHtml}</div></div>`;
}
