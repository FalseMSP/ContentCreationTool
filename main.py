"""
main.py – Shorts pipeline entry point.

Usage
-----
    python main.py                         # process all videos, upload, clean up
    python main.py --no-upload             # process only (skip YouTube)
    python main.py --no-subtitles          # skip caption burning
    python main.py --no-delete             # keep source files after upload
    python main.py --input path/to/file    # process a single file
"""

from __future__ import annotations

import argparse
import os
import sys

from config import (
    DEFAULT_DESCRIPTION,
    DEFAULT_TAGS,
    INPUT_DIRECTORY,
    SUBTITLE_CONFIG,
)
from video_processor import output_path_for, process_video, scan_for_videos
from uploader import get_authenticated_service, upload_video


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class ShortsPipeline:
    """
    Orchestrates the full Shorts workflow:
      scan → process → upload → (optionally) clean up
    """

    def __init__(
        self,
        directory: str = INPUT_DIRECTORY,
        upload: bool = True,
        add_subtitles: bool = True,
        delete_after: bool = True,
        audio_path: str | None = None,
    ) -> None:
        self.directory = directory
        self.upload = upload
        self.add_subtitles = add_subtitles
        self.delete_after = delete_after
        self.audio_path = audio_path
        self._yt_service = None  # lazy-loaded

    # ------------------------------------------------------------------
    def run(self, single_file: str | None = None) -> None:
        files = [single_file] if single_file else scan_for_videos(self.directory)

        if not files:
            print("No video files found. Exiting.")
            return

        print(f"Found {len(files)} video(s) to process.")

        processed_pairs: list[tuple[str, str]] = []  # (input, output)

        for src in files:
            dst = output_path_for(src)
            try:
                self._process(src, dst)
                processed_pairs.append((src, dst))
            except Exception as exc:
                print(f"  [pipeline] ERROR processing {src}: {exc}", file=sys.stderr)

        if self.upload:
            service = self._get_yt_service()
            for src, dst in processed_pairs:
                try:
                    self._upload(service, dst, title=_stem(src))
                except Exception as exc:
                    print(f"  [pipeline] ERROR uploading {dst}: {exc}", file=sys.stderr)

        if self.delete_after:
            self._cleanup([src for src, _ in processed_pairs]
                          + [dst for _, dst in processed_pairs])

        print("\n[pipeline] All done.")

    # ------------------------------------------------------------------
    def _process(self, src: str, dst: str) -> None:
        print(f"\n[pipeline] Processing: {os.path.basename(src)}")
        process_video(
            input_path=src,
            output_path=dst,
            audio_path=self.audio_path,
            subtitle_cfg=SUBTITLE_CONFIG if self.add_subtitles else None,
            add_subtitles=self.add_subtitles,
        )

    def _upload(self, service, path: str, title: str) -> None:
        print(f"\n[pipeline] Uploading: {os.path.basename(path)}")
        upload_video(
            service=service,
            file_path=path,
            title=title,
            description=DEFAULT_DESCRIPTION,
            tags=DEFAULT_TAGS,
        )

    def _get_yt_service(self):
        if self._yt_service is None:
            self._yt_service = get_authenticated_service()
        return self._yt_service

    @staticmethod
    def _cleanup(paths: list[str]) -> None:
        print("\n[pipeline] Cleaning up processed files…")
        for p in paths:
            try:
                os.remove(p)
                print(f"  Deleted: {p}")
            except FileNotFoundError:
                pass
            except Exception as exc:
                print(f"  Could not delete {p}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Automated YouTube Shorts pipeline")
    p.add_argument("--input", metavar="FILE", help="Process a single file instead of the whole directory")
    p.add_argument("--no-upload", action="store_true", help="Skip YouTube upload")
    p.add_argument("--no-subtitles", action="store_true", help="Skip subtitle generation")
    p.add_argument("--no-delete", action="store_true", help="Keep source files after processing")
    p.add_argument("--audio", metavar="FILE", help="Path to background music file")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    pipeline = ShortsPipeline(
        upload=not args.no_upload,
        add_subtitles=not args.no_subtitles,
        delete_after=not args.no_delete,
        audio_path=args.audio,
    )
    pipeline.run(single_file=args.input)
