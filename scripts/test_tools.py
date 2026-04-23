"""Test tools for verifying API connections.

Run: python -m services.social_listening.test_tools
"""
import os
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment from local .env file
load_dotenv()


def test_supabase():
    """Test Supabase connection."""
    print("\n=== Testing Supabase ===")
    from supabase import create_client

    url = os.getenv("BEURER_SUPABASE_URL")
    key = os.getenv("BEURER_SUPABASE_KEY")

    if not url or not key:
        print("FAIL: Missing BEURER_SUPABASE_URL or BEURER_SUPABASE_KEY")
        return False

    try:
        client = create_client(url, key)
        result = client.table("social_items").select("id").limit(1).execute()
        count = client.table("social_items").select("id", count="exact").execute()
        print(f"SUCCESS: Connected to Supabase")
        print(f"  - social_items count: {count.count}")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_firecrawl():
    """Test Firecrawl API."""
    print("\n=== Testing Firecrawl ===")
    api_key = os.getenv("FIRECRAWL_API_KEY")

    if not api_key:
        print("FAIL: Missing FIRECRAWL_API_KEY")
        return False

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "url": "https://www.gutefrage.net/frage/blutdruckmessgeraet-empfehlung",
                    "formats": ["markdown"]
                }
            )
            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS: Firecrawl API working")
                print(f"  - Scraped {len(data.get('data', {}).get('markdown', ''))} chars")
                return True
            else:
                print(f"FAIL: Status {response.status_code} - {response.text[:200]}")
                return False
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_apify():
    """Test Apify API token."""
    print("\n=== Testing Apify ===")
    token = os.getenv("APIFY_API_TOKEN")

    if not token:
        print("FAIL: Missing APIFY_API_TOKEN")
        return False

    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(
                "https://api.apify.com/v2/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS: Apify API working")
                print(f"  - User: {data.get('data', {}).get('username', 'unknown')}")
                return True
            else:
                print(f"FAIL: Status {response.status_code}")
                return False
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_gemini_embeddings():
    """Test Gemini embeddings API."""
    print("\n=== Testing Gemini Embeddings ===")
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("SKIP: Missing GEMINI_API_KEY (add to .env.beurer)")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        result = genai.embed_content(
            model="models/text-embedding-004",
            content="Test embedding for Blutdruckmessgerät",
            task_type="retrieval_document"
        )
        embedding = result['embedding']
        print(f"SUCCESS: Gemini embeddings working")
        print(f"  - Embedding dimension: {len(embedding)}")
        return True
    except ImportError:
        print("FAIL: google-generativeai package not installed")
        return False
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_serper():
    """Test Serper API for web search."""
    print("\n=== Testing Serper ===")
    api_key = os.getenv("SERPER_API_KEY")

    if not api_key:
        print("SKIP: Missing SERPER_API_KEY (add to .env.beurer)")
        return None

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key},
                json={"q": "Beurer Blutdruckmessgerät Test", "gl": "de", "hl": "de"}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS: Serper API working")
                print(f"  - Results: {len(data.get('organic', []))}")
                return True
            else:
                print(f"FAIL: Status {response.status_code}")
                return False
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_gemini():
    """Test Gemini API for classification."""
    print("\n=== Testing Gemini ===")
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("SKIP: Missing GEMINI_API_KEY (add to .env.beurer)")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content("Say 'test successful' in German")
        print(f"SUCCESS: Gemini API working")
        print(f"  - Response: {response.text[:50]}...")
        return True
    except ImportError:
        print("FAIL: google-generativeai package not installed")
        return False
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def run_all_tests():
    """Run all API tests."""
    print("=" * 50)
    print("Social Listening - API Connection Tests")
    print("=" * 50)

    results = {
        "Supabase": test_supabase(),
        "Firecrawl": test_firecrawl(),
        "Apify": test_apify(),
        "Gemini (LLM)": test_gemini(),
        "Gemini Embeddings": test_gemini_embeddings(),
        "Serper": test_serper(),
    }

    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)

    for name, result in results.items():
        if result is True:
            status = "PASS"
        elif result is False:
            status = "FAIL"
        else:
            status = "SKIP"
        print(f"  {name}: {status}")

    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
