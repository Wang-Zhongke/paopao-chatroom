#!/usr/bin/env python3
"""Checkpointed OCR fallback for Bilibili videos with no public AI track."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import datetime as dt
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from bili_video_download import download, resolve_stream
from ocr_caption_clean import write_outputs


def save_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    videos = manifest.get("videos", [])
    if not videos:
        return
    fields: list[str] = []
    for video in videos:
        for key in video:
            if key not in fields:
                fields.append(key)
    with path.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(videos)


def compile_ocr(source: Path, binary: Path) -> None:
    binary.parent.mkdir(parents=True, exist_ok=True)
    module_cache = Path(tempfile.gettempdir()) / "paopao-clang-module-cache"
    command = [
        "clang", "-fobjc-arc",
        "-framework", "Foundation",
        "-framework", "AVFoundation",
        "-framework", "Vision",
        "-framework", "CoreGraphics",
        "-framework", "CoreMedia",
        str(source), "-o", str(binary),
    ]
    env = {**os.environ, "CLANG_MODULE_CACHE_PATH": str(module_cache)}
    subprocess.run(command, check=True, env=env)


def process_video(video: dict, args: argparse.Namespace, ocr_binary: Path) -> dict:
    bvid = video["bvid"]
    stream = resolve_stream(bvid, args.quality)
    cache_dir = args.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    video_path = cache_dir / f"{bvid}.mp4"
    raw_dir = args.output_dir / "transcripts" / "ocr-raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{bvid}.jsonl"

    downloaded = download(stream, video_path)
    command = [
        str(ocr_binary), str(video_path), str(raw_path),
        "--step", str(args.step),
        "--crop-top", str(args.crop_top),
        "--crop-bottom", str(args.crop_bottom),
    ]
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    clean = write_outputs(raw_path, args.output_dir, video, args.step)
    if not args.keep_video:
        video_path.unlink(missing_ok=True)
    return {
        "bvid": bvid,
        "status": "downloaded-ocr" if clean["segments"] else "ocr-empty",
        "video_bytes": downloaded,
        "quality_returned": stream["quality_returned"],
        "ocr_stdout": completed.stdout.strip(),
        **clean,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=Path(tempfile.gettempdir()) / "paopao-video-cache")
    parser.add_argument("--ocr-source", type=Path, default=Path(__file__).with_name("burned_caption_ocr.m"))
    parser.add_argument("--ocr-binary", type=Path, default=Path(tempfile.gettempdir()) / "paopao-burned-caption-ocr")
    parser.add_argument("--bvid", nargs="*")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--step", type=float, default=0.8)
    parser.add_argument("--crop-top", type=float, default=0.50)
    parser.add_argument("--crop-bottom", type=float, default=0.96)
    parser.add_argument("--quality", type=int, default=32)
    parser.add_argument("--keep-video", action="store_true")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument(
        "--force", action="store_true",
        help="reprocess explicitly listed --bvid items even when already completed",
    )
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    if not args.ocr_binary.exists() or args.ocr_binary.stat().st_mtime < args.ocr_source.stat().st_mtime:
        compile_ocr(args.ocr_source, args.ocr_binary)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    requested = set(args.bvid or [])
    candidates = []
    for video in manifest["videos"]:
        if requested and video["bvid"] not in requested:
            continue
        status = video.get("transcript_status", "pending")
        if (
            status == "needs-ocr-asr"
            or (status in {"ocr-error", "ocr-empty", "ocr-partial"} and args.retry_errors)
            or (args.force and requested)
        ):
            candidates.append(video)
    if args.limit is not None:
        candidates = candidates[:args.limit]

    summary = {
        "started_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        "selected": len(candidates), "downloaded_ocr": 0, "errors": 0,
        "video_bytes": 0, "segments": 0,
    }
    if args.workers < 1 or args.workers > 4:
        raise SystemExit("--workers must be between 1 and 4")

    def guarded(video: dict) -> tuple[dict, dict]:
        try:
            result = process_video(video, args, args.ocr_binary)
        except Exception as exc:
            result = {"bvid": video["bvid"], "status": "ocr-error", "error": repr(exc)}
        return video, result

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)
    try:
        futures = [executor.submit(guarded, video) for video in candidates]
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            video, result = future.result()

            video["processed_at"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
            if result["status"] == "downloaded-ocr":
                video["transcript_status"] = "downloaded-ocr"
                video["transcript_method"] = "burned-in-caption-ocr"
                video["transcript_segments"] = result["segments"]
                video["ocr_mean_confidence"] = round(result["mean_confidence"], 4)
                video["ocr_caption_band_y"] = round(result["caption_band_y"], 3)
                video["ocr_sample_step_seconds"] = args.step
                video["download_quality"] = result["quality_returned"]
                video.pop("last_error", None)
                summary["downloaded_ocr"] += 1
                summary["video_bytes"] += result["video_bytes"]
                summary["segments"] += result["segments"]
            elif result["status"] == "ocr-empty":
                video["transcript_status"] = "ocr-empty"
                video["transcript_method"] = "burned-in-caption-ocr"
                video["transcript_segments"] = 0
                video["ocr_mean_confidence"] = round(result["mean_confidence"], 4)
                video["ocr_caption_band_y"] = round(result["caption_band_y"], 3)
                video["ocr_sample_step_seconds"] = args.step
                video["download_quality"] = result["quality_returned"]
                video.pop("last_error", None)
                summary["errors"] += 1
            else:
                # A forced recovery pass must not destroy an already usable
                # transcript merely because a fresh network/OCR attempt failed.
                if args.force and video.get("transcript_status") == "downloaded-ocr":
                    video["last_recovery_error"] = result["error"]
                else:
                    video["transcript_status"] = "ocr-error"
                    video["last_error"] = result["error"]
                summary["errors"] += 1

            manifest["last_ocr_batch"] = {
                **summary, "progress": f"{index}/{len(candidates)}", "last_bvid": video["bvid"],
            }
            save_manifest(args.manifest, manifest)
            print(json.dumps({"progress": f"{index}/{len(candidates)}", **result}, ensure_ascii=False), flush=True)
            if index < len(candidates):
                time.sleep(args.delay)
    finally:
        executor.shutdown(wait=True)

    summary["finished_at"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
    manifest["last_ocr_batch"] = summary
    save_manifest(args.manifest, manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
