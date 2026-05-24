"""
تشخیص گفتار با Whisper (word-level timestamps) یا بارگذاری transcript JSON
"""

import json
import whisper
from pathlib import Path
from config import WHISPER_MODEL

_model = None

def _get_model():
    global _model
    if _model is None:
        print(f"  بارگذاری Whisper ({WHISPER_MODEL})...")
        _model = whisper.load_model(WHISPER_MODEL)
    return _model


def transcribe(audio_path: str, language: str = "fa") -> list[dict]:
    """
    صدای را با Whisper + word-level timestamps تبدیل می‌کند.
    خروجی: لیست segment‌ها (هر segment = یک کلمه)
    هر segment: {"start": float, "end": float, "text": str}
    """
    model = _get_model()
    print(f"  تشخیص گفتار: {Path(audio_path).name} (word-level)")

    result = model.transcribe(
        audio_path,
        language=language,
        task="transcribe",
        verbose=False,
        fp16=False,
        word_timestamps=True,          # <-- کلید حل مشکل سینک
    )

    segments = []
    for seg in result["segments"]:
        for word in seg.get("words", []):
            text = word["word"].strip()
            if text:
                segments.append({
                    "start": float(word["start"]),
                    "end":   float(word["end"]),
                    "text":  text,
                })

    print(f"  {len(segments)} کلمه شناسایی شد.")
    return segments


def load_transcript(path: str) -> list[dict]:
    """
    بارگذاری transcript از فایل JSON.
    فرمت: [{"start": float, "end": float, "text": str}, ...]
    اگر فایل حاوی word-level نباشد (یعنی segments طولانی)،
    همچنان کار می‌کند ولی دقت سینک کمتر است.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = []
    for i, item in enumerate(data):
        try:
            start = float(item["start"])
            end   = float(item["end"])
            text  = str(item.get("text", "")).strip()
            if end > start and text:
                segments.append({"start": start, "end": end, "text": text})
        except (KeyError, ValueError, TypeError):
            print(f"  segment {i} نامعتبر، رد شد.")

    print(f"  {len(segments)} segment از فایل بارگذاری شد.")
    return segments