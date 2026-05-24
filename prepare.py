"""
prepare.py
----------
۱. keywords.txt را می‌خواند و mapping موقت می‌سازد
۲. MP3 را با Whisper تحلیل می‌کند و timestamp می‌گیرد
۳. متن script.txt را با timestamp ترکیب می‌کند
۴. transcript.json می‌سازد

استفاده:
    py -3.12 prepare.py
"""

import json
import re
from pathlib import Path
import whisper
from config import INPUT_DIR, MAPPING_FILE, IMAGES_DIR, MUSIC_DIR, WHISPER_MODEL


# ══════════════════════════════════════════════════════════════
# خواندن keywords.txt
# ══════════════════════════════════════════════════════════════

def load_keywords(path: Path) -> dict[str, tuple[str, str]]:
    """
    keywords.txt را می‌خواند.
    فرمت هر خط:
        کلمه کلیدی = پوشه_تصویر
        کلمه کلیدی = پوشه_تصویر , موسیقی.wav

    مثال:
        افغانستان = city
        طالبان = person , Contraband.wav
        قتل = crime , Contraband.wav

    خروجی: {keyword: (folder, music_file)}
    """
    result = {}
    if not path.exists():
        print("  ⚠️  keywords.txt پیدا نشد — فقط از کلمات پیش‌فرض استفاده می‌شود.")
        return result

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        parts = line.split("=", 1)
        kw    = parts[0].strip()
        rest  = parts[1].strip()

        if "," in rest:
            folder, music = [x.strip() for x in rest.split(",", 1)]
        else:
            folder = rest.strip()
            music  = _default_music_for_folder(folder)

        if kw:
            result[kw.lower()] = (folder, music)

    print(f"  {len(result)} کلمه کلیدی از keywords.txt خوانده شد.")
    return result


def _default_music_for_folder(folder: str) -> str:
    """موسیقی پیش‌فرض برای هر نوع پوشه"""
    dark_folders = {"crime", "prison", "person", "dark"}
    if folder in dark_folders:
        return "Contraband.wav"
    return "EW1133.wav"


# ══════════════════════════════════════════════════════════════
# ساخت mapping موقت برای این اپیزود
# ══════════════════════════════════════════════════════════════

# کلمات کلیدی پیش‌فرض که همیشه فعال هستند
DEFAULT_KEYWORDS = {
    "جسد":     ("crime",  "Contraband.wav"),
    "کشته":    ("crime",  "Contraband.wav"),
    "قتل":     ("crime",  "Contraband.wav"),
    "پلیس":    ("police", "Contraband.wav"),
    "دستگیر":  ("police", "Contraband.wav"),
    "بازجویی": ("police", "EW1133.wav"),
    "دادگاه":  ("court",  "EW1133.wav"),
    "محاکمه":  ("court",  "EW1133.wav"),
    "زندان":   ("prison", "Contraband.wav"),
    "قاتل":    ("person", "Contraband.wav"),
    "شب":      ("dark",   "Roaring Silence.wav"),
    "تاریکی":  ("dark",   "Roaring Silence.wav"),
    "پرونده":  ("dark",   "EW1133.wav"),
}


def build_episode_mapping(episode_keywords: dict[str, tuple[str, str]]) -> dict:
    """
    mapping کامل این اپیزود را می‌سازد:
    کلمات پیش‌فرض + کلمات اختصاصی این اپیزود
    """
    # default image و music
    default_img   = IMAGES_DIR / "default.jpg"
    default_music = MUSIC_DIR / "EW1133.wav"

    mapping = {
        "default": {
            "folder": None,
            "image":  str(default_img) if default_img.exists() else None,
            "music":  str(default_music) if default_music.exists() else None,
        },
        "keywords": {}
    }

    # ترکیب کلمات پیش‌فرض + اختصاصی (اختصاصی override می‌کند)
    all_keywords = {**DEFAULT_KEYWORDS, **episode_keywords}

    for kw, (folder, music_file) in all_keywords.items():
        folder_path = IMAGES_DIR / folder
        music_path  = MUSIC_DIR / music_file

        # بررسی وجود پوشه
        if not folder_path.exists() or not any(folder_path.iterdir()):
            print(f"  ⚠️  پوشه خالی یا ناموجود: {folder}/ — کلمه '{kw}' از default استفاده می‌کند")
            continue

        mapping["keywords"][kw] = {
            "folder": str(folder_path),
            "image":  None,
            "music":  str(music_path) if music_path.exists() else mapping["default"]["music"],
        }

    print(f"  {len(mapping['keywords'])} کلمه کلیدی فعال شد.")
    return mapping


# ══════════════════════════════════════════════════════════════
# ساخت transcript با timestamp
# ══════════════════════════════════════════════════════════════

def build_transcript(text_path: Path, audio_path: Path, language: str = "fa") -> list[dict]:
    """
    متن را از script.txt می‌خواند.
    timestamp را از MP3 با Whisper می‌گیرد.
    ترکیب می‌کند و transcript.json می‌سازد.
    """
    # خواندن متن
    raw   = text_path.read_text(encoding="utf-8").strip()
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines:
        raise ValueError("script.txt خالی است.")
    print(f"  {len(lines)} خط در script.txt پیدا شد.")

    # Whisper برای timestamp
    print(f"  بارگذاری Whisper ({WHISPER_MODEL})...")
    model  = whisper.load_model(WHISPER_MODEL)
    print(f"  تشخیص timestamp از MP3...")
    result = model.transcribe(
        str(audio_path),
        language=language,
        task="transcribe",
        verbose=False,
        fp16=False,
    )

    total_duration = float(result["segments"][-1]["end"]) if result["segments"] else 0
    print(f"  مدت کل: {total_duration:.1f}s")

    # تقسیم زمان بر اساس نسبت طول هر خط
    total_chars = sum(len(l) for l in lines)
    segments    = []
    cursor      = 0.0

    for i, line in enumerate(lines):
        ratio = len(line) / max(total_chars, 1)
        dur   = total_duration * ratio
        start = round(cursor, 3)
        end   = round(min(cursor + dur, total_duration), 3)
        if i == len(lines) - 1:
            end = total_duration
        if end > start:
            segments.append({"start": start, "end": end, "text": line})
        cursor = end

    print(f"  {len(segments)} segment ساخته شد.")
    return segments


# ══════════════════════════════════════════════════════════════
# اجرای اصلی
# ══════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="fa")
    args = parser.parse_args()

    print()
    print("=" * 55)
    print("  prepare.py — آماده‌سازی اپیزود")
    print("=" * 55)

    # ── پیدا کردن فایل‌ها ─────────────────────────────────────
    keywords_path  = INPUT_DIR / "keywords.txt"
    script_path    = INPUT_DIR / "script.txt"
    transcript_out = INPUT_DIR / "transcript.json"
    mapping_out    = INPUT_DIR / "episode_mapping.json"

    # پیدا کردن MP3
    audio_path = None
    for ext in ("*.mp3", "*.wav", "*.m4a"):
        files = sorted(INPUT_DIR.glob(ext))
        if files:
            audio_path = files[0]
            break

    if not audio_path:
        print("❌ هیچ فایل صوتی در input/ پیدا نشد.")
        return

    if not script_path.exists():
        print("❌ script.txt در input/ پیدا نشد.")
        return

    print(f"\n  صدا    : {audio_path.name}")
    print(f"  متن    : script.txt")
    if keywords_path.exists():
        print(f"  کلمات  : keywords.txt")

    # ── خواندن keywords.txt ───────────────────────────────────
    print("\n[1/3] خواندن کلمات کلیدی...")
    episode_kws = load_keywords(keywords_path)
    mapping     = build_episode_mapping(episode_kws)

    # ذخیره mapping اپیزود
    with open(mapping_out, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"  mapping ذخیره شد: episode_mapping.json")

    # ── ساخت transcript ───────────────────────────────────────
    print("\n[2/3] ساخت transcript...")
    segments = build_transcript(script_path, audio_path, args.language)

    # ── ذخیره transcript ──────────────────────────────────────
    print("\n[3/3] ذخیره transcript.json...")
    with open(transcript_out, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    print()
    for s in segments:
        print(f"  [{s['start']:6.1f}s → {s['end']:6.1f}s]  {s['text'][:55]}")

    print()
    print("=" * 55)
    print("  ✅ آماده‌سازی تمام شد.")
    print("=" * 55)
    print()
    print("  حالا اجرا کنید:")
    print(f"  py -3.12 main.py --transcript input/transcript.json --mapping input/episode_mapping.json")


if __name__ == "__main__":
    main()
