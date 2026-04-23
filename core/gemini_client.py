"""Gemini client for the blog pipeline using google.genai SDK (v1.x).

NOTE: This is separate from the project root's gemini_client.py which uses the
older google.generativeai SDK for social listening classification tasks. This
module uses the newer google.genai SDK required by the blog pipeline stages.
"""
import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types as genai_types

from blog.shared.constants import GEMINI_MODEL, GEMINI_TIMEOUT_GROUNDING, GEMINI_TIMEOUT_DEFAULT

logger = logging.getLogger(__name__)


def _repair_truncated_json(text: str) -> str:
    """Attempt to repair JSON truncated by token limits.

    Handles the common case where Gemini hits max_output_tokens mid-string,
    leaving unterminated strings, arrays, or objects.
    """
    # Close any unterminated string (odd number of unescaped quotes)
    in_string = False
    escaped = False
    for ch in text:
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
    if in_string:
        text += '"'

    # Close open brackets/braces from the end
    stack = []
    in_str = False
    esc = False
    for ch in text:
        if esc:
            esc = False
            continue
        if ch == '\\':
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in ('{', '['):
            stack.append('}' if ch == '{' else ']')
        elif ch in ('}', ']') and stack:
            stack.pop()

    # Remove trailing comma before closing (invalid JSON)
    text = re.sub(r',\s*$', '', text)

    # Append missing closers
    text += ''.join(reversed(stack))

    return text


class GeminiClient:
    """Wrapper around google.genai SDK for blog article generation."""

    def __init__(self, service_type=None, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._model = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
        self._client = genai.Client(api_key=self._api_key)

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        use_url_context: bool = False,
        use_google_search: bool = False,
        json_output: bool = False,
        extract_sources: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        """Generate content with optional grounding tools.

        Called by blog_writer.py for article generation.
        """
        tools = []
        if use_google_search:
            tools.append(genai_types.Tool(google_search=genai_types.GoogleSearch()))
        if use_url_context:
            tools.append(genai_types.Tool(url_context=genai_types.UrlContext()))

        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_tokens,
            tools=tools or None,
        )

        if json_output:
            config.response_mime_type = "application/json"

        coro = asyncio.to_thread(
            self._client.models.generate_content,
            model=self._model,
            contents=prompt,
            config=config,
        )
        _timeout = GEMINI_TIMEOUT_GROUNDING if (use_google_search or use_url_context) else GEMINI_TIMEOUT_DEFAULT
        response = await asyncio.wait_for(coro, timeout=_timeout)

        # Extract text
        text = response.text or ""

        # Parse JSON if requested
        if json_output:
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                if "```json" in text:
                    text = text.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in text:
                    text = text.split("```", 1)[1].split("```", 1)[0].strip()
                try:
                    result = json.loads(text)
                except json.JSONDecodeError:
                    logger.warning("JSON truncated, attempting repair")
                    text = _repair_truncated_json(text)
                    result = json.loads(text)
        else:
            result = {"text": text}

        # Extract grounding sources if requested
        if extract_sources and response.candidates:
            grounding_sources = self._extract_grounding_sources(response.candidates)
            if grounding_sources:
                result["_grounding_sources"] = grounding_sources

        return result

    async def generate_with_schema(
        self,
        prompt: str,
        response_schema: Any,
        use_url_context: bool = False,
        use_google_search: bool = False,
        extract_sources: bool = False,
        temperature: float = 0.7,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate content with structured JSON schema output.

        Called by stage_3.py for quality fix suggestions.
        """
        tools = []
        if use_google_search:
            tools.append(genai_types.Tool(google_search=genai_types.GoogleSearch()))
        if use_url_context:
            tools.append(genai_types.Tool(url_context=genai_types.UrlContext()))

        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema,
            tools=tools or None,
        )

        coro = asyncio.to_thread(
            self._client.models.generate_content,
            model=self._model,
            contents=prompt,
            config=config,
        )
        _timeout = timeout or (GEMINI_TIMEOUT_GROUNDING if (use_google_search or use_url_context) else GEMINI_TIMEOUT_DEFAULT)
        response = await asyncio.wait_for(coro, timeout=_timeout)

        text = response.text or "{}"
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            if "```json" in text:
                text = text.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in text:
                text = text.split("```", 1)[1].split("```", 1)[0].strip()
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                logger.warning("JSON truncated in schema response, attempting repair")
                text = _repair_truncated_json(text)
                result = json.loads(text)

        # Extract grounding sources if requested
        if extract_sources and response.candidates:
            grounding_sources = self._extract_grounding_sources(response.candidates)
            if grounding_sources:
                result["_grounding_sources"] = grounding_sources

        return result

    @staticmethod
    def _extract_grounding_sources(candidates) -> List[Dict[str, str]]:
        """Extract source URLs from grounding metadata."""
        sources = []
        for candidate in candidates:
            metadata = getattr(candidate, "grounding_metadata", None)
            if not metadata:
                continue
            chunks = getattr(metadata, "grounding_chunks", None) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if web:
                    sources.append({
                        "title": getattr(web, "title", "") or "",
                        "url": getattr(web, "uri", "") or "",
                    })
        return sources
