"""
DARK_TIDES — ساخت ویدیوی پادکست جنایی
"""

import sys
import argparse
from pathlib import Path
from moviepy import AudioFileClip

from config import INPUT_DIR, OUTPUT_DIR, KEYWORD_HOLD_SEC, AUTO_CREATE_DIRS
from timeline_builder import load_mapping, get_keywords, build_timeline
from asr import transcribe, load_transcript
from video import create_video


def ensure_dirs():
    if AUTO_CREATE_DIRS:
        for d in [INPUT_DIR, OUTPUT_DIR]:
            d.mkdir(parents=True, exist_ok=True)


def find_audio(arg: str) -> Path:
    if arg:
        p = Path(arg)
        if p.exists(): return p
        c = INPUT_DIR / p
        if c.exists(): return c
        print(f"No audio file found: {arg}")
        sys.exit(1)
    for ext in ("*.mp3", "*.wav", "*.m4a"):
        files = sorted(INPUT_DIR.glob(ext))
        if files:
            print(f"  Audio: {files[0].name}")
            return files[0]
    print("No audio file found in input/")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="DARK_TIDES")
    parser.add_argument("audio",        nargs="?", default="")
    parser.add_argument("--transcript", default="")
    parser.add_argument("--mapping",    default="",   help="مسیر mapping (پیش‌فرض: assets/mapping.json)")
    parser.add_argument("--language",   default="fa")
    parser.add_argument("--output",     default="")
    parser.add_argument("--hold",       type=float, default=KEYWORD_HOLD_SEC)
    args = parser.parse_args()

    ensure_dirs()
    audio_path = find_audio(args.audio)
    output     = args.output or str(OUTPUT_DIR / f"{audio_path.stem}_video.mp4")

    print()
    print("=" * 55)
    print("  DARK_TIDES")
    print("=" * 55)
    print(f"  Audio  : {audio_path.name}")
    print(f"  Output : {output}")

    # ── ۱. mapping ────────────────────────────────────────────
    print("\n[1/4] Loading mapping...")

    # اول دنبال episode_mapping.json در input/ بگرد
    episode_mapping = INPUT_DIR / "episode_mapping.json"
    if args.mapping:
        mapping_path = args.mapping
    elif episode_mapping.exists():
        mapping_path = str(episode_mapping)
        print(f"  Using episode mapping: episode_mapping.json")
    else:
        mapping_path = None

    mapping  = load_mapping(mapping_path)
    keywords = get_keywords(mapping)
    print(f"  Keywords: {', '.join(keywords[:8])}{'...' if len(keywords) > 8 else ''}")

    # ── ۲. transcript ─────────────────────────────────────────
    if args.transcript:
        print("\n[2/4] Loading transcript from JSON...")
        segments = load_transcript(args.transcript)
    else:
        # دنبال transcript.json در input/ بگرد
        default_transcript = INPUT_DIR / "transcript.json"
        if default_transcript.exists():
            print("\n[2/4] Loading transcript.json...")
            segments = load_transcript(str(default_transcript))
        else:
            print("\n[2/4] Running Whisper...")
            segments = transcribe(str(audio_path), language=args.language)

    # ── ۳. timeline ───────────────────────────────────────────
    print("\n[3/4] Building timeline...")
    clip     = AudioFileClip(str(audio_path))
    duration = clip.duration
    clip.close()
    print(f"  Duration: {duration:.1f}s ({duration/60:.1f} min)")

    timeline = build_timeline(duration, segments, mapping, hold_sec=args.hold)
    print(f"  {len(timeline)} scenes built.")
    print()
    for s in timeline:
        kw  = f"[{s['keyword']}]" if s['keyword'] else "[default]"
        img = Path(s['image']).name if s.get('image') else "—"
        print(f"    {s['start']:6.1f}s → {s['end']:6.1f}s  {kw:14s}  {img}")

    # ── ۴. رندر ──────────────────────────────────────────────
    print("\n[4/4] Rendering video...")
    create_video(
        voice_path=str(audio_path),
        timeline=timeline,
        output_path=output,
        fallback_music=mapping["default"]["music"],
    )

    print()
    print("=" * 55)
    print("  Done!")
    print(f"  {output}")
    print("=" * 55)


if __name__ == "__main__":
    main()
