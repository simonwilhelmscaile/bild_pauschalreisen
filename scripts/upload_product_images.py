"""One-time upload of Beurer product cutout images to Supabase Storage."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()
from db.client import get_beurer_supabase

PRODUCT_IMAGES_DIR = Path(os.environ.get(
    "BEURER_PRODUCT_IMAGES_DIR",
    "C:/Users/yousi/scaile/workshop-beurer/02_CLIENT_INPUT/2026-02-18_produktbilder_datenblaetter/produktbilder",
))

BUCKET = "blog-images"
FOLDER = "products"


def upload_all():
    sb = get_beurer_supabase()
    if not PRODUCT_IMAGES_DIR.exists():
        print(f"ERROR: Directory not found: {PRODUCT_IMAGES_DIR}")
        sys.exit(1)

    # Use a set to deduplicate on case-insensitive Windows
    jpg_files = list({p.name: p for p in list(PRODUCT_IMAGES_DIR.glob("*.jpg")) + list(PRODUCT_IMAGES_DIR.glob("*.JPG"))}.values())
    print(f"Found {len(jpg_files)} product images in {PRODUCT_IMAGES_DIR}")

    uploaded = 0
    for img_path in sorted(jpg_files):
        storage_path = f"{FOLDER}/{img_path.name}"
        try:
            with open(img_path, "rb") as f:
                sb.storage.from_(BUCKET).upload(
                    path=storage_path,
                    file=f.read(),
                    file_options={"content-type": "image/jpeg", "upsert": "true"},
                )
            url = sb.storage.from_(BUCKET).get_public_url(storage_path)
            print(f"  OK: {img_path.name} -> {url[:80]}...")
            uploaded += 1
        except Exception as e:
            print(f"  FAIL: {img_path.name} -> {e}")

    print(f"\nUploaded {uploaded}/{len(jpg_files)} images to {BUCKET}/{FOLDER}/")


if __name__ == "__main__":
    upload_all()
