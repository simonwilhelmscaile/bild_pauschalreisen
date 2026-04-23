"""One-time script to extract Beurer branding (logo, colors) via Firecrawl Branding API."""
import asyncio
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


async def extract_branding():
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY not set in .env")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"url": "https://www.beurer.com", "formats": ["branding"]},
        )
        response.raise_for_status()
        data = response.json()

    branding = data.get("data", {}).get("metadata", {}).get("branding", {})
    if not branding:
        # Try top-level branding key
        branding = data.get("data", {}).get("branding", {})

    print("=== Full response structure ===")
    print(json.dumps(data, indent=2, default=str))
    print("\n=== Branding data ===")
    print(json.dumps(branding, indent=2, default=str))

    logos = branding.get("logos", []) or branding.get("logo", [])
    if logos:
        print("\n=== Logos ===")
        for logo in (logos if isinstance(logos, list) else [logos]):
            print(f"  {logo}")


if __name__ == "__main__":
    asyncio.run(extract_branding())
