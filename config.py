"""
Central configuration for the Shorts pipeline.
Edit the values here to change behaviour across the entire pipeline.
"""

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
INPUT_DIRECTORY = "C:/Users/markp/Videos/Clip_Input/"

# ---------------------------------------------------------------------------
# YouTube metadata
# ---------------------------------------------------------------------------
YOUTUBE_SCOPES     = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_CATEGORY_ID = "20"      # Gaming
YOUTUBE_PRIVACY     = "unlisted" # "public" | "unlisted" | "private"

DEFAULT_DESCRIPTION = (
    "Redlife/Bluelife does impressive Omen outplays to get free kills"
)
DEFAULT_TAGS = [
    "Omen Outplay", "Flick", "Valorant",
    "Valorant Ace", "Valorant 5k", "Valorant 6k",
]

# ---------------------------------------------------------------------------
# Video processing
# ---------------------------------------------------------------------------
TRIM_FRONT_SECONDS: float = 0.0
TRIM_END_SECONDS:   float = 0.0
OUTPUT_WIDTH        = 1080
OUTPUT_HEIGHT       = 1920
SHORTS_MAX_DURATION = 9999    # YouTube Shorts hard limit (seconds)

# ---------------------------------------------------------------------------
# Subtitle configuration
# ---------------------------------------------------------------------------

@dataclass
class SubtitleConfig:
    """
    Controls transcription, the interactive SRT edit step, and FFmpeg burn-in.

    Workflow
    --------
    1. Whisper transcribes the clip word-by-word
    2. An SRT file is written and opened in your text editor
    3. You fix any mistranscriptions, save, press ENTER
    4. FFmpeg burns the (edited) captions directly into the video
       with a scale-bounce pop animation — one word at a time

    Font
    ----
    Put OpenSans-Bold.ttf (from fonts.google.com) at fonts/OpenSans-Bold.ttf

    Transcription
    -------------
    whisper_model        "large-v3" most accurate | "base" fastest
    whisper_device       "cuda" for GPU (RTX cards) | "cpu" fallback
    whisper_compute_type "float16" for NVIDIA GPU  | "int8" for CPU
    whisper_language     None = auto-detect        | "en" to force English

    Styling
    -------
    font_size            px — 80 small / 100 medium / 120 large
    vertical_position    0.0 = top of frame, 1.0 = bottom (0.80 recommended)
    text_color           RGB tuple — white (255,255,255) is standard
    stroke_color         RGB tuple — black (0,0,0) outline for readability
    stroke_width         outline thickness in px — raise for busy backgrounds
    all_caps             True = ALL CAPS (more energetic)
    """

    # --- Transcription ---
    whisper_model:        str           = "base"
    whisper_device:       str           = "cuda"
    whisper_compute_type: str           = "float16"  # "float16" GPU | "int8" CPU
    whisper_language:     Optional[str] = None       # None = auto-detect

    # --- SRT ---
    max_words_per_segment: int  = 1     # 1 = one word at a time (recommended)
    all_caps:              bool = True

    # --- Visual (FFmpeg burn-in) ---
    font_path:         str   = "fonts/OpenSans_SemiCondensed-Bold.ttf"
    font_size:         int   = 100                   # px
    vertical_position: float = 0.80                  # 0=top 1=bottom
    text_color:        tuple = (255, 255, 255)        # white
    stroke_color:      tuple = (0, 0, 0)             # black outline
    stroke_width:      int   = 6                     # outline px


SUBTITLE_CONFIG = SubtitleConfig()