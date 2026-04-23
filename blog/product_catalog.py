"""
Beurer product catalog for blog article validation.

Loads product/category data from JSON (PIM-ready: swap loader for API later).
Validates product mentions in article HTML against the catalog.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).parent / "product_catalog.json"

# Only match known Beurer prefixes to avoid false positives (e.g., "EU 27")
_PRODUCT_PATTERN = re.compile(r'\b(BM|BC|EM|IL)\s?(\d{2,3})\b')

# Category-level generic names for fallback replacement
_CATEGORY_GENERIC_NAMES = {
    ("blood_pressure", "oberarm"): "Beurer Oberarm-Blutdruckmessgeraet",
    ("blood_pressure", "handgelenk"): "Beurer Handgelenk-Blutdruckmessgeraet",
    ("pain_tens", "tens_ems"): "Beurer TENS/EMS-Geraet",
    ("infrarot", "infrarotlampe"): "Beurer Infrarotlampe",
}

# Keyword-to-category mapping for article context scoping
# Beurer rules:
#   - Blood pressure articles: ONLY BM/BC devices
#   - Pain therapy articles: TENS/EMS (EM) + Infrared (IL) allowed together
#   - Menstrual devices (EM 50, EM 55): ONLY in menstrual-specific articles
_CATEGORY_KEYWORDS = {
    "menstrual": ["menstrual", "regel", "periode", "menstruation", "periodenschmerz"],
    "pain_therapy": [
        "tens", "ems", "reizstrom", "elektroden", "schmerztherapie", "muskelstimulation",
        "infrarot", "rotlicht", "wärmelampe", "infrared",
        "rueckenschmerz", "rückenschmerz", "nackenschmerz", "gelenkschmerz", "muskelschmerz",
    ],
    "blood_pressure": ["blutdruck", "blutdruckmess", "oberarm", "handgelenk", "hypertonie", "blood pressure"],
}
_CATEGORY_PRIORITY = ["menstrual", "pain_therapy", "blood_pressure"]


def detect_article_category(keyword: str) -> str:
    """Detect article category from keyword for context scoping.

    Returns one of: 'pain_therapy', 'blood_pressure', 'menstrual', 'general'.
    Priority order handles ambiguous keywords (e.g. 'TENS bei Regelschmerzen' -> 'menstrual').

    pain_therapy includes both TENS/EMS and infrared products per Beurer's rules —
    they are one product family for pain management content.
    """
    kw_lower = keyword.lower()
    for category in _CATEGORY_PRIORITY:
        if any(term in kw_lower for term in _CATEGORY_KEYWORDS[category]):
            return category
    return "general"


def get_products_for_category(category: str, catalog: Optional['ProductCatalog'] = None) -> List['Product']:
    """Return only products relevant to the given article category.

    Args:
        category: One of 'pain_therapy', 'blood_pressure', 'menstrual', 'general'.
        catalog: Optional pre-loaded catalog. Loads from disk if not provided.

    Returns:
        Filtered list of Product objects per Beurer rules:
        - blood_pressure: only BM/BC products
        - pain_therapy: EM (non-menstrual) + IL products
        - menstrual: all EM products (menstrual-only + general TENS for comparison)
        - general: full catalog
    """
    if catalog is None:
        catalog = load_catalog()

    if category == "general":
        return list(catalog.products.values())

    products = []
    for p in catalog.products.values():
        if category == "pain_therapy":
            # TENS/EMS (non-menstrual) + infrared lamps
            if p.type == "tens_ems" and p.usage_restriction != "menstrual_only":
                products.append(p)
            elif p.category == "infrarot":
                products.append(p)
        elif category == "blood_pressure":
            # ONLY blood pressure monitors (BM/BC)
            if p.category == "blood_pressure":
                products.append(p)
        elif category == "menstrual":
            # All TENS/EMS including menstrual-only (EM 50, EM 55)
            if p.type == "tens_ems":
                products.append(p)

    return products


def format_product_specs(products: List['Product'], language: str = "de") -> str:
    """Format product list with specs for injection into Gemini prompt.

    Includes key specs (programs, channels, electrodes, connectivity) from
    catalog data so Gemini uses correct values instead of hallucinating.
    """
    if not products:
        return ""

    is_de = language.startswith("de")
    lines = []

    if is_de:
        lines.append("=== PRODUKTE FÜR DIESEN ARTIKEL (NUR diese verwenden, mit GENAU diesen Spezifikationen) ===")
    else:
        lines.append("=== PRODUCTS FOR THIS ARTICLE (use ONLY these, with EXACTLY these specs) ===")

    for p in sorted(products, key=lambda x: (x.priority or 99, x.sku)):
        parts = [p.sku]

        if p.type == "oberarm":
            parts.append("Oberarm" if is_de else "Upper arm")
        elif p.type == "handgelenk":
            parts.append("Handgelenk" if is_de else "Wrist")
        elif p.type == "tens_ems":
            funcs = [f.upper() for f in p.functions if f in ("tens", "ems", "massage")]
            if funcs:
                parts.append("/".join(funcs))
        elif p.type == "infrarotlampe":
            parts.append("Infrarotlampe" if is_de else "Infrared lamp")

        _raw = _load_raw_product(p.sku)
        if _raw:
            if "programs" in _raw:
                parts.append(f"{_raw['programs']} Programme" if is_de else f"{_raw['programs']} programs")
            if "channels" in _raw:
                parts.append(f"{_raw['channels']} Kanäle" if is_de else f"{_raw['channels']} channels")
            if "electrodes" in _raw:
                parts.append(f"{_raw['electrodes']} Elektroden" if is_de else f"{_raw['electrodes']} electrodes")

        if p.has_heat:
            parts.append("Wärmefunktion" if is_de else "Heat function")

        if p.usage_restriction == "menstrual_only":
            parts.append("NUR für Menstruationsschmerzen" if is_de else "Menstrual pain ONLY")

        if p.app_compatible:
            parts.append("Bluetooth, HealthManager Pro kompatibel" if is_de else "Bluetooth, HealthManager Pro compatible")
        else:
            parts.append("kein Bluetooth, keine App" if is_de else "no Bluetooth, no app")

        lines.append(f"- {', '.join(parts)}")

    if is_de:
        lines.append("")
        lines.append("Erwähne KEINE Produkte, die nicht oben aufgelistet sind. Ändere KEINE dieser Spezifikationen.")
    else:
        lines.append("")
        lines.append("DO NOT mention any product not listed above. DO NOT modify these specifications.")

    return "\n".join(lines)


def _load_raw_product(sku: str) -> Optional[Dict[str, Any]]:
    """Load raw product data from JSON (includes extra fields like programs, channels)."""
    try:
        data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
        return data.get("products", {}).get(sku)
    except Exception:
        return None


@dataclass
class Product:
    sku: str
    url: Optional[str]
    priority: Optional[int]
    category: str
    type: str
    has_bluetooth: bool = False
    app_compatible: bool = False
    has_heat: bool = False
    has_ekg: bool = False
    functions: List[str] = field(default_factory=list)
    usage_restriction: Optional[str] = None


@dataclass
class ValidationIssue:
    sku: str
    replacement_sku: Optional[str]
    replacement_text: Optional[str]
    reason: str


@dataclass
class ValidationResult:
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    products_found: List[str] = field(default_factory=list)


@dataclass
class ProductCatalog:
    products: Dict[str, Product]
    categories: Dict[str, Optional[str]]
    meta: Dict[str, str]

    def get_product_url(self, sku: str) -> Optional[str]:
        """Return webshop URL for a product SKU, or None if not populated."""
        product = self.products.get(sku)
        return product.url if product else None

    def get_priority_products(self, max_priority: int = 1) -> List[Product]:
        """Return products at or above the given priority level (1 = highest)."""
        return [
            p for p in self.products.values()
            if p.priority is not None and p.priority <= max_priority
        ]

    def get_category_urls(self) -> Dict[str, str]:
        """Return category URLs that are non-null."""
        return {k: v for k, v in self.categories.items() if v is not None}

    def get_category_overview_url(self, article_category: str, keyword: str = "") -> Optional[str]:
        """Return the single category overview URL for an article category.

        Article categories come from `detect_article_category()` and are one
        of: blood_pressure, pain_therapy, menstrual, general.
        """
        if not article_category:
            return None
        return self.categories.get(article_category)

    def get_product_urls(self) -> Dict[str, str]:
        """Return product SKU -> URL for products with non-null URLs."""
        return {sku: p.url for sku, p in self.products.items() if p.url is not None}


def load_catalog(path: Optional[Path] = None) -> ProductCatalog:
    """Load product catalog from JSON file.

    Args:
        path: Override path to catalog JSON. Defaults to blog/product_catalog.json.

    Returns:
        ProductCatalog with all products and categories.
    """
    catalog_path = path or _CATALOG_PATH
    data = json.loads(catalog_path.read_text(encoding="utf-8"))

    products = {}
    for sku, info in data.get("products", {}).items():
        # Normalize SKU: ensure space between prefix and number
        normalized = _normalize_sku(sku)
        products[normalized] = Product(
            sku=normalized,
            url=info.get("url"),
            priority=info.get("priority"),
            category=info.get("category", ""),
            type=info.get("type", ""),
            has_bluetooth=info.get("has_bluetooth", False),
            app_compatible=info.get("app_compatible", False),
            has_heat=info.get("has_heat", False),
            has_ekg=info.get("has_ekg", False),
            functions=info.get("functions", []),
            usage_restriction=info.get("usage_restriction"),
        )

    categories = data.get("categories", {})
    meta = data.get("meta", {})

    logger.info(f"Loaded product catalog: {len(products)} products, {len(categories)} categories")
    return ProductCatalog(products=products, categories=categories, meta=meta)


def find_product_for_keyword(keyword: str) -> Optional[str]:
    """Extract a Beurer product model code from a keyword string.

    Examples:
        "Beurer EM 59 Erfahrung" -> "EM 59"
        "BM27 Test" -> "BM 27"
        "Blutdruck messen" -> None
    """
    m = _PRODUCT_PATTERN.search(keyword)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return None


def get_product_known_issues(model_code: str) -> Optional[list]:
    """Return unresolved known issues for a product from the catalog JSON.

    Args:
        model_code: Normalized product code, e.g. "EM 59".

    Returns:
        List of issue dicts with keys: issue, severity, source, date_reported.
        None if no unresolved issues exist.
    """
    data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    product = data.get("products", {}).get(model_code, {})
    issues = product.get("known_issues", [])
    active = [i for i in issues if not i.get("resolved", False)]
    return active or None


def _normalize_sku(sku: str) -> str:
    """Normalize SKU to 'XX NN' format (prefix space number)."""
    m = _PRODUCT_PATTERN.search(sku)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return sku.strip()


def validate_product_mentions(html: str, catalog: ProductCatalog) -> ValidationResult:
    """Scan HTML for Beurer product mentions and validate against catalog.

    Args:
        html: Article HTML content.
        catalog: Loaded product catalog.

    Returns:
        ValidationResult with issues for any products not in catalog.
    """
    result = ValidationResult(valid=True)

    for match in _PRODUCT_PATTERN.finditer(html):
        sku = f"{match.group(1)} {match.group(2)}"
        result.products_found.append(sku)

        if sku not in catalog.products:
            # Find replacement: highest-priority product in same category+type
            replacement = _find_replacement(sku, catalog)
            result.valid = False
            result.issues.append(ValidationIssue(
                sku=sku,
                replacement_sku=replacement.sku if replacement else None,
                replacement_text=replacement.sku if replacement else _get_generic_name(sku),
                reason=f"Product {sku} not in German webshop catalog",
            ))

    return result


def _find_replacement(sku: str, catalog: ProductCatalog) -> Optional[Product]:
    """Find the best replacement product for an invalid SKU.

    Heuristic: same category + type, highest priority (lowest number).
    """
    # Guess category from prefix
    prefix = sku.split()[0] if " " in sku else sku[:2]
    prefix_category = {
        "BM": ("blood_pressure", "oberarm"),
        "BC": ("blood_pressure", "handgelenk"),
        "EM": ("pain_tens", "tens_ems"),
        "IL": ("infrarot", "infrarotlampe"),
    }.get(prefix)

    if not prefix_category:
        return None

    cat, typ = prefix_category
    candidates = [
        p for p in catalog.products.values()
        if p.category == cat and p.type == typ and p.priority is not None
    ]
    if not candidates:
        # Fallback: same category, any type
        candidates = [
            p for p in catalog.products.values()
            if p.category == cat and p.priority is not None
        ]
    if not candidates:
        return None

    # Sort by priority (1 = best), return top
    candidates.sort(key=lambda p: p.priority)
    return candidates[0]


def _get_generic_name(sku: str) -> Optional[str]:
    """Get a category-level generic product name for an invalid SKU."""
    prefix = sku.split()[0] if " " in sku else sku[:2]
    prefix_to_key = {
        "BM": ("blood_pressure", "oberarm"),
        "BC": ("blood_pressure", "handgelenk"),
        "EM": ("pain_tens", "tens_ems"),
        "IL": ("infrarot", "infrarotlampe"),
    }
    key = prefix_to_key.get(prefix)
    return _CATEGORY_GENERIC_NAMES.get(key) if key else None


@dataclass
class ClaimIssue:
    sku: str
    claim_type: str  # "app_compatibility", "usage_restriction", "false_feature", "unknown_product"
    description: str
    context: str  # surrounding text snippet
    fix_hint: str  # what to replace/remove


def validate_product_claims(html: str, catalog: ProductCatalog) -> List[ClaimIssue]:
    """Scan HTML for false product feature claims and return issues.

    Checks:
    1. HealthManager Pro / app claims near non-compatible products
    2. EM 50/55 (menstrual-only) recommended for non-menstrual pain
    3. EKG claims on non-EKG devices
    4. Bluetooth/app claims on non-connected devices
    """
    issues: List[ClaimIssue] = []
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    # 1. HealthManager Pro / app near non-compatible products
    for m in re.finditer(r'HealthManager\s*Pro', text, re.IGNORECASE):
        ctx_start = max(0, m.start() - 200)
        ctx_end = min(len(text), m.end() + 200)
        ctx = text[ctx_start:ctx_end]
        # Find product mentions in context
        for pm in _PRODUCT_PATTERN.finditer(ctx):
            sku = f"{pm.group(1).upper()} {pm.group(2)}"
            product = catalog.products.get(sku)
            if product and not product.app_compatible:
                issues.append(ClaimIssue(
                    sku=sku,
                    claim_type="app_compatibility",
                    description=f"{sku} is not compatible with HealthManager Pro",
                    context=ctx.strip()[:200],
                    fix_hint="Remove HealthManager Pro reference or replace with correct product",
                ))

    # 2. Menstrual-only devices used for non-menstrual pain
    menstrual_skus = {
        sku for sku, p in catalog.products.items()
        if p.usage_restriction == "menstrual_only"
    }
    non_menstrual_pain = re.compile(
        r'(rücken|nacken|knie|schulter|gelenk|muskel|kopf|arthrose|'
        r'ischias|fibromyalgie|neuropath|sportver)',
        re.IGNORECASE,
    )
    for sku in menstrual_skus:
        sku_pattern = re.compile(rf'\b{re.escape(sku)}\b')
        for m in sku_pattern.finditer(text):
            ctx_start = max(0, m.start() - 200)
            ctx_end = min(len(text), m.end() + 200)
            ctx = text[ctx_start:ctx_end]
            if non_menstrual_pain.search(ctx):
                # Check it's not just listing it in a comparison table with correct label
                if not re.search(r'menstrual|regelschmerz|menstruation', ctx, re.IGNORECASE):
                    issues.append(ClaimIssue(
                        sku=sku,
                        claim_type="usage_restriction",
                        description=f"{sku} is menstrual-only but mentioned for non-menstrual pain",
                        context=ctx.strip()[:200],
                        fix_hint=f"Remove {sku} from non-menstrual context or add menstrual qualifier",
                    ))

    # 3. EKG claims on non-EKG devices
    ekg_skus = {sku for sku, p in catalog.products.items() if p.has_ekg}
    for m in re.finditer(r'\b(BM|BC)\s?(\d{2,3})\b', text, re.IGNORECASE):
        sku = f"{m.group(1).upper()} {m.group(2)}"
        if sku in ekg_skus:
            continue
        product = catalog.products.get(sku)
        if not product:
            continue
        ctx_start = max(0, m.start() - 100)
        ctx_end = min(len(text), m.end() + 100)
        ctx = text[ctx_start:ctx_end]
        if re.search(r'\bEKG\b', ctx, re.IGNORECASE):
            issues.append(ClaimIssue(
                sku=sku,
                claim_type="false_feature",
                description=f"{sku} does not have EKG functionality",
                context=ctx.strip()[:200],
                fix_hint=f"Remove EKG claim from {sku} or replace with BM 96",
            ))

    # 4. Bluetooth/app claims on non-Bluetooth devices
    app_keywords = re.compile(
        r'(Bluetooth|WLAN|WiFi|App.{0,20}(?:verbind|koppel|synchron|Daten|übertrag))',
        re.IGNORECASE,
    )
    for m in _PRODUCT_PATTERN.finditer(text):
        sku = f"{m.group(1).upper()} {m.group(2)}"
        product = catalog.products.get(sku)
        if not product or product.has_bluetooth:
            continue
        ctx_start = max(0, m.start() - 150)
        ctx_end = min(len(text), m.end() + 150)
        ctx = text[ctx_start:ctx_end]
        if app_keywords.search(ctx):
            issues.append(ClaimIssue(
                sku=sku,
                claim_type="false_feature",
                description=f"{sku} does not have Bluetooth/app connectivity",
                context=ctx.strip()[:200],
                fix_hint=f"Remove connectivity claim from {sku}",
            ))

    return issues


def apply_claim_validation(article: Dict[str, Any], catalog: ProductCatalog) -> Dict[str, Any]:
    """Run feature claim validation on all content fields and report issues.

    Does NOT auto-fix (claims require contextual rewriting, not simple replacement).
    Returns a report dict with issues found.
    """
    all_issues: List[Dict] = []

    content_fields = ["Intro", "Direct_Answer"]
    for i in range(1, 10):
        content_fields.append(f"section_{i:02d}_content")

    for field_name in content_fields:
        content = article.get(field_name, "")
        if not isinstance(content, str) or not content:
            continue
        issues = validate_product_claims(content, catalog)
        for issue in issues:
            all_issues.append({
                "field": field_name,
                "sku": issue.sku,
                "claim_type": issue.claim_type,
                "description": issue.description,
                "context": issue.context,
                "fix_hint": issue.fix_hint,
            })

    return {
        "issues_found": len(all_issues),
        "issues": all_issues,
    }


def apply_product_validation(article: Dict[str, Any], catalog: ProductCatalog) -> Dict[str, Any]:
    """Run product validation on all HTML content fields and fix invalid mentions.

    Modifies article dict in place. Returns dict with validation report.
    """
    fields_checked = 0
    replacements_made = 0

    # Fields that can contain product mentions
    content_fields = ["Intro", "Direct_Answer"]
    for i in range(1, 10):
        content_fields.append(f"section_{i:02d}_content")

    for field_name in content_fields:
        content = article.get(field_name, "")
        if not isinstance(content, str) or not content:
            continue

        fields_checked += 1
        result = validate_product_mentions(content, catalog)

        if not result.valid:
            for issue in result.issues:
                if issue.replacement_text:
                    # Replace invalid SKU with replacement
                    # Use word-boundary-aware replacement
                    pattern = re.compile(
                        rf'\b{re.escape(issue.sku)}\b'
                    )
                    new_content = pattern.sub(issue.replacement_text, content)
                    if new_content != content:
                        content = new_content
                        replacements_made += 1
                        logger.info(
                            f"Replaced '{issue.sku}' with '{issue.replacement_text}' "
                            f"in {field_name}"
                        )

            article[field_name] = content

    # Rewrite product links to use catalog URLs
    links_rewritten = _rewrite_product_links(article, catalog, content_fields)

    return {
        "fields_checked": fields_checked,
        "replacements_made": replacements_made,
        "links_rewritten": links_rewritten,
    }


def get_product_service_insights(product_model: str, client_id: str = "beurer") -> Optional[str]:
    """Get formatted service case summary for article generation context.

    Returns a prompt-ready German string, or None if no data available.
    """
    try:
        from db.client import get_beurer_supabase, get_service_case_summary
        client = get_beurer_supabase()
        summary = get_service_case_summary(client, client_id, product_model)
        if not summary or summary["total_cases"] == 0:
            return None

        lines = [f"## Kundendienst-Daten (letzte 90 Tage)"]
        lines.append(f"{summary['product']}: {summary['total_cases']} Fälle")
        for r in summary["top_reasons"]:
            lines.append(f"- {r['reason']}: {r['count']} ({r['percent']}%)")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Service case lookup failed for {product_model}: {e}")
        return None


def _rewrite_product_links(
    article: Dict, catalog: ProductCatalog, fields: List[str]
) -> int:
    """Rewrite <a href> tags that reference Beurer products to use catalog URLs."""
    rewritten = 0
    product_urls = catalog.get_product_urls()
    if not product_urls:
        return 0  # No URLs populated yet

    for field_name in fields:
        content = article.get(field_name, "")
        if not isinstance(content, str) or not content:
            continue

        for sku, url in product_urls.items():
            # Find anchor tags whose text mentions this SKU
            # but skip category overview links (/de/l/) — those should not be
            # rewritten to individual product pages
            pattern = re.compile(
                rf'<a\s+([^>]*?)href=["\'](?!(?:[^"\']*?/l/))[^"\']*["\']([^>]*)>'
                rf'([^<]*\b{re.escape(sku)}\b[^<]*)</a>',
                re.IGNORECASE,
            )
            def _replace_href(m, _url=url):
                attrs_before = m.group(1)
                attrs_after = m.group(2)
                text = m.group(3)
                return (
                    f'<a {attrs_before}href="{_url}"{attrs_after}>'
                    f'{text}</a>'
                )

            new_content = pattern.sub(_replace_href, content)
            if new_content != content:
                content = new_content
                rewritten += 1

        article[field_name] = content

    return rewritten
