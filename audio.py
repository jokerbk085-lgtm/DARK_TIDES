"""
موتور صدای ducked — صدای اصلی هرگز تغییر نمی‌کند
"""

import subprocess
import numpy as np
from config import (
    AUDIO_SAMPLE_RATE, DUCKING_FRAME_SAMPLES,
    MUSIC_BG_LEVEL, MUSIC_SCENE_LEVEL, MUSIC_DUCKED_LEVEL,
    ATTACK_MS, RELEASE_MS, RMS_SPEECH_THRESH, DUCKING_KNEE,
)

_pcm_cache: dict[str, np.ndarray] = {}
_rms_cache: dict[str, np.ndarray] = {}


def _ffmpeg_path() -> str:
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        return get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def _load_pcm(path: str) -> np.ndarray:
    """فایل صوتی → float32 stereo (n_samples, 2) — cached"""
    if path in _pcm_cache:
        return _pcm_cache[path]
    cmd = [
        _ffmpeg_path(), "-i", path,
        "-f", "f32le", "-acodec", "pcm_f32le",
        "-ar", str(AUDIO_SAMPLE_RATE), "-ac", "2",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    data = np.frombuffer(proc.stdout, dtype=np.float32).reshape(-1, 2)
    _pcm_cache[path] = data
    return data


def _get_rms(voice_path: str) -> np.ndarray:
    """RMS per frame از صدای اصلی — cached"""
    if voice_path in _rms_cache:
        return _rms_cache[voice_path]
    pcm  = _load_pcm(voice_path)
    mono = pcm.mean(axis=1)
    n    = len(mono) // DUCKING_FRAME_SAMPLES
    frames = mono[:n * DUCKING_FRAME_SAMPLES].reshape(n, DUCKING_FRAME_SAMPLES)
    rms  = np.sqrt(np.mean(frames ** 2, axis=1)).astype(np.float32)
    _rms_cache[voice_path] = rms
    return rms


def _gain_envelope(rms: np.ndarray, unducked: float) -> np.ndarray:
    """gain envelope با soft-knee و IIR smoothing"""
    lo = RMS_SPEECH_THRESH - DUCKING_KNEE / 2
    hi = RMS_SPEECH_THRESH + DUCKING_KNEE / 2

    gain = np.full(len(rms), unducked, dtype=np.float32)
    gain[rms >= hi] = MUSIC_DUCKED_LEVEL

    mask = (rms >= lo) & (rms < hi)
    if np.any(mask):
        t = (rms[mask] - lo) / DUCKING_KNEE
        t = t * t * (3.0 - 2.0 * t)  # smoothstep
        gain[mask] = unducked + t * (MUSIC_DUCKED_LEVEL - unducked)

    # IIR smoothing
    fps   = AUDIO_SAMPLE_RATE / DUCKING_FRAME_SAMPLES
    a_atk = 1.0 / max(1, int(ATTACK_MS  / 1000 * fps))
    a_rel = 1.0 / max(1, int(RELEASE_MS / 1000 * fps))
    g     = gain.astype(np.float64)
    for i in range(1, len(g)):
        a    = a_atk if g[i] < g[i-1] else a_rel
        g[i] = g[i-1] + a * (g[i] - g[i-1])
    return g.astype(np.float32)


def build_music_track(
    timeline: list[dict],
    voice_path: str,
    audio_duration: float,
    fallback_music: str | None = None,
) -> np.ndarray:
    """
    ساخت آرایه PCM stereo کامل برای موسیقی ducked.
    هر صحنه در بازه sample خودش نوشته می‌شود — sequential، بدون overlap.
    """
    n_samples = int(audio_duration * AUDIO_SAMPLE_RATE)
    output    = np.zeros((n_samples, 2), dtype=np.float32)
    rms       = _get_rms(voice_path)

    for scene in timeline:
        music = scene.get("music") or fallback_music
        if not music:
            continue

        unducked = MUSIC_SCENE_LEVEL if scene.get("keyword") else MUSIC_BG_LEVEL
        s_idx    = int(scene["start"] * AUDIO_SAMPLE_RATE)
        e_idx    = min(int(scene["end"] * AUDIO_SAMPLE_RATE), n_samples)
        seg_len  = e_idx - s_idx
        if seg_len <= 0:
            continue

        music_pcm = _load_pcm(music)
        indices   = np.arange(s_idx, e_idx) % len(music_pcm)
        seg       = music_pcm[indices]

        env = _gain_envelope(rms, unducked)
        env_s = np.repeat(env, DUCKING_FRAME_SAMPLES)
        if len(env_s) < n_samples:
            env_s = np.concatenate([env_s, np.full(n_samples - len(env_s), unducked, dtype=np.float32)])

        output[s_idx:e_idx] = np.clip(seg * env_s[s_idx:e_idx, np.newaxis], -1.0, 1.0)

    return output


def pcm_to_audio_clip(data: np.ndarray, duration: float):
    from moviepy import AudioClip
    n = len(data)

    def make_frame(t):
        t_arr = np.atleast_1d(np.asarray(t, dtype=np.float64))
        idx   = np.clip((t_arr * AUDIO_SAMPLE_RATE).astype(np.int64), 0, n - 1)
        out   = data[idx]
        return out[0] if np.isscalar(t) else out

    return AudioClip(frame_function=make_frame, duration=duration, fps=AUDIO_SAMPLE_RATE)
