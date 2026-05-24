# DARK_TIDES

ابزار ساخت ویدیوی پادکست جنایی برای یوتیوب شورتز (فرمت ۹:۱۶).
متن گفتاری را می‌گیرد، با Whisper timestamp می‌زند، و به‌طور خودکار عکس‌های مرتبط را با موسیقی پس‌زمینه ترکیب می‌کند.

---

## ساختار پروژه

```
DARK_TIDES/
├── input/                    ← فایل‌های هر اپیزود اینجا می‌آیند
│   ├── audio.mp3             ← فایل صوتی (mp3/wav/m4a)
│   ├── script.txt            ← متن روایت (هر پاراگراف یک خط)
│   ├── keywords.txt          ← کلمات کلیدی اختصاصی این اپیزود
│   ├── transcript.json       ← خروجی prepare.py (ساخته می‌شود)
│   └── episode_mapping.json  ← خروجی prepare.py (ساخته می‌شود)
│
├── assets/
│   ├── images/               ← عکس‌ها دسته‌بندی شده در پوشه
│   │   ├── default.jpg       ← عکس پیش‌فرض
│   │   ├── city/
│   │   ├── court/
│   │   ├── crime/
│   │   ├── dark/
│   │   ├── person/
│   │   ├── police/
│   │   └── prison/
│   ├── music/                ← فایل‌های موسیقی WAV
│   │   ├── EW1133.wav
│   │   ├── Contraband.wav
│   │   ├── Roaring Silence.wav
│   │   └── Basmbs.wav
│   └── mapping.json          ← نگاشت کلی کلمات کلیدی
│
├── output/                   ← ویدیوهای خروجی اینجا ذخیره می‌شوند
│
├── main.py                   ← اجرای اصلی
├── prepare.py                ← آماده‌سازی transcript و mapping
├── update_mapping.py         ← به‌روزرسانی mapping.json کلی
├── config.py                 ← تنظیمات (کیفیت، FPS، ducking)
├── timeline_builder.py       ← ساخت timeline از transcript
├── video.py                  ← رندر ویدیو با moviepy
├── audio.py                  ← موسیقی با ducking خودکار
├── asr.py                    ← تشخیص گفتار با Whisper
├── run.bat                   ← اجرای سریع ویندوز
└── run.sh                    ← اجرای سریع لینوکس/مک
```

---

## نصب

**پیش‌نیاز:** Python 3.12 و ffmpeg

```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
openai-whisper>=20231117
moviepy>=2.1.1
numpy>=1.24,<2.0
Pillow>=10.0
imageio-ffmpeg>=0.4.9
```

---

## استفاده — روش سریع

### گام ۱: آماده‌سازی فایل‌های ورودی

فایل‌های زیر را در پوشه `input/` بگذارید:

| فایل | توضیح |
|------|-------|
| `audio.mp3` | فایل صوتی اپیزود |
| `script.txt` | متن روایت (هر پاراگراف یک خط) |
| `keywords.txt` | کلمات کلیدی اختصاصی (اختیاری) |

### گام ۲: ساخت transcript و mapping

```bash
py -3.12 prepare.py
```

این دستور:
- با Whisper timestamp می‌زند
- `transcript.json` می‌سازد
- `episode_mapping.json` می‌سازد

### گام ۳: رندر ویدیو

```bash
py -3.12 main.py
```

یا با دابل‌کلیک روی `run.bat`.

ویدیوی نهایی در `output/` ذخیره می‌شود.

---

## استفاده پیشرفته

```bash
# مسیر صدا را مستقیم بدهید
py -3.12 main.py input/episode01.mp3

# transcript آماده داشته باشید (بدون Whisper)
py -3.12 main.py --transcript input/transcript.json

# mapping اختصاصی
py -3.12 main.py --mapping input/episode_mapping.json

# خروجی با نام دلخواه
py -3.12 main.py --output output/episode01.mp4

# همه آرگومان‌ها با هم
py -3.12 main.py input/audio.mp3 \
  --transcript input/transcript.json \
  --mapping input/episode_mapping.json \
  --output output/episode01.mp4
```

---

## فرمت keywords.txt

```
# کلمه کلیدی = پوشه تصویر , موسیقی.wav
افغانستان = city , EW1133.wav
طالبان = person , Contraband.wav
قتل = crime , Contraband.wav
شب = dark
```

اگر موسیقی ننوشید، بر اساس نوع پوشه انتخاب می‌شود.

کلمات کلیدی پیش‌فرض (همیشه فعال):

| کلمه | پوشه | موسیقی |
|------|------|--------|
| جسد / کشته / قتل | crime | Contraband |
| پلیس / دستگیر / بازجویی | police | Contraband |
| دادگاه / محاکمه | court | EW1133 |
| زندان | prison | Contraband |
| قاتل | person | Contraband |
| شب / تاریکی / پرونده | dark | Roaring Silence |

---

## نحوه کار سیستم سینک عکس

```
صدا  ──────────────────────────────────────────────────►
        [ segment 1 ]      [قتل]   [ segment 3 ]
عکس  ── default ─────────── crime/ ─── default ──────────
موسیقی ── EW1133 ─────────── Contraband ─ EW1133 ─────────
```

- **Whisper** متن را word-by-word timestamp می‌زند
- وقتی keyword پیدا می‌شود، عکس مرتبط نمایش داده می‌شود + `hold_sec=1.5s` بعد از کلمه
- بین keyword‌ها، عکس default ثابت می‌ماند (بدون فلیکر)
- عکس‌ها با Ken Burns effect (zoom آرام) نمایش داده می‌شوند
- بین هر صحنه crossfade نیم‌ثانیه‌ای اعمال می‌شود

---

## تنظیمات `config.py`

```python
TARGET_W, TARGET_H = 1080, 1920   # رزولوشن شورتز
FPS           = 24
KEN_ZOOM      = 0.04              # شدت zoom کن‌برنز
CROSSFADE_DUR = 0.5               # مدت crossfade (ثانیه)
PRESET        = "ultrafast"       # سرعت رندر
CRF           = 23                # کیفیت (کمتر = بهتر)
THREADS       = 8                 # هسته‌های CPU

MUSIC_BG_LEVEL     = 0.20         # ولوم موسیقی در صحنه عادی
MUSIC_SCENE_LEVEL  = 0.40         # ولوم موسیقی در صحنه keyword
MUSIC_DUCKED_LEVEL = 0.06         # ولوم موسیقی زیر صدای گوینده
KEYWORD_HOLD_SEC   = 1.5          # مدت نگه‌داشتن عکس keyword
```

---

## اضافه کردن عکس جدید

عکس‌ها را در پوشه مناسب داخل `assets/images/` بگذارید:

```
assets/images/crime/crime_new.jpg
assets/images/police/police_new.jpg
```

پروژه به‌طور خودکار از بین عکس‌های هر پوشه تصادفی انتخاب می‌کند و از تکرار پشت‌سرهم جلوگیری می‌کند.

برای به‌روزرسانی `assets/mapping.json` کلی:

```bash
py -3.12 update_mapping.py
```

---

## خروجی

- **فرمت:** MP4 (H.264 + AAC)
- **رزولوشن:** 1080×1920 (9:16)
- **FPS:** 24
- **صدا:** صدای اصلی + موسیقی ducked
