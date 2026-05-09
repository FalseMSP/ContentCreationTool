# Automated YouTube Shorts Pipeline

Processes gameplay clips into 9:16 Shorts, burns in auto-generated captions
(Open Sans, word-highlight style), and uploads to YouTube.

---

## Project structure

```
shorts_pipeline/
├── config.py           ← ALL settings live here (paths, tags, subtitle style)
├── main.py             ← Entry point / CLI
├── video_processor.py  ← Crop, trim, resize logic
├── subtitler.py        ← Whisper transcription + Pillow caption renderer
├── uploader.py         ← YouTube OAuth + upload
├── requirements.txt
├── client_secret.json  ← OAuth credentials (you provide this)
├── fonts/
│   └── OpenSans-Bold.ttf   ← Download from fonts.google.com
└── token.pickle        ← Auto-generated after first auth
```

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

> **GPU acceleration** (optional, much faster transcription):
> ```bash
> pip install faster-whisper
> # and install the CUDA-enabled version of ctranslate2 for your GPU
> ```

### 2. Get the Open Sans font
Download **OpenSans-Bold.ttf** from https://fonts.google.com/specimen/Open+Sans  
and place it at `fonts/OpenSans-Bold.ttf`.

### 3. YouTube API credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → enable **YouTube Data API v3**
3. Create **OAuth 2.0 credentials** (Desktop app type)
4. Download the JSON and save it as `client_secret.json` in this folder

---

## Usage

```bash
# Process all videos in INPUT_DIRECTORY, upload, then clean up
python main.py

# Process only (no upload)
python main.py --no-upload

# Skip caption burning
python main.py --no-subtitles

# Keep source files
python main.py --no-delete

# Process a single file
python main.py --input "C:/path/to/clip.mp4"

# Add background music
python main.py --audio "C:/path/to/music.mp3"
```

---

## Subtitle customisation

Everything is in `config.py` inside the `SubtitleConfig` dataclass:

| Setting | Default | Effect |
|---|---|---|
| `font_size` | `100` | Caption size in pixels (80=small, 120=large) |
| `vertical_position` | `0.82` | 0=top of frame, 1=bottom |
| `max_words_per_segment` | `3` | Words shown at once |
| `all_caps` | `True` | Forces ALL CAPS (more punchy) |
| `highlight_current_word` | `True` | Yellow highlight on active word |
| `highlight_color` | yellow | RGB tuple |
| `stroke_width` | `6` | Outline thickness — increase for busy backgrounds |
| `background_enabled` | `False` | Semi-transparent pill behind text |
| `whisper_model` | `"base"` | `"tiny"` faster, `"small"`/`"medium"` more accurate |
| `whisper_device` | `"cpu"` | `"cuda"` for GPU |

---

## How subtitles work

1. Audio is extracted from the processed (cropped/trimmed) clip  
2. `faster-whisper` transcribes it with **word-level timestamps**  
3. Words are grouped into short bursts (controlled by `max_words_per_segment`)  
4. Each burst is rendered onto the frame using **Pillow** with:
   - Open Sans Bold font
   - Heavy black stroke outline (readable over gameplay)
   - Yellow highlight on whichever word is currently being spoken
   - Centred horizontally, positioned vertically at `vertical_position`
