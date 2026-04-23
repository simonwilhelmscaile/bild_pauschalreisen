"""Lightweight heuristic validation for text replacements.

Catches truncated, broken, or grammatically unsound replacements
before they are applied to article content. All checks are O(n)
string operations — no LLM calls.
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)


def validate_replacement(
    original: str,
    replacement: str,
    context_before: str = "",
    context_after: str = "",
    is_html: bool = False,
) -> Tuple[bool, str]:
    """Validate that a proposed replacement is safe to apply.

    Args:
        original: The text being replaced (the "find" string).
        replacement: The proposed replacement text.
        context_before: ~80 chars of content before the match position.
        context_after: ~80 chars of content after the match position.
        is_html: Whether the content is HTML (enables tag-balance check).

    Returns:
        (ok, reason) — True if safe, False with rejection reason.
    """
    orig_len = len(original)
    repl_len = len(replacement)

    # --- Check 1: Truncated replacement (< 30% of original length) ---
    # Skip for short originals (< 20 chars) — these are often single-word fixes
    if orig_len >= 20 and repl_len > 0:
        ratio = repl_len / orig_len
        if ratio < 0.3:
            return False, (
                f"Replacement too short (ratio {ratio:.2f}). "
                f"Original {orig_len} chars -> replacement {repl_len} chars"
            )

    # --- Check 2: Oversized replacement (> 3x original + 200 chars) ---
    if repl_len > 0 and orig_len > 0:
        ratio = repl_len / orig_len
        delta = repl_len - orig_len
        if ratio > 3.0 and delta > 200:
            return False, (
                f"Replacement too large (ratio {ratio:.2f}, delta {delta}). "
                f"Looks like a paragraph rewrite, not a surgical fix"
            )

    # --- Check 3: Empty replacement deleting mid-sentence ---
    if repl_len == 0 and orig_len > 0:
        # Empty replacement is fine if original is a complete removable unit:
        # full sentence, list item, or parenthetical.
        stripped = original.strip()

        # Full sentence: ends with sentence-ending punctuation
        is_full_sentence = bool(stripped) and stripped[-1] in ".!?>"

        # List item: starts with <li or - bullet
        is_list_item = stripped.startswith("<li") or stripped.startswith("- ")

        # Parenthetical: enclosed in brackets/parens
        is_parenthetical = (
            (stripped.startswith("(") and stripped.endswith(")"))
            or (stripped.startswith("[") and stripped.endswith("]"))
        )

        if not (is_full_sentence or is_list_item or is_parenthetical):
            # Check context: if we're mid-sentence, this deletion breaks grammar
            before = context_before.rstrip()
            after = context_after.lstrip()
            # Mid-sentence if preceding context doesn't end at a boundary
            if before and before[-1] not in ".!?>\n":
                return False, (
                    "Empty replacement deletes from mid-sentence. "
                    "Use find=full sentence + replace=rewritten sentence instead"
                )

    # --- Check 4: HTML tag imbalance ---
    if is_html and repl_len > 0:
        # Count opening and closing tags in original vs replacement
        orig_opens = len(re.findall(r"<(?!/)(\w+)[\s>]", original))
        orig_closes = len(re.findall(r"</(\w+)>", original))
        repl_opens = len(re.findall(r"<(?!/)(\w+)[\s>]", replacement))
        repl_closes = len(re.findall(r"</(\w+)>", replacement))

        orig_balance = orig_opens - orig_closes
        repl_balance = repl_opens - repl_closes

        # The replacement should maintain the same tag balance as the original
        # (both balanced, or both leave the same tags open/closed)
        if orig_balance != repl_balance:
            return False, (
                f"HTML tag imbalance: original balance={orig_balance}, "
                f"replacement balance={repl_balance}. "
                f"Replacement may orphan or introduce unclosed tags"
            )

    # --- Check 5: Sentence-ending punctuation loss ---
    if repl_len > 0 and orig_len > 0:
        orig_stripped = original.rstrip()
        repl_stripped = replacement.rstrip()
        if orig_stripped and orig_stripped[-1] in ".!?" and repl_stripped:
            if repl_stripped[-1] not in ".!?":
                return False, (
                    f"Replacement drops sentence-ending punctuation "
                    f"('{orig_stripped[-1]}' -> '{repl_stripped[-1]}')"
                )

    return True, ""
