"""
main.py – Shorts pipeline entry point.

Usage
-----
    py main.py                          # process all videos, subtitle, upload, clean up
    py main.py --no-upload              # skip YouTube upload
    py main.py --no-subtitles           # skip subtitle generation entirely
    py main.py --no-interactive         # skip SRT edit pause (auto-burn straight away)
    py main.py --no-delete              # keep source files after processing
    py main.py --input path/to/file.mp4 # process a single file
    py main.py --audio path/to/music.mp3
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback

from config import DEFAULT_DESCRIPTION, DEFAULT_TAGS, INPUT_DIRECTORY, SUBTITLE_CONFIG
from video_processor import output_path_for, process_video, scan_for_videos
from uploader import get_authenticated_service, upload_video


class ShortsPipeline:
    def __init__(
        self,
        directory:    str  = INPUT_DIRECTORY,
        upload:       bool = False,
        add_subtitles: bool = True,
        interactive:  bool = True,
        delete_after: bool = False,
        audio_path:   str | None = None,
    ) -> None:
        self.directory     = directory
        self.upload        = upload
        self.add_subtitles = add_subtitles
        self.interactive   = interactive
        self.delete_after  = delete_after
        self.audio_path    = audio_path
        self._yt_service   = None

    def run(self, single_file: str | None = None) -> None:
        files = [single_file] if single_file else scan_for_videos(self.directory)

        if not files:
            print("No video files found. Exiting.")
            return

        print(f"Found {len(files)} video(s) to process.")
        processed_pairs: list[tuple[str, str]] = []

        for src in files:
            dst = output_path_for(src)
            print(f"\n  [pipeline] Output path will be: {dst}")
            try:
                self._process(src, dst)
                processed_pairs.append((src, dst))
            except Exception:
                print(f"\n  [pipeline] ERROR processing {src}:")
                traceback.print_exc()

        if self.upload:
            service = self._get_yt_service()
            for src, dst in processed_pairs:
                try:
                    self._upload(service, dst, title=_stem(src))
                except Exception:
                    print(f"\n  [pipeline] ERROR uploading {dst}:")
                    traceback.print_exc()

        if self.delete_after:
            self._cleanup([s for s, _ in processed_pairs] + [d for _, d in processed_pairs])

        print("\n[pipeline] All done.")

    def _process(self, src: str, dst: str) -> None:
        print(f"\n[pipeline] Processing: {os.path.basename(src)}")
        process_video(
            input_path    = src,
            output_path   = dst,
            audio_path    = self.audio_path,
            subtitle_cfg  = SUBTITLE_CONFIG if self.add_subtitles else None,
            add_subtitles = self.add_subtitles,
            interactive   = self.interactive,
        )

    def _upload(self, service, path: str, title: str) -> None:
        print(f"\n[pipeline] Uploading: {os.path.basename(path)}")
        upload_video(service, path, title, DEFAULT_DESCRIPTION, DEFAULT_TAGS)

    def _get_yt_service(self):
        if self._yt_service is None:
            self._yt_service = get_authenticated_service()
        return self._yt_service

    @staticmethod
    def _cleanup(paths: list[str]) -> None:
        print("\n[pipeline] Cleaning up…")
        for p in paths:
            try:
                os.remove(p)
                print(f"  Deleted: {p}")
            except FileNotFoundError:
                pass
            except Exception:
                print(f"  Could not delete {p}:")
                traceback.print_exc()


def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Automated YouTube Shorts pipeline")
    p.add_argument("--input",        metavar="FILE", help="Process a single file")
    p.add_argument("--upload",       action="store_true", help="Upload to YouTube (default: off)")
    p.add_argument("--no-subtitles", action="store_true", help="Skip subtitle generation")
    p.add_argument("--delete",       action="store_true", help="Delete source files after processing (default: off)")
    p.add_argument("--audio",        metavar="FILE", help="Background music file")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    ShortsPipeline(
        upload        = args.upload,
        add_subtitles = not args.no_subtitles,
        interactive   = False,
        delete_after  = args.delete,
        audio_path    = args.audio,
    ).run(single_file=args.input)