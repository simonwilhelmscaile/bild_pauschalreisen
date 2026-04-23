"""
Image Creator - Generates images using Google Imagen 4.0.

Uses the dedicated Imagen API for image generation.
Uploads images to Supabase Storage for production use.
"""

import asyncio
import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import PIL for image processing
try:
    from PIL import Image as PILImage
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    PILImage = None

# Check if Supabase storage is available via db/client.py
def _is_supabase_configured():
    try:
        from db.client import get_beurer_supabase
        get_beurer_supabase()
        return True
    except Exception:
        return False

SUPABASE_AVAILABLE = True  # db/client always importable in this repo

# Image generation model
MODEL = "imagen-4.0-generate-001"


async def generate_image(
    prompt: str,
    output_dir: Optional[str] = None,
    api_key: Optional[str] = None,
    aspect_ratio: Optional[str] = "16:9",
) -> Optional[str]:
    """
    Generate an image using Google Imagen 4.0.

    Args:
        prompt: Image description
        output_dir: Directory to save image (default: output/images)
        api_key: API key (falls back to env var)

    Returns:
        Path to saved image, or None on failure
    """
    if not prompt or not prompt.strip():
        logger.error("Empty image prompt")
        return None

    api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        logger.warning("No API key - returning mock image URL")
        return _mock_url(prompt)

    logger.info(f"Generating image: {prompt[:80]}...")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        config_kwargs = {"number_of_images": 1}
        if aspect_ratio:
            config_kwargs["aspect_ratio"] = aspect_ratio

        response = await asyncio.to_thread(
            client.models.generate_images,
            model=MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(**config_kwargs),
        )

        if not response:
            logger.error("No response from Imagen API")
            return None

        generated_images = getattr(response, 'generated_images', None)
        if not generated_images:
            logger.error("No generated_images in response")
            return None

        img = generated_images[0]
        img_data = getattr(img, 'image', None)
        if not img_data:
            logger.error("No image data in first generated image")
            return None

        image_bytes = getattr(img_data, 'image_bytes', None)
        if not image_bytes:
            logger.error("No image_bytes in image data")
            return None

        # Try to upload to Supabase first (for production use)
        if SUPABASE_AVAILABLE and _is_supabase_configured():
            logger.info("Supabase configured - uploading image...")
            supabase_url = await _upload_to_supabase(image_bytes, prompt)
            if supabase_url:
                logger.info(f"Image uploaded to Supabase: {supabase_url[:100]}...")
                return supabase_url
            logger.warning("Supabase upload failed, falling back to local storage")
        else:
            logger.info("Supabase not configured, using local storage")

        # Fall back to local storage
        return _save_image(image_bytes, prompt, output_dir)

    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return None


async def _upload_to_supabase(image_bytes: bytes, prompt: str) -> Optional[str]:
    """
    Upload image to Supabase Storage (blog-images bucket).

    Returns:
        Public URL of uploaded image, or None on failure
    """
    try:
        from db.client import get_beurer_supabase

        # Convert to WebP if PIL available (smaller file size)
        if PIL_AVAILABLE:
            try:
                with PILImage.open(io.BytesIO(image_bytes)) as img:
                    webp_buffer = io.BytesIO()
                    img.save(webp_buffer, format='WEBP', quality=85)
                    image_bytes = webp_buffer.getvalue()
                    content_type = "image/webp"
                    ext = ".webp"
            except Exception as e:
                logger.debug(f"WebP conversion failed, using original: {e}")
                content_type = "image/png"
                ext = ".png"
        else:
            content_type = "image/png"
            ext = ".png"

        # Generate unique filename from prompt hash + timestamp to avoid cache collisions
        import time
        unique_key = f"{prompt}_{time.time()}"
        file_hash = hashlib.sha256(unique_key.encode()).hexdigest()[:12]
        filepath = f"generated/image_{file_hash}{ext}"

        sb = get_beurer_supabase()
        sb.storage.from_("blog-images").upload(
            path=filepath,
            file=image_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )

        # Build public URL
        public_url = sb.storage.from_("blog-images").get_public_url(filepath)
        return public_url

    except Exception as e:
        logger.error(f"Failed to upload to Supabase: {e}")
        return None


def _save_image(image_bytes: bytes, prompt: str, output_dir: Optional[str]) -> Optional[str]:
    """Save image to disk."""
    # Validate image data before processing
    if not image_bytes or len(image_bytes) < 8:
        logger.error("Invalid image data: empty or too small")
        return None

    # Check for common image magic bytes
    magic_bytes = {
        b'\x89PNG': 'PNG',
        b'\xff\xd8\xff': 'JPEG',
        b'GIF87a': 'GIF',
        b'GIF89a': 'GIF',
        b'RIFF': 'WEBP',  # WEBP starts with RIFF
    }

    is_valid_image = False
    for magic, fmt in magic_bytes.items():
        if image_bytes[:len(magic)] == magic:
            is_valid_image = True
            logger.debug(f"Detected image format: {fmt}")
            break

    if not is_valid_image:
        logger.warning("Image data does not match known formats, attempting to save anyway")

    try:
        if output_dir:
            out_path = Path(output_dir)
        else:
            # Default to stage 2 output/images (absolute path)
            out_path = Path(__file__).parent / "output" / "images"
        out_path.mkdir(parents=True, exist_ok=True)

        # Use SHA256 instead of MD5 (more secure, though not critical here)
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:12]

        # Convert to WebP if PIL available (skip PNG intermediate)
        if PIL_AVAILABLE:
            webp_path = out_path / f"image_{prompt_hash}.webp"
            try:
                # Use context manager for proper resource cleanup
                with PILImage.open(io.BytesIO(image_bytes)) as img:
                    img.save(str(webp_path), format='WEBP', quality=85)
                logger.info(f"Image saved: {webp_path}")
                return str(webp_path)
            except Exception as pil_error:
                logger.warning(f"PIL conversion failed: {pil_error}, falling back to PNG")
                # Fall through to PNG save

        # Fallback: save as PNG only if PIL not available or failed
        png_path = out_path / f"image_{prompt_hash}.png"
        with open(png_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"Image saved: {png_path}")
        return str(png_path)

    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        return None


def _mock_url(prompt: str) -> str:
    """Generate mock placeholder image URL for testing."""
    # Use placehold.co which is a real placeholder service
    # 1600x900 is 16:9 ratio for blog hero images
    return "https://placehold.co/1600x900/e2e8f0/475569?text=Mock+Image"


def generate_alt_text(headline: str) -> str:
    """Generate alt text from headline, truncated at word boundary."""
    alt = f"Article image: {headline}"
    if len(alt) <= 125:
        return alt
    # Truncate at word boundary
    truncated = alt[:122]
    last_space = truncated.rfind(' ')
    if last_space > 50:  # Keep at least 50 chars
        truncated = alt[:last_space]
    return truncated + "..."


class ImageCreator:
    """Wrapper class for stage_2.py compatibility."""

    def __init__(self, api_key: Optional[str] = None, output_dir: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.output_dir = output_dir
        self.mock_mode = not self.api_key
        if self.mock_mode:
            logger.warning("ImageCreator: No API key - using mock mode")
        else:
            logger.info(f"ImageCreator initialized (model: {MODEL})")

    async def generate_async(self, prompt: str, output_dir: Optional[str] = None, aspect_ratio: Optional[str] = "16:9") -> Optional[str]:
        """Generate image (async)."""
        return await generate_image(prompt, output_dir or self.output_dir, self.api_key, aspect_ratio)

    def generate(self, prompt: str, output_dir: Optional[str] = None, aspect_ratio: Optional[str] = "16:9") -> Optional[str]:
        """Generate image (sync - only use outside async context)."""
        try:
            # Check if we're already in an async context
            asyncio.get_running_loop()
            # If we get here, there IS a running loop - can't use asyncio.run
            raise RuntimeError("Use generate_async() when already in async context")
        except RuntimeError as e:
            # RuntimeError means no running loop OR our own error
            if "generate_async" in str(e):
                raise  # Re-raise our own error
            # No running loop - safe to use asyncio.run
            return asyncio.run(generate_image(prompt, output_dir or self.output_dir, self.api_key, aspect_ratio))

    @staticmethod
    def generate_alt_text(headline: str) -> str:
        return generate_alt_text(headline)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python image_creator.py <prompt>")
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])

    async def main():
        url = await generate_image(prompt)
        print(f"\nImage: {url}")

    asyncio.run(main())
