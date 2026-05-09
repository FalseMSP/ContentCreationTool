"""
subtitler.py – Transcribe video audio with faster-whisper, then burn in
Open Sans captions using Pillow.  Styling mimics viral Shorts creators:
large bold text, word-level timing, yellow highlight on the current word,
heavy black stroke, centred near the bottom of the frame.
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, VideoClip

from config import SubtitleConfig


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Segment:
    """A short burst of words shown simultaneously on screen."""
    words: List[Word]

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end

    def text_at(self, t: float) -> Tuple[List[str], int]:
        """
        Returns (word_texts, highlighted_index) at time *t*.
        highlighted_index is -1 when no word is active.
        """
        texts = [w.text for w in self.words]
        hi = -1
        for i, w in enumerate(self.words):
            if w.start <= t <= w.end:
                hi = i
                break
        return texts, hi


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def transcribe(video_path: str, cfg: SubtitleConfig) -> List[Word]:
    """
    Use faster-whisper to extract word-level timestamps from the video.
    Returns a flat list of Word objects.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper is required for subtitles.\n"
            "Install it with:  pip install faster-whisper"
        )

    print(f"  [subtitler] Loading Whisper model '{cfg.whisper_model}' on {cfg.whisper_device}…")
    model = WhisperModel(cfg.whisper_model, device=cfg.whisper_device, compute_type=cfg.whisper_compute_type)
    
    segments_iter, _ = model.transcribe(
        video_path,
        language=cfg.whisper_language,
        word_timestamps=True,
    )

    words: List[Word] = []
    for seg in segments_iter:
        if seg.words:
            for w in seg.words:
                words.append(Word(text=w.word.strip(), start=w.start, end=w.end))

    print(f"  [subtitler] Transcribed {len(words)} words.")
    return words


# ---------------------------------------------------------------------------
# Segment builder
# ---------------------------------------------------------------------------

def build_segments(words: List[Word], max_per_segment: int) -> List[Segment]:
    """
    Group words into short bursts of *max_per_segment* words each.
    Words with no timestamp gap >0.8 s are kept together.
    """
    segments: List[Segment] = []
    buf: List[Word] = []

    for w in words:
        if not w.text:
            continue
        if buf and (len(buf) >= max_per_segment or w.start - buf[-1].end > 0.8):
            segments.append(Segment(buf))
            buf = []
        buf.append(w)

    if buf:
        segments.append(Segment(buf))

    return segments


# ---------------------------------------------------------------------------
# Frame renderer
# ---------------------------------------------------------------------------

class SubtitleRenderer:
    """Renders caption frames as numpy arrays for MoviePy."""

    def __init__(self, cfg: SubtitleConfig, frame_size: Tuple[int, int]):
        self.cfg = cfg
        self.w, self.h = frame_size          # (width, height) in pixels
        self._load_font()

    # ------------------------------------------------------------------
    def _load_font(self) -> None:
        cfg = self.cfg
        if not os.path.isfile(cfg.font_path):
            raise FileNotFoundError(
                f"Font not found: {cfg.font_path}\n"
                "Download Open Sans Bold from fonts.google.com and place it at that path."
            )
        self.font = ImageFont.truetype(cfg.font_path, cfg.font_size)

    # ------------------------------------------------------------------
    def _word_widths(self, words: List[str]) -> List[int]:
        """Measure pixel width of each word (including trailing space)."""
        tmp = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(tmp)
        widths = []
        for word in words:
            bb = draw.textbbox((0, 0), word + " ", font=self.font)
            widths.append(bb[2] - bb[0])
        return widths

    # ------------------------------------------------------------------
    def render_frame(
        self,
        words: List[str],
        highlighted: int,
        frame_array: np.ndarray,
    ) -> np.ndarray:
        """
        Composites subtitle text onto *frame_array* (H×W×3 uint8).
        Returns a new H×W×3 array.
        """
        cfg = self.cfg
        img = Image.fromarray(frame_array).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        display_words = [w.upper() if cfg.all_caps else w for w in words]
        word_widths = self._word_widths(display_words)
        total_width = sum(word_widths)

        # --- Background pill ---
        if cfg.background_enabled:
            padding = 20
            pill_x0 = self.w // 2 - total_width // 2 - padding
            pill_y0 = int(self.h * cfg.vertical_position) - cfg.font_size // 2 - padding
            pill_x1 = self.w // 2 + total_width // 2 + padding
            pill_y1 = int(self.h * cfg.vertical_position) + cfg.font_size // 2 + padding
            bg_color = (*cfg.background_color, cfg.background_opacity)
            draw.rounded_rectangle([pill_x0, pill_y0, pill_x1, pill_y1], radius=20, fill=bg_color)

        # --- Draw each word ---
        cursor_x = self.w // 2 - total_width // 2
        y = int(self.h * cfg.vertical_position) - cfg.font_size // 2

        for i, (word, ww) in enumerate(zip(display_words, word_widths)):
            color = cfg.highlight_color if (cfg.highlight_current_word and i == highlighted) else cfg.text_color

            # Stroke (drawn first, slightly offset in 8 directions)
            for dx in range(-cfg.stroke_width, cfg.stroke_width + 1, max(1, cfg.stroke_width // 2)):
                for dy in range(-cfg.stroke_width, cfg.stroke_width + 1, max(1, cfg.stroke_width // 2)):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text(
                        (cursor_x + dx, y + dy),
                        word,
                        font=self.font,
                        fill=(*cfg.stroke_color, 255),
                    )

            # Main text
            draw.text((cursor_x, y), word, font=self.font, fill=(*color, 255))
            cursor_x += ww

        # Composite
        result = Image.alpha_composite(img, overlay).convert("RGB")
        return np.array(result)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_subtitles(video: VideoFileClip, cfg: SubtitleConfig) -> VideoFileClip:
    """
    Transcribe *video*, build word-timed segments, and return a new
    VideoFileClip with captions burned in.
    """
    # Write audio to a temp file for Whisper
    import tempfile, uuid
    tmp_audio = os.path.join(tempfile.gettempdir(), f"shorts_audio_{uuid.uuid4().hex}.wav")
    try:
        video.audio.write_audiofile(tmp_audio, logger=None)
        words = transcribe(tmp_audio, cfg)
    finally:
        if os.path.exists(tmp_audio):
            os.remove(tmp_audio)

    segments = build_segments(words, cfg.max_words_per_segment)
    renderer = SubtitleRenderer(cfg, (video.w, video.h))

    # Build a lookup: for any time t, which segment is active?
    def get_active_segment(t: float) -> Optional[Segment]:
        for seg in segments:
            if seg.start <= t <= seg.end:
                return seg
        return None

    # Wrap make_frame to composite subtitles
    original_make_frame = video.get_frame

    def make_frame_with_subs(t: float) -> np.ndarray:
        frame = original_make_frame(t)
        seg = get_active_segment(t)
        if seg is None:
            return frame
        word_texts, hi = seg.text_at(t)
        return renderer.render_frame(word_texts, hi, frame)

    from moviepy import VideoClip
    result = VideoClip(make_frame_with_subs, duration=video.duration)
    result = result.with_audio(video.audio)
    result = result.with_fps(video.fps)
    return result