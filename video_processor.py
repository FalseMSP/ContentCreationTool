"""
video_processor.py – Crop, trim, resize to Shorts format using FFmpeg directly
(no MoviePy re-encode), then hand off to subtitler for transcription + burn-in.

Using FFmpeg for the initial processing avoids the large RAM/VRAM spike that
MoviePy causes, which was silently killing the process after transcription.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sys
import tempfile
import uuid
from typing import Optional

from config import (
    OUTPUT_HEIGHT,
    OUTPUT_WIDTH,
    SHORTS_MAX_DURATION,
    SUBTITLE_CONFIG,
    TRIM_END_SECONDS,
    TRIM_FRONT_SECONDS,
    SubtitleConfig,
)


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError(
            "ffmpeg not found on PATH.\n"
            "Download from https://ffmpeg.org/download.html and add to PATH."
        )
    return path


def _require_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if not path:
        raise RuntimeError(
            "ffprobe not found on PATH.\n"
            "It ships with ffmpeg — make sure the ffmpeg bin folder is on PATH."
        )
    return path


def _get_duration(input_path: str) -> float:
    result = subprocess.run(
        [
            _require_ffprobe(),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{result.stderr}")
    return float(result.stdout.strip())


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
    _require_ffmpeg()

    print(f"  [processor] Probing: {input_path}")
    duration = _get_duration(input_path)

    if duration > SHORTS_MAX_DURATION + trim_front + trim_end:
        trim_front = duration - trim_end - SHORTS_MAX_DURATION
        print(f"  [processor] Auto-adjusted trim_front to {trim_front:.1f}s")

    start_time = trim_front
    end_time   = duration - trim_end
    clip_dur   = end_time - start_time

    if clip_dur <= 0:
        raise ValueError(
            f"clip duration {clip_dur:.2f}s <= 0. "
            "Check TRIM_FRONT_SECONDS / TRIM_END_SECONDS in config.py."
        )

    print(f"  [processor] Trimming: {start_time:.1f}s -> {end_time:.1f}s ({clip_dur:.1f}s clip)")

    crop_filter = (
        "crop="
        "if(gt(iw/ih\\,9/16)\\,ih*9/16\\,iw):"
        "if(gt(iw/ih\\,9/16)\\,ih\\,iw*16/9):"
        "if(gt(iw/ih\\,9/16)\\,(iw-ih*9/16)/2\\,0):"
        "if(gt(iw/ih\\,9/16)\\,0\\,(ih-iw*16/9)/2)"
    )
    scale_filter = f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}"
    vf = f"{crop_filter},{scale_filter}"

    tmp_video = os.path.join(
        tempfile.gettempdir(), f"shorts_nosubs_{uuid.uuid4().hex}.mp4"
    )

    try:
        cmd = [
            _require_ffmpeg(), "-y",
            "-ss", str(start_time),
            "-i",  input_path,
            "-t",  str(clip_dur),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            tmp_video,
        ]

        print(f"  [processor] FFmpeg crop+scale (one pass)...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("  [processor] FFmpeg stderr:")
            print(result.stderr[-3000:])
            raise RuntimeError("FFmpeg crop/scale step failed.")

        print(f"  [processor] Intermediate video ready.")

        if add_subtitles and subtitle_cfg is not None:
            srt_path = os.path.splitext(output_path)[0] + ".srt"

            font_abs = os.path.abspath(subtitle_cfg.font_path)
            if not os.path.isfile(font_abs):
                raise FileNotFoundError(
                    f"Font not found: {font_abs}\n"
                    "Download OpenSans_SemiCondensed-Bold.ttf from fonts.google.com\n"
                    "and place it at fonts/OpenSans_SemiCondensed-Bold.ttf"
                )

            tmp_audio = os.path.join(
                tempfile.gettempdir(), f"shorts_audio_{uuid.uuid4().hex}.wav"
            )
            try:
                print(f"  [processor] Extracting audio for transcription...")
                audio_cmd = [
                    _require_ffmpeg(), "-y",
                    "-i", tmp_video,
                    "-vn",
                    "-acodec", "pcm_s16le",
                    "-ar", "16000",
                    "-ac", "1",
                    tmp_audio,
                ]
                audio_result = subprocess.run(audio_cmd, capture_output=True, text=True)
                if audio_result.returncode != 0:
                    raise RuntimeError(f"Audio extraction failed:\n{audio_result.stderr[-1000:]}")

                # Run Whisper in a separate subprocess so VRAM is fully
                # released when it exits before the rest of the pipeline runs.
                worker = os.path.join(os.path.dirname(__file__), "transcribe_worker.py")
                worker_cmd = [
                    sys.executable, worker,
                    tmp_audio,
                    srt_path,
                    subtitle_cfg.whisper_model,
                    subtitle_cfg.whisper_device,
                    subtitle_cfg.whisper_compute_type,
                ]
                if subtitle_cfg.whisper_language:
                    worker_cmd.append(subtitle_cfg.whisper_language)

                print(f"  [processor] Transcribing in subprocess (VRAM will free on exit)...")
                worker_result = subprocess.run(worker_cmd, text=True)
                if worker_result.returncode != 0:
                    raise RuntimeError("Transcription worker failed.")

            finally:
                if os.path.exists(tmp_audio):
                    os.remove(tmp_audio)

            if not os.path.exists(srt_path):
                raise RuntimeError(f"SRT not produced by worker: {srt_path}")
            print(f"  [processor] SRT saved -> {srt_path}")

            # Burn-in disabled — copy clean video and export SRT only
            shutil.copy2(tmp_video, output_path)
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / 1_048_576
                print(f"  [processor] Video saved -> {output_path} ({size_mb:.1f} MB)")
            else:
                raise RuntimeError(f"File copy failed: {output_path}")

        else:
            shutil.copy2(tmp_video, output_path)
            print(f"  [processor] Done -> {output_path}")

    finally:
        if os.path.exists(tmp_video):
            try:
                os.remove(tmp_video)
            except Exception:
                pass

    print(f"  [processor] All steps complete.")


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