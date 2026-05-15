"""
subtitler.py

Pipeline:
  1. Transcribe audio with faster-whisper (word-level timestamps)
  2. Write SRT — pause and let the user edit it in their text editor
  3. Re-read the (possibly edited) SRT
  4. Burn captions into the video via FFmpeg drawtext — one word at a time,
     with a scale-bounce pop animation, Open Sans Bold, heavy stroke outline
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from typing import List, Optional

from config import SubtitleConfig


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Caption:
    index: int
    start: float   # seconds
    end: float     # seconds
    text: str


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def transcribe(audio_path: str, cfg: SubtitleConfig) -> List[Caption]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError("py -m pip install faster-whisper")

    print(f"  [subtitler] Loading Whisper '{cfg.whisper_model}' on {cfg.whisper_device}…")
    model = WhisperModel(
        cfg.whisper_model,
        device=cfg.whisper_device,
        compute_type=cfg.whisper_compute_type,
    )

    segments_iter, _ = model.transcribe(
        audio_path,
        language=cfg.whisper_language,
        word_timestamps=True,
    )

    captions: List[Caption] = []
    idx = 1
    for seg in segments_iter:
        if not seg.words:
            continue
        for w in seg.words:
            text = w.word.strip()
            if not text:
                continue
            captions.append(Caption(
                index=idx,
                start=w.start,
                end=w.end,
                text=text.upper() if cfg.all_caps else text,
            ))
            idx += 1

    print(f"  [subtitler] Transcribed {len(captions)} words.")

    # Explicitly free the model from VRAM before returning.
    # large-v3 holds ~3 GB of VRAM; without this, FFmpeg can crash
    # the process due to out-of-memory on the GPU/system.
    try:
        del model
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("  [subtitler] VRAM freed.")
    except Exception:
        pass  # non-CUDA or torch not installed — safe to ignore

    return captions


# ---------------------------------------------------------------------------
# SRT read / write
# ---------------------------------------------------------------------------

def _fmt_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h  = ms // 3_600_000; ms %= 3_600_000
    m  = ms // 60_000;    ms %= 60_000
    s  = ms // 1_000;     ms %= 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _parse_srt_time(t: str) -> float:
    t = t.replace(",", ".")
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def write_srt(captions: List[Caption], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for cap in captions:
            f.write(f"{cap.index}\n")
            f.write(f"{_fmt_srt_time(cap.start)} --> {_fmt_srt_time(cap.end)}\n")
            f.write(cap.text + "\n\n")


def read_srt(path: str) -> List[Caption]:
    """Parse an SRT file back into Caption objects."""
    text = open(path, encoding="utf-8").read()
    blocks = [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]
    captions = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0])
        except ValueError:
            continue
        start_s, end_s = lines[1].split(" --> ")
        caption_text = " ".join(lines[2:]).strip()
        captions.append(Caption(
            index=idx,
            start=_parse_srt_time(start_s.strip()),
            end=_parse_srt_time(end_s.strip()),
            text=caption_text,
        ))
    return captions


# ---------------------------------------------------------------------------
# Interactive SRT edit pause
# ---------------------------------------------------------------------------

def prompt_edit_srt(srt_path: str) -> None:
    """
    Open the SRT in the user's default text editor and wait for them
    to confirm before continuing the burn-in step.
    """
    print()
    print("=" * 60)
    print("  SUBTITLE REVIEW")
    print("=" * 60)
    print(f"  SRT file: {srt_path}")
    print()
    print("  Opening in your default text editor…")
    print("  Edit any mistranscribed words, save the file, then")
    print("  come back here and press ENTER to continue.")
    print("=" * 60)

    # Open in default system editor (works on Windows, mac, Linux)
    try:
        if sys.platform == "win32":
            os.startfile(srt_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", srt_path])
        else:
            subprocess.Popen(["xdg-open", srt_path])
    except Exception as e:
        print(f"  (Could not auto-open editor: {e})")
        print(f"  Please open manually: {srt_path}")

    input("\n  Press ENTER when you're done editing… ")
    print()


# ---------------------------------------------------------------------------
# FFmpeg burn-in
# ---------------------------------------------------------------------------

def _escape_ffmpeg(text: str) -> str:
    """Escape text for FFmpeg drawtext.

    text= is wrapped in single quotes in the filter chain, so any
    apostrophe breaks parsing and must be stripped entirely.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace("\u2019", "")  # right curly apostrophe
    text = text.replace("\u2018", "")  # left curly apostrophe
    text = text.replace("'", "")        # straight apostrophe
    text = text.replace(":", "\\:")
    text = text.replace("%", "\\%")
    return text


def burn_subtitles_ffmpeg(
    input_video: str,
    output_video: str,
    captions: List[Caption],
    cfg: SubtitleConfig,
) -> None:
    """
    Burn captions into video using FFmpeg drawtext filters.
    One word per filter entry with a scale-bounce pop animation.

    Animation:
      - Word scales from 1.15x → 1.0x over the first 6 frames (pop-in)
      - Full opacity for the duration
      - Disappears on the next word's start
    """
    if not captions:
        print("  [subtitler] No captions to burn in, copying video as-is.")
        import shutil
        shutil.copy2(input_video, output_video)
        return

    font_path = os.path.abspath(cfg.font_path)
    if not os.path.isfile(font_path):
        raise FileNotFoundError(
            f"Font not found: {font_path}\n"
            "Download OpenSans-Bold.ttf from fonts.google.com → fonts/OpenSans-Bold.ttf"
        )

    # FFmpeg on Windows needs forward slashes and escaped colons in paths
    font_path_ffmpeg = font_path.replace("\\", "/").replace(":", "\\:")

    # Vertical position in pixels  (cfg.vertical_position is 0-1 fraction)
    # We use FFmpeg expressions so it works for any resolution
    y_expr = f"(h*{cfg.vertical_position:.4f})-(text_h/2)"

    filters = []
    fps_approx = 60  # used only for bounce frame count — close enough

    for cap in captions:
        text = _escape_ffmpeg(cap.text)
        s = cap.start
        e = cap.end
        bounce_dur = min(6 / fps_approx, (e - s) * 0.4)  # pop-in over first ~6 frames

        # Scale expression: interpolates from 1.15 to 1.0 during bounce_dur,
        # then holds at 1.0.  FFmpeg drawtext doesn't support true scale, so
        # we achieve the pop by animating fontsize.
        base_size = cfg.font_size
        big_size  = int(base_size * 1.18)

        # fontsize lerp: big_size → base_size over bounce_dur seconds
        # after bounce_dur: stays at base_size
        size_expr = (
            f"if(lt(t-{s:.4f},{bounce_dur:.4f}),"
            f"{big_size}+({base_size}-{big_size})*((t-{s:.4f})/{bounce_dur:.4f}),"
            f"{base_size})"
        )

        # x centred accounting for variable font size — approximate with base
        x_expr = "(w-text_w)/2"

        # Build one drawtext filter per word
        # Stroke is simulated with borderw / bordercolor
        f = (
            f"drawtext="
            f"fontfile='{font_path_ffmpeg}':"
            f"text='{text}':"
            f"fontsize={size_expr}:"
            f"fontcolor={_rgb_to_hex(cfg.text_color)}:"
            f"borderw={cfg.stroke_width}:"
            f"bordercolor={_rgb_to_hex(cfg.stroke_color)}:"
            f"x={x_expr}:"
            f"y={y_expr}:"
            f"enable='between(t,{s:.4f},{e:.4f})'"
        )
        filters.append(f)

    filter_chain = ",".join(filters)

    # Normalise to forward slashes for FFmpeg on Windows
    input_ffmpeg  = input_video.replace("\\", "/")
    output_ffmpeg = output_video.replace("\\", "/")

    # Write filter chain to a temp file to avoid Windows CLI length limits
    # and any shell quoting issues with the output path.
    tmp_filter_path = None
    try:
        tmp_filter_fd, tmp_filter_path = tempfile.mkstemp(
            suffix=".txt", prefix="shorts_filter_"
        )
        with os.fdopen(tmp_filter_fd, "w", encoding="utf-8") as fh:
            fh.write(filter_chain)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_ffmpeg,
            "-filter_script:v", tmp_filter_path,
            "-codec:a", "copy",
            output_ffmpeg,
        ]

        print(f"  [subtitler] Burning {len(captions)} captions with FFmpeg\u2026")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("  [subtitler] FFmpeg error:")
            print(result.stderr[-2000:])
            raise RuntimeError("FFmpeg burn-in failed. See error above.")
    finally:
        if tmp_filter_path and os.path.exists(tmp_filter_path):
            try:
                os.remove(tmp_filter_path)
            except Exception:
                pass

    print(f"  [subtitler] Burn-in complete \u2192 {output_video}")


def _rgb_to_hex(rgb: tuple) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_subtitles(
    video_path: str,
    output_path: str,
    srt_path: str,
    cfg: SubtitleConfig,
    interactive: bool = True,
) -> None:
    """
    Full subtitle pipeline:
      1. Extract audio → transcribe → write SRT
      2. (If interactive) open SRT for user to edit, wait for ENTER
      3. Re-read SRT (picks up any edits)
      4. Burn captions into video via FFmpeg
    """
    # Step 1: transcribe
    tmp_audio = os.path.join(tempfile.gettempdir(), f"shorts_audio_{uuid.uuid4().hex}.wav")
    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(tmp_audio, logger=None)
        clip.close()
        captions = transcribe(tmp_audio, cfg)
    finally:
        if os.path.exists(tmp_audio):
            os.remove(tmp_audio)

    write_srt(captions, srt_path)

    # Step 2: let user edit
    if interactive:
        prompt_edit_srt(srt_path)

    # Step 3: re-read (captures edits)
    captions = read_srt(srt_path)

    # Step 4: burn in
    burn_subtitles_ffmpeg(video_path, output_path, captions, cfg)