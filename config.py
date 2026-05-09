"""
Central configuration for the Shorts pipeline.
Edit the values here to change behaviour across the entire pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
INPUT_DIRECTORY = r"C:\Users\markp\Videos\Clip_Input"

# ---------------------------------------------------------------------------
# YouTube metadata
# ---------------------------------------------------------------------------
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_CATEGORY_ID = "20"  # Gaming
YOUTUBE_PRIVACY = "unlisted"  # "public" | "unlisted" | "private"

DEFAULT_DESCRIPTION = (
    "Redlife/Bluelife does impressive Omen outplays to get free kills"
)
DEFAULT_TAGS = [
    "Omen Outplay",
    "Flick",
    "Valorant",
    "Valorant Ace",
    "Valorant 5k",
    "Valorant 6k",
]

# ---------------------------------------------------------------------------
# Video processing
# ---------------------------------------------------------------------------
TRIM_FRONT_SECONDS: float = 0.0
TRIM_END_SECONDS: float = 0.0
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
SHORTS_MAX_DURATION = 59  # YouTube Shorts hard limit

# ---------------------------------------------------------------------------
# Subtitle configuration
# ---------------------------------------------------------------------------

@dataclass
class SubtitleConfig:
    """
    Controls how auto-generated captions look and behave.

    Styling tips
    ------------
    - `font_size` 90-120 is the sweet spot for Shorts viewed on phone
    - Keep `max_words_per_segment` at 2-3 for that punchy word-pop style
    - `highlight_color` + `highlight_current_word` mimics MrBeast / CapCut style
    - Raise `stroke_width` if background is busy (gameplay footage = busy)
    """

    # --- Font ---
    font_path: str = "fonts/OpenSans_SemiCondensed-Bold.ttf"   # path to .ttf; must exist
    font_size: int = 100                          # px; 80=small 100=medium 120=large

    # --- Layout ---
    # Vertical position as a fraction of frame height (0=top, 1=bottom)
    vertical_position: float = 0.82              # 0.75-0.88 works well for Shorts
    max_words_per_segment: int = 3               # words shown at once (2-4 recommended)
    all_caps: bool = True                        # ALL CAPS looks more energetic

    # --- Colors (R, G, B) ---
    text_color: tuple = (255, 255, 255)          # white text
    stroke_color: tuple = (0, 0, 0)             # black outline
    stroke_width: int = 6                        # outline thickness in px

    # --- Word-highlight (CapCut-style) ---
    highlight_current_word: bool = True
    highlight_color: tuple = (255, 220, 0)       # yellow highlight

    # --- Background pill ---
    background_enabled: bool = False             # semi-transparent pill behind text
    background_color: tuple = (0, 0, 0)
    background_opacity: int = 140                # 0-255

    # --- Transcription ---
    # "tiny" is fastest, "base"/"small" are more accurate
    whisper_model: str = "large-v3"
    whisper_language: Optional[str] = None       # None = auto-detect; "en" to force English
    whisper_device: str = "cuda"                  # "cpu" or "cuda"
    whisper_compute_type: str = "float16"


SUBTITLE_CONFIG = SubtitleConfig()
