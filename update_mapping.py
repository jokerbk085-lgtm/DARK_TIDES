"""
update_mapping.py
-----------------
mapping.json را بر اساس پوشه‌های images/ به‌روز می‌کند.
هر keyword به یک پوشه وصل می‌شود.
پروژه خودش تصادفی یک عکس از آن پوشه انتخاب می‌کند.

استفاده:
    python update_mapping.py
"""

import json
from pathlib import Path
from config import ASSETS_DIR, IMAGES_DIR, MUSIC_DIR, MAPPING_FILE

# ── نگاشت keyword → پوشه تصویر و فایل موسیقی ────────────────
# هر keyword به یک پوشه وصل است
# پروژه خودش یک عکس تصادفی از آن پوشه انتخاب می‌کند

KEYWORD_MAP = {
    # کلمه کلیدی : (پوشه تصویر، فایل موسیقی)
    "جسد":      ("crime",  "Contraband.wav"),
    "کشته":     ("crime",  "Contraband.wav"),
    "قتل":      ("crime",  "Contraband.wav"),
    "پلیس":     ("police", "Contraband.wav"),
    "کارآگاه":  ("police", "Contraband.wav"),
    "بازجویی":  ("police", "EW1133.wav"),
    "دستگیر":   ("police", "Contraband.wav"),
    "دادگاه":   ("court",  "EW1133.wav"),
    "محاکمه":   ("court",  "EW1133.wav"),
    "قاضی":     ("court",  "EW1133.wav"),
    "زندان":    ("prison", "Contraband.wav"),
    "حبس":      ("prison", "Contraband.wav"),
    "تهران":    ("city",   "EW1133.wav"),
    "شهر":      ("city",   "EW1133.wav"),
    "خیابان":   ("city",   "Roaring Silence.wav"),
    "قاتل":     ("person", "Contraband.wav"),
    "متهم":     ("person", "EW1133.wav"),
    "مظنون":    ("person", "EW1133.wav"),
    "شب":       ("dark",   "Roaring Silence.wav"),
    "تاریکی":   ("dark",   "Roaring Silence.wav"),
    "کابوس":    ("dark",   "Contraband.wav"),
    "وحشت":     ("dark",   "Contraband.wav"),
    "روزنامه":  ("dark",   "EW1133.wav"),
    "پرونده":   ("dark",   "EW1133.wav"),
}


def find_music(filename: str) -> str | None:
    """مسیر کامل فایل موسیقی را پیدا می‌کند."""
    p = MUSIC_DIR / filename
    return str(p) if p.exists() else None


def build_mapping() -> dict:
    """mapping.json را بر اساس پوشه‌ها می‌سازد."""

    # default
    default_img = IMAGES_DIR / "default.jpg"
    mapping = {
        "default": {
            "image":  str(default_img) if default_img.exists() else None,
            "folder": None,
            "music":  find_music("EW1133.wav"),
        }
    }

    # keywords
    keywords = {}
    for kw, (folder, music_file) in KEYWORD_MAP.items():
        folder_path = IMAGES_DIR / folder
        has_images  = folder_path.exists() and any(
            folder_path.glob("*.jpg")
        ) or any(folder_path.glob("*.png")) if folder_path.exists() else False

        if not folder_path.exists() or not any(folder_path.iterdir()):
            # پوشه خالی است → از default استفاده می‌شود
            continue

        keywords[kw] = {
            "folder": str(folder_path),   # ← پوشه، نه فایل مشخص
            "image":  None,               # ← خودکار انتخاب می‌شود
            "music":  find_music(music_file),
        }

    mapping["keywords"] = keywords

    print(f"  {len(keywords)} کلمه کلیدی با پوشه وصل شد.")
    return mapping


def save_mapping(mapping: dict):
    """mapping را در فایل JSON ذخیره می‌کند."""
    # برای JSON فقط مسیرهای نسبی ذخیره می‌کنیم
    root = ASSETS_DIR.parent

    def to_relative(path: str | None) -> str | None:
        if not path:
            return None
        try:
            return str(Path(path).relative_to(root))
        except ValueError:
            return path

    output = {
        "default": {
            "folder": to_relative(mapping["default"].get("folder")),
            "image":  to_relative(mapping["default"].get("image")),
            "music":  to_relative(mapping["default"].get("music")),
        },
        "keywords": {}
    }

    for kw, entry in mapping["keywords"].items():
        output["keywords"][kw] = {
            "folder": to_relative(entry.get("folder")),
            "image":  to_relative(entry.get("image")),
            "music":  to_relative(entry.get("music")),
        }

    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  ذخیره شد: {MAPPING_FILE}")


def main():
    print()
    print("=" * 50)
    print("  update_mapping.py")
    print("=" * 50)
    print()

    mapping = build_mapping()
    save_mapping(mapping)

    print()
    print("  ✅ mapping.json آپدیت شد.")
    print()
    print("  کلمات کلیدی فعال:")
    for kw, entry in mapping["keywords"].items():
        folder_name = Path(entry["folder"]).name if entry.get("folder") else "—"
        print(f"    {kw:12s} →  {folder_name}/")


if __name__ == "__main__":
    main()
