"""
organize_images.py
------------------
همه عکس‌های پراکنده در assets/images را
به پوشه‌های مناسب منتقل می‌کند و اسم تمیز می‌دهد.

استفاده:
    python organize_images.py
"""

import shutil
from pathlib import Path
from config import IMAGES_DIR

# ── پوشه‌هایی که باید وجود داشته باشند ──────────────────────
FOLDERS = ["city", "crime", "police", "dark", "court", "prison", "person"]

# ── قوانین دسته‌بندی بر اساس کلمات در اسم فایل ──────────────
# اگر این کلمات در اسم فایل بود → آن پوشه
RULES = [
    (["police", "cop", "detective", "investigation", "chase", "pll", "interrogat"], "police"),
    (["court", "courtroom", "judge", "trial", "محاکمه"],                            "court"),
    (["prison", "jail", "cell", "زندان"],                                           "prison"),
    (["crime", "murder", "victim", "جسد", "pengle", "hyper", "natural_human"],     "crime"),
    (["city", "tehran", "street", "urban", "downtown", "night_city", "شهر"],       "city"),
    (["killer", "shadow", "silhouette", "person", "figure", "mafia", "boss"],      "person"),
    (["dark", "mystery", "fog", "house", "room", "alley", "noir", "bat", "welcome",
      "newspaper", "icartoon", "default_prompt", "leonardo", "prompt_آماده"],      "dark"),
]

# ── فایل‌هایی که باید حذف شوند ───────────────────────────────
DELETE_PATTERNS = [
    "PUT_IMAGES_HERE",
    ".txt",
]


def guess_folder(filename: str) -> str:
    """بر اساس اسم فایل، پوشه مناسب را حدس می‌زند."""
    name_lower = filename.lower()
    for keywords, folder in RULES:
        for kw in keywords:
            if kw.lower() in name_lower:
                return folder
    return "dark"  # پیش‌فرض


def organize():
    print()
    print("=" * 50)
    print("  organize_images.py")
    print("=" * 50)

    # ساخت پوشه‌ها
    for folder in FOLDERS:
        (IMAGES_DIR / folder).mkdir(exist_ok=True)

    # پیدا کردن همه عکس‌ها در root پوشه images
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    files = [
        f for f in IMAGES_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    ]

    if not files:
        print("  هیچ عکسی در images/ پیدا نشد.")
        return

    print(f"\n  {len(files)} فایل پیدا شد:\n")

    moved   = 0
    skipped = 0

    for f in sorted(files):
        # حذف فایل‌های placeholder
        if any(p in f.name for p in DELETE_PATTERNS):
            f.unlink()
            print(f"  🗑️  حذف شد: {f.name}")
            continue

        # default.jpg در root می‌ماند
        if f.stem.lower() == "default":
            print(f"  ✓  نگه داشته شد: {f.name}")
            skipped += 1
            continue

        # تعیین پوشه مناسب
        folder = guess_folder(f.name)
        dest_dir = IMAGES_DIR / folder

        # شماره‌گذاری خودکار
        existing = list(dest_dir.glob(f"*{f.suffix}"))
        new_name = f"{folder}_{len(existing) + 1:02d}{f.suffix.lower()}"
        dest     = dest_dir / new_name

        # انتقال
        shutil.move(str(f), str(dest))
        print(f"  ✓  {f.name[:45]:<45} →  {folder}/{new_name}")
        moved += 1

    print()
    print(f"  {moved} فایل منتقل شد.")
    print(f"  {skipped} فایل در جای خود ماند.")
    print()
    print("  ساختار نهایی:")
    for folder in FOLDERS:
        count = len(list((IMAGES_DIR / folder).glob("*.*")))
        if count > 0:
            print(f"    {folder}/  ← {count} عکس")

    print()
    print("  ✅ تمام شد.")
    print()
    print("  حالا mapping.json را آپدیت کنید:")
    print("  python update_mapping.py")


if __name__ == "__main__":
    organize()
