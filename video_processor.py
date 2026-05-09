"""
video_processor.py – Crop, trim, resize to Shorts format, then hand off
to subtitler for transcription, review, and FFmpeg burn-in.
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


def process_video(
    input_path: str,
    output_path: str,
    trim_front: float = TRIM_FRONT_SECONDS,
    trim_end: float = TRIM_END_SECONDS,
    audio_path: Optional[str] = None,
    subtitle_cfg: Optional[SubtitleConfig] = SUBTITLE_CONFIG,
    add_subtitles: bool = True,
    interactive: bool = True,
) -> None:
    """
    1. Load & validate
    2. Auto-trim to <= 59 s
    3. Crop to 9:16
    4. Resize to 1080x1920
    5. (Optional) Layer background audio
    6. Export cropped/resized video to a temp file
    7. (Optional) Transcribe → edit SRT → FFmpeg burn-in → final output
       Otherwise just move the temp file to output_path
    """
    print(f"  [processor] Loading: {input_path}")
    video = VideoFileClip(input_path)

    # --- auto-trim ---
    duration = video.duration
    if duration > SHORTS_MAX_DURATION + trim_front + trim_end:
        trim_front = duration - trim_end - SHORTS_MAX_DURATION
        print(f"  [processor] Auto-adjusted trim_front to {trim_front:.1f}s")

    start_time = trim_front
    end_time   = duration - trim_end
    if end_time <= start_time:
        raise ValueError(
            f"end_time ({end_time:.2f}s) <= start_time ({start_time:.2f}s). "
            "Check TRIM_FRONT_SECONDS / TRIM_END_SECONDS in config.py."
        )

    trimmed = video.subclipped(start_time, end_time)
    cropped = _crop_to_9_16(trimmed)
    scaled  = cropped.resized((OUTPUT_WIDTH, OUTPUT_HEIGHT))

    if audio_path:
        bg     = AudioFileClip(audio_path).multiply_volume(0.3).with_duration(scaled.duration)
        scaled = scaled.with_audio(bg)

    # Transcribe and write SRT for use in DaVinci Resolve
    if add_subtitles and subtitle_cfg is not None:
        srt_path = os.path.splitext(output_path)[0] + ".srt"
        from subtitler import transcribe, write_srt
        import tempfile, uuid
        from moviepy import VideoFileClip as _VFC
        tmp_audio = os.path.join(tempfile.gettempdir(), f"shorts_audio_{uuid.uuid4().hex}.wav")
        try:
            scaled.audio.write_audiofile(tmp_audio, logger=None)
            captions = transcribe(tmp_audio, subtitle_cfg)
        finally:
            if os.path.exists(tmp_audio):
                os.remove(tmp_audio)
        write_srt(captions, srt_path)
        print(f"  [processor] SRT saved → {srt_path}")

    # Export video (no burn-in)
    print(f"  [processor] Writing: {output_path}")
    scaled.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
    _close_clips(video, trimmed, cropped, scaled)

    print(f"  [processor] Done → {output_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _crop_to_9_16(video: VideoFileClip) -> VideoFileClip:
    target_ratio = 9 / 16
    w, h = video.size
    if w / h > target_ratio:
        new_w = int(h * target_ratio)
        x1 = (w - new_w) // 2
        return video.cropped(x1=x1, x2=x1 + new_w, y1=0, y2=h)
    else:
        new_h = int(w / target_ratio)
        y1 = (h - new_h) // 2
        return video.cropped(x1=0, x2=w, y1=y1, y2=y1 + new_h)


def _close_clips(*clips) -> None:
    for c in clips:
        try:
            c.close()
        except Exception:
            pass


def output_path_for(input_path: str) -> str:
    directory = os.path.dirname(input_path)
    stem, _   = os.path.splitext(os.path.basename(input_path))
    return os.path.join(directory, f"{stem}_short.mp4")


def scan_for_videos(directory: str) -> list[str]:
    extensions = {".mp4", ".mkv", ".avi", ".mov", ".wmv"}
    found = []
    for root, _, files in os.walk(directory):
        for name in files:
            if os.path.splitext(name)[1].lower() in extensions:
                if not name.endswith("_short.mp4"):
                    found.append(os.path.join(root, name))
    return found