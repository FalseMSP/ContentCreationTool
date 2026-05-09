"""
video_processor.py – Crop, trim, resize, and optionally add background
audio to a video clip, producing a Shorts-ready 9:16 MP4.
"""

from __future__ import annotations

import os
from typing import Optional

from moviepy import AudioFileClip, VideoFileClip

from config import (
    OUTPUT_HEIGHT,
    OUTPUT_WIDTH,
    SHORTS_MAX_DURATION,
    SUBTITLE_CONFIG,
    TRIM_END_SECONDS,
    TRIM_FRONT_SECONDS,
    SubtitleConfig,
)


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_video(
    input_path: str,
    output_path: str,
    trim_front: float = TRIM_FRONT_SECONDS,
    trim_end: float = TRIM_END_SECONDS,
    audio_path: Optional[str] = None,
    subtitle_cfg: Optional[SubtitleConfig] = SUBTITLE_CONFIG,
    add_subtitles: bool = True,
) -> None:
    """
    Full Shorts pipeline for a single file:
      1. Load
      2. Auto-trim to ≤59 s if needed
      3. Crop to 9:16
      4. Resize to 1080×1920
      5. (Optional) Replace / layer background audio
      6. (Optional) Burn in subtitles
      7. Export
    """
    print(f"  [processor] Loading: {input_path}")
    video = VideoFileClip(input_path)

    # --- Step 2: ensure ≤59 s ---
    duration = video.duration
    max_duration = SHORTS_MAX_DURATION

    if duration > max_duration + trim_front + trim_end:
        trim_front = duration - trim_end - max_duration
        print(f"  [processor] Auto-adjusted trim_front to {trim_front:.1f}s to stay under {max_duration}s")

    start_time = trim_front
    end_time = duration - trim_end

    if end_time <= start_time:
        raise ValueError(
            f"Computed end_time ({end_time:.2f}s) ≤ start_time ({start_time:.2f}s). "
            "Check TRIM_FRONT_SECONDS / TRIM_END_SECONDS."
        )

    trimmed = video.subclipped(start_time, end_time)

    # --- Step 3: crop to 9:16 ---
    cropped = _crop_to_9_16(trimmed)

    # --- Step 4: resize ---
    scaled = cropped.resized((OUTPUT_WIDTH, OUTPUT_HEIGHT))

    # --- Step 5: background audio ---
    if audio_path:
        bg = AudioFileClip(audio_path).multiply_volume(0.3).with_duration(scaled.duration)
        scaled = scaled.with_audio(bg)

    # --- Step 6: subtitles ---
    final = scaled
    if add_subtitles and subtitle_cfg is not None:
        print("  [processor] Generating subtitles…")
        from subtitler import add_subtitles as burn_subtitles
        final = burn_subtitles(scaled, subtitle_cfg)

    # --- Step 7: export ---
    print(f"  [processor] Writing: {output_path}")
    final.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)

    # Clean up
    for clip in [video, trimmed, cropped, scaled, final]:
        try:
            clip.close()
        except Exception:
            pass

    print(f"  [processor] Done → {output_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _crop_to_9_16(video: VideoFileClip) -> VideoFileClip:
    """Centre-crop *video* to 9:16 aspect ratio."""
    target_ratio = 9 / 16
    w, h = video.size

    if w / h > target_ratio:
        # Too wide — crop sides
        new_w = int(h * target_ratio)
        x1 = (w - new_w) // 2
        return video.cropped(x1=x1, x2=x1 + new_w, y1=0, y2=h)
    else:
        # Too tall — crop top/bottom
        new_h = int(w / target_ratio)
        y1 = (h - new_h) // 2
        return video.cropped(x1=0, x2=w, y1=y1, y2=y1 + new_h)


def output_path_for(input_path: str) -> str:
    """Derive the output path from an input path (same dir, _short suffix)."""
    directory = os.path.dirname(input_path)
    stem, _ = os.path.splitext(os.path.basename(input_path))
    return os.path.join(directory, f"{stem}_short.mp4")


def scan_for_videos(directory: str) -> list[str]:
    """Recursively find all video files in *directory*."""
    extensions = {".mp4", ".mkv", ".avi", ".mov", ".wmv"}
    found = []
    for root, _, files in os.walk(directory):
        for name in files:
            if os.path.splitext(name)[1].lower() in extensions:
                found.append(os.path.join(root, name))
    return found