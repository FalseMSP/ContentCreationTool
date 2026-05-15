"""
transcribe_worker.py – Run as a subprocess.
Loads Whisper, transcribes, writes SRT, then exits (freeing all VRAM).

Usage:
    python transcribe_worker.py <audio_path> <srt_path> <model> <device> <compute_type> [language]
"""

import sys
import os

def _fmt_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h  = ms // 3_600_000; ms %= 3_600_000
    m  = ms // 60_000;    ms %= 60_000
    s  = ms // 1_000;     ms %= 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    if len(sys.argv) < 6:
        print("Usage: transcribe_worker.py <audio> <srt> <model> <device> <compute_type> [language]")
        sys.exit(1)

    audio_path   = sys.argv[1]
    srt_path     = sys.argv[2]
    model_name   = sys.argv[3]
    device       = sys.argv[4]
    compute_type = sys.argv[5]
    language     = sys.argv[6] if len(sys.argv) > 6 else None

    print(f"  [worker] Loading Whisper '{model_name}' on {device}…", flush=True)

    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    segments_iter, _ = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
    )

    captions = []
    idx = 1
    for seg in segments_iter:
        if not seg.words:
            continue
        for w in seg.words:
            text = w.word.strip().upper()
            if not text:
                continue
            captions.append((idx, w.start, w.end, text))
            idx += 1

    print(f"  [worker] Transcribed {len(captions)} words.", flush=True)

    # Write SRT
    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, start, end, text in captions:
            f.write(f"{idx}\n")
            f.write(f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}\n")
            f.write(text + "\n\n")

    print(f"  [worker] SRT written -> {srt_path}", flush=True)
    # Process exits here — VRAM is fully released


if __name__ == "__main__":
    main()