"""
رندر ویدیوی سینمایی نهایی با سرعت بیشتر
"""

import numpy as np
from PIL import Image as PILImage, ImageFilter
from pathlib import Path
from moviepy import (
    VideoClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip,
)
from moviepy.video.fx import CrossFadeIn
from config import (
    TARGET_W, TARGET_H, FPS, KEN_ZOOM, CROSSFADE_DUR,
    VIDEO_CODEC, AUDIO_CODEC, AUDIO_BITRATE, CRF, PRESET, THREADS,
)
from audio import build_music_track, pcm_to_audio_clip

# vignette — یک‌بار پیش‌محاسبه
_vy, _vx = np.mgrid[0:TARGET_H, 0:TARGET_W]
_d = np.sqrt(((_vx - TARGET_W/2) / (TARGET_W*0.55))**2 + ((_vy - TARGET_H/2) / (TARGET_H*0.55))**2)
VIGNETTE = np.clip(1.0 - 0.55 * _d**2, 0.0, 1.0).astype(np.float32)

_img_cache: dict[str, np.ndarray] = {}

# تغییر: برای سرعت بیشتر، color grading را غیرفعال می‌کنیم
ENABLE_COLOR_GRADING = False   # اگر می‌خواهید افکت‌های سینمایی داشته باشید True کنید

def _grade(frame: np.ndarray) -> np.ndarray:
    """Color grading سینمایی ملایم (اختیاری)"""
    if not ENABLE_COLOR_GRADING:
        return frame
    f   = frame.astype(np.float32) / 255.0
    lum = 0.299*f[:,:,0] + 0.587*f[:,:,1] + 0.114*f[:,:,2]
    f   = f * 0.72 + lum[:,:,np.newaxis] * 0.28
    f   = np.clip(f * 1.12 - 0.05, 0.0, 1.0)
    sh  = np.clip(1.0 - lum * 2.5, 0.0, 1.0)
    f[:,:,2] = np.clip(f[:,:,2] + 0.05*sh, 0.0, 1.0)
    f[:,:,1] = np.clip(f[:,:,1] + 0.02*sh, 0.0, 1.0)
    f  *= VIGNETTE[:,:,np.newaxis]
    return (f * 255).astype(np.uint8)


def _make_vertical(img: PILImage.Image) -> PILImage.Image:
    """تبدیل عکس به فرمت عمودی 9:16 (بدون تغییر)"""
    iw, ih = img.size
    target_ratio = TARGET_W / TARGET_H
    img_ratio    = iw / ih

    if img_ratio <= target_ratio * 1.2:
        r  = max(TARGET_W / iw, TARGET_H / ih)
        nw, nh = int(iw * r) + 1, int(ih * r) + 1
        img = img.resize((nw, nh), PILImage.LANCZOS)
        l = (nw - TARGET_W) // 2
        t = (nh - TARGET_H) // 2
        return img.crop((l, t, l + TARGET_W, t + TARGET_H))

    bg = img.resize((TARGET_W, TARGET_H), PILImage.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
    bg_arr = np.array(bg).astype(np.float32) * 0.45
    bg = PILImage.fromarray(bg_arr.astype(np.uint8))

    scale   = TARGET_W / iw
    fg_w    = TARGET_W
    fg_h    = int(ih * scale)
    fg      = img.resize((fg_w, fg_h), PILImage.LANCZOS)
    y_offset = (TARGET_H - fg_h) // 2
    result   = bg.copy()
    result.paste(fg, (0, max(0, y_offset)))
    return result


def _load_img(path: str, scale: float) -> np.ndarray:
    """بارگذاری تصویر با padding برای Ken Burns"""
    key = f"{path}::{scale:.4f}"
    if key in _img_cache:
        return _img_cache[key]

    img     = PILImage.open(path).convert("RGB")
    vertical = _make_vertical(img)
    tw, th = int(TARGET_W * scale), int(TARGET_H * scale)
    r      = max(tw / TARGET_W, th / TARGET_H)
    nw     = int(TARGET_W * r) + 1
    nh     = int(TARGET_H * r) + 1
    padded = vertical.resize((nw, nh), PILImage.LANCZOS)
    l      = (nw - tw) // 2
    t      = (nh - th) // 2
    arr    = np.array(padded.crop((l, t, l + tw, t + th)))

    _img_cache[key] = arr
    return arr


def _ken_burns(image_path: str, duration: float, zoom_in: bool) -> VideoClip:
    """Ken Burns clip با سرعت بالاتر"""
    pad  = 1.0 + KEN_ZOOM
    base = _load_img(image_path, pad)
    h, w = base.shape[:2]

    def frame(t: float) -> np.ndarray:
        p    = max(0.0, min(1.0, t / max(duration, 1e-9)))
        zoom = (1.0 - KEN_ZOOM * p) if zoom_in else (1.0 - KEN_ZOOM + KEN_ZOOM * p)
        zoom = max(0.01, zoom)
        cw, ch = int(w * zoom), int(h * zoom)
        x,  y  = (w - cw) // 2, (h - ch) // 2
        crop   = base[y:y+ch, x:x+cw]
        resized = np.array(PILImage.fromarray(crop).resize((TARGET_W, TARGET_H), PILImage.LANCZOS))
        return _grade(resized)

    return VideoClip(frame_function=frame, duration=duration).with_fps(FPS)


def create_video(
    voice_path: str,
    timeline: list[dict],
    output_path: str,
    fallback_music: str | None = None,
) -> None:
    """رندر ویدیوی نهایی — صدای اصلی untouched"""
    print("  بارگذاری صدای اصلی...")
    voice_clip     = AudioFileClip(voice_path)
    audio_duration = voice_clip.duration

    # موسیقی ducked
    has_music = any(s.get("music") for s in timeline) or fallback_music
    if has_music:
        print("  ساخت موسیقی ducked...")
        music_pcm   = build_music_track(timeline, voice_path, audio_duration, fallback_music)
        music_clip  = pcm_to_audio_clip(music_pcm, audio_duration)
        final_audio = CompositeAudioClip([voice_clip, music_clip])
    else:
        print("  ⚠️  موسیقی پیدا نشد — فقط صدای اصلی.")
        final_audio = voice_clip

    # کلیپ‌های ویدیویی
    print(f"  ساخت {len(timeline)} کلیپ تصویری...")
    clips = []
    for i, scene in enumerate(timeline):
        img = scene.get("image")
        if not img or not Path(img).exists():
            print(f"  ⚠️  تصویر صحنه {i} پیدا نشد، رد شد.")
            continue

        dur       = scene["end"] - scene["start"]
        is_first  = (len(clips) == 0)
        can_xfade = not is_first and CROSSFADE_DUR > 0 and dur > CROSSFADE_DUR * 2

        if can_xfade:
            clip_start = max(0.0, scene["start"] - CROSSFADE_DUR)
            clip_dur   = dur + CROSSFADE_DUR
        else:
            clip_start = scene["start"]
            clip_dur   = dur

        clip = _ken_burns(img, clip_dur, zoom_in=(i % 2 == 0))
        if can_xfade:
            clip = clip.with_effects([CrossFadeIn(CROSSFADE_DUR)])
        clips.append(clip.with_start(clip_start))

    if not clips:
        raise RuntimeError("هیچ تصویری برای رندر پیدا نشد.")

    print("  رندر نهایی...")
    final = (
        CompositeVideoClip(clips, size=(TARGET_W, TARGET_H))
        .with_duration(audio_duration)
        .with_audio(final_audio)
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        output_path,
        fps=FPS, codec=VIDEO_CODEC,
        audio_codec=AUDIO_CODEC, audio_bitrate=AUDIO_BITRATE,
        threads=THREADS,
        ffmpeg_params=["-preset", PRESET, "-crf", str(CRF)],
        logger=None,
    )
    voice_clip.close()
    print(f"  ✓ ذخیره شد: {output_path}")