from pathlib import Path

# ── مسیرها ────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent
ASSETS_DIR   = BASE_DIR / "assets"
IMAGES_DIR   = ASSETS_DIR / "images"
MUSIC_DIR    = ASSETS_DIR / "music"
MAPPING_FILE = ASSETS_DIR / "mapping.json"
INPUT_DIR    = BASE_DIR / "input"
OUTPUT_DIR   = BASE_DIR / "output"

# ── ویدیو ─────────────────────────────────────────────────────
TARGET_W      = 1080
TARGET_H      = 1920
FPS           = 24               # کاهش FPS برای سرعت بیشتر (قبلاً 30)
KEN_ZOOM      = 0.04
CROSSFADE_DUR = 0.5

VIDEO_CODEC   = "libx264"
AUDIO_CODEC   = "aac"
AUDIO_BITRATE = "192k"
CRF           = 23               # کیفیت کمی پایین‌تر ولی خیلی سریع‌تر (قبلاً 18)
PRESET        = "ultrafast"      # سریع‌ترین preset (قبلاً fast)
THREADS       = 8                # اگر CPU شما ۸ هسته دارد (تغییر دهید)

# ── صدا و ducking ─────────────────────────────────────────────
AUDIO_SAMPLE_RATE     = 44_100
DUCKING_FRAME_SAMPLES = 2048

MUSIC_BG_LEVEL     = 0.20
MUSIC_SCENE_LEVEL  = 0.40
MUSIC_DUCKED_LEVEL = 0.06
ATTACK_MS          = 80
RELEASE_MS         = 1800
RMS_SPEECH_THRESH  = 0.04
DUCKING_KNEE       = 0.03

# ── Whisper ───────────────────────────────────────────────────
WHISPER_MODEL    = "base"

# ── رفتار ────────────────────────────────────────────────────
KEYWORD_HOLD_SEC = 1.5            # کمی کمتر برای پاسخ سریع‌تر (قبلاً 2.0)
AUTO_CREATE_DIRS = True