"""
timeline_builder.py
-------------------
ساخت timeline منطقی — بدون MoviePy، بدون numpy
از پوشه‌های دسته‌بندی‌شده عکس تصادفی انتخاب می‌کند.
"""

import json
import random
from pathlib import Path
from config import MAPPING_FILE

_TOL = 1e-4

# ── کش پوشه‌ها ────────────────────────────────────────────────
_folder_cache: dict[str, list[str]] = {}
_last_picked:  dict[str, int]       = {}


def _pick_from_folder(folder: str | None, fallback: str | None) -> str | None:
    """
    یک عکس تصادفی از پوشه انتخاب می‌کند.
    تضمین می‌کند دو بار پشت سر هم همان عکس انتخاب نشود.
    اگر پوشه خالی بود → fallback برمی‌گردد.
    """
    if not folder:
        return fallback

    p = Path(folder)
    if not p.exists():
        return fallback

    if folder not in _folder_cache:
        exts  = {".jpg", ".jpeg", ".png", ".webp"}
        files = [str(f) for f in sorted(p.iterdir()) if f.suffix.lower() in exts]
        _folder_cache[folder] = files

    files = _folder_cache[folder]
    if not files:
        return fallback
    if len(files) == 1:
        return files[0]

    last    = _last_picked.get(folder, -1)
    choices = [i for i in range(len(files)) if i != last]
    idx     = random.choice(choices)
    _last_picked[folder] = idx
    return files[idx]


def load_mapping(path: str | None = None) -> dict:
    """
    بارگذاری mapping.json.
    از فیلد folder (پوشه) یا image (فایل مستقیم) استفاده می‌کند.

    خروجی:
    {
        "default":  {"folder": str|None, "image": str|None, "music": str|None},
        "keywords": {keyword_lower: {"folder": str|None, "image": str|None, "music": str|None}}
    }
    """
    mf = Path(path) if path else MAPPING_FILE
    if not mf.exists():
        raise FileNotFoundError(f"mapping.json پیدا نشد: {mf}")

    with open(mf, "r", encoding="utf-8") as f:
        raw = json.load(f)

    root = mf.parent.parent  # root پروژه

    def resolve_path(p: str | None) -> str | None:
        """مسیر نسبی → مسیر کامل، بررسی وجود فایل/پوشه"""
        if not p:
            return None
        full = Path(p) if Path(p).is_absolute() else root / p
        if full.exists():
            return str(full)
        print(f"  ⚠️  پیدا نشد: {p}")
        return None

    # default
    default_raw = raw.get("default") or {}
    default = {
        "folder": resolve_path(default_raw.get("folder")),
        "image":  resolve_path(default_raw.get("image")),
        "music":  resolve_path(default_raw.get("music")),
    }

    # keywords
    keywords = {}
    for kw, entry in (raw.get("keywords") or {}).items():
        entry = entry or {}
        folder = resolve_path(entry.get("folder"))
        image  = resolve_path(entry.get("image"))
        music  = resolve_path(entry.get("music"))

        # fallback موسیقی به default
        if not music:
            music = default["music"]

        keywords[kw.lower()] = {
            "folder": folder,
            "image":  image,
            "music":  music,
        }

    print(f"  {len(keywords)} کلمه کلیدی بارگذاری شد.")
    return {"default": default, "keywords": keywords}


def get_keywords(mapping: dict) -> list[str]:
    return list(mapping["keywords"].keys())


def _get_image(entry: dict, default: dict) -> str | None:
    """
    تصویر مناسب را از entry برمی‌گرداند.
    اول folder → تصادفی، بعد image → مستقیم، بعد default.
    """
    img = _pick_from_folder(entry.get("folder"), entry.get("image"))
    if img:
        return img
    # fallback به default
    return _pick_from_folder(default.get("folder"), default.get("image"))


def build_timeline(
    audio_duration: float,
    segments: list[dict] | None,
    mapping: dict,
    hold_sec: float = 2.0,
) -> list[dict]:
    """
    ساخت timeline کامل از 0.0 تا audio_duration.
    هر segment → یک scene.
    گپ‌ها با default پر می‌شوند.
    عکس‌های default تا تغییر keyword ثابت می‌مانند.
    """
    default = mapping["default"]
    kw_map  = mapping["keywords"]
    kw_list = list(kw_map.keys())

    # عکس default در طول یک build ثابت می‌ماند تا فلیکر نشود
    _default_img_holder: list[str | None] = [None]

    def find_keyword(text: str) -> str | None:
        t = text.lower()
        for kw in kw_list:
            if kw in t:
                return kw
        return None

    def make_scene(start, end, text, keyword, image, music):
        return {
            "start":    round(start, 6),
            "end":      round(end,   6),
            "duration": round(end - start, 6),
            "text":     text,
            "keyword":  keyword,
            "image":    image,
            "music":    music,
        }

    def default_scene(start, end, text=""):
        # عکس default را یک‌بار انتخاب می‌کنیم و نگه می‌داریم
        if _default_img_holder[0] is None:
            _default_img_holder[0] = _get_image(default, default)
        return make_scene(start, end, text, None, _default_img_holder[0], default["music"])

    def refresh_default_img():
        """بعد از هر keyword scene، عکس default را تغییر می‌دهیم"""
        _default_img_holder[0] = _get_image(default, default)

    # بدون segment → یک scene کامل default
    if not segments:
        return [default_scene(0.0, audio_duration)]

    # فیلتر segmentهای معتبر
    valid = []
    for s in segments:
        try:
            start = float(s["start"])
            end   = float(s["end"])
            text  = str(s.get("text", "")).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if start < 0 or end <= start or start >= audio_duration:
            continue
        end = min(end, audio_duration)
        kw  = find_keyword(text)
        if kw:
            end = min(end + hold_sec, audio_duration)
        valid.append((start, end, text, kw))

    valid.sort(key=lambda x: x[0])

    # رفع تداخل
    resolved = []
    for item in valid:
        s, e, text, kw = item
        if resolved and s < resolved[-1][1]:
            s = resolved[-1][1]
        if s >= e:
            continue
        resolved.append((s, e, text, kw))

    # ساخت timeline
    timeline = []
    cursor   = 0.0

    for s, e, text, kw in resolved:
        if s > cursor + _TOL:
            timeline.append(default_scene(cursor, s))

        if kw:
            entry = kw_map[kw]
            img   = _get_image(entry, default)
            timeline.append(make_scene(s, e, text, kw, img, entry["music"]))
            refresh_default_img()  # بعد از keyword، عکس default عوض می‌شود
        else:
            timeline.append(default_scene(s, e, text))

        cursor = e

    if cursor < audio_duration - _TOL:
        timeline.append(default_scene(cursor, audio_duration))

    # ادغام صحنه‌های default پشت سر هم (با همان عکس)
    # بدون این، word-level timestamps صدها کلیپ کوچک می‌سازد
    merged = []
    for scene in timeline:
        if (
            merged
            and scene["keyword"] is None
            and merged[-1]["keyword"] is None
            and scene["image"] == merged[-1]["image"]
            and abs(scene["start"] - merged[-1]["end"]) < _TOL
        ):
            merged[-1]["end"]      = scene["end"]
            merged[-1]["duration"] = round(scene["end"] - merged[-1]["start"], 6)
            merged[-1]["text"]     = (merged[-1]["text"] + " " + scene["text"]).strip()
        else:
            merged.append(dict(scene))
    timeline = merged

    # تضمین دقت floating point
    if timeline:
        timeline[0]["start"]     = 0.0
        timeline[0]["duration"]  = round(timeline[0]["end"], 6)
        timeline[-1]["end"]      = audio_duration
        timeline[-1]["duration"] = round(audio_duration - timeline[-1]["start"], 6)

    validate_timeline(timeline, audio_duration)
    return timeline


def validate_timeline(timeline: list[dict], audio_duration: float) -> None:
    if not timeline:
        raise ValueError("timeline خالی است.")
    if abs(timeline[0]["start"]) > _TOL:
        raise ValueError(f"timeline از {timeline[0]['start']} شروع می‌شود.")
    if abs(timeline[-1]["end"] - audio_duration) > _TOL:
        raise ValueError(f"timeline در {timeline[-1]['end']} تمام می‌شود.")
    for i in range(1, len(timeline)):
        gap = timeline[i]["start"] - timeline[i-1]["end"]
        if gap > _TOL:
            raise ValueError(f"gap در timeline: صحنه {i-1}→{i}")
        if gap < -_TOL:
            raise ValueError(f"overlap در timeline: صحنه {i-1}→{i}")


if __name__ == "__main__":
    # تست سریع
    mapping = {
        "default": {"folder": None, "image": "default.jpg", "music": "bg.wav"},
        "keywords": {
            "پلیس": {"folder": None, "image": "police.jpg", "music": "dark.wav"},
            "جسد":  {"folder": None, "image": "crime.jpg",  "music": "dark.wav"},
        }
    }
    segs = [
        {"start": 5.0,  "end": 15.0, "text": "پلیس وارد شد"},
        {"start": 20.0, "end": 30.0, "text": "جسد پیدا شد"},
        {"start": 35.0, "end": 45.0, "text": "تهران در وحشت"},
    ]
    tl = build_timeline(60.0, segs, mapping)
    total = sum(s["duration"] for s in tl)
    print(f"{len(tl)} صحنه — {total:.2f}s")
    for s in tl:
        kw = f"[{s['keyword']}]" if s["keyword"] else "[default]"
        print(f"  {s['start']:5.1f}→{s['end']:5.1f}  {kw}")
    print("✅ تست موفق")
