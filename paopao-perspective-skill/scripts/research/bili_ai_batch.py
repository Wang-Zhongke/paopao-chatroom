#!/usr/bin/env python3
"""Checkpointed batch downloader for a Bilibili series inventory."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import time
from pathlib import Path

from bili_ai_subtitles import process


def save_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)

    videos = manifest.get("videos", [])
    if videos:
        csv_path = path.with_suffix(".csv")
        fields = []
        for video in videos:
            for key in video:
                if key not in fields:
                    fields.append(key)
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(videos)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bvid", nargs="*")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--delay", type=float, default=0.45)
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    requested = set(args.bvid or [])
    candidates = []
    for video in manifest["videos"]:
        if requested and video["bvid"] not in requested:
            continue
        status = video.get("transcript_status", "pending")
        # AI subtitles are the preferred source, but completed transcripts must
        # never be downgraded by a later probe. OCR-complete items are therefore
        # excluded unless the caller explicitly names their BVID.
        if status in {"downloaded", "downloaded-ocr"} and not requested:
            continue
        if status in {"error", "ocr-error"} and not args.retry_errors:
            continue
        if not requested and status not in {"pending", "needs-ocr-asr", "error", "ocr-error"}:
            continue
        candidates.append(video)
    if args.limit is not None:
        candidates = candidates[: args.limit]

    started = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
    summary = {"started_at": started, "selected": len(candidates), "downloaded": 0, "no_ai_zh": 0, "errors": 0}
    for index, video in enumerate(candidates, start=1):
        bvid = video["bvid"]
        prior_status = video.get("transcript_status", "pending")
        try:
            result = process(bvid, args.output_dir)
        except Exception as exc:
            result = {"bvid": bvid, "status": "error", "error": repr(exc)}

        video["processed_at"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
        if result["status"] == "downloaded":
            video["official_subtitle_status"] = "ai-zh"
            video["bilibili_ai_status"] = "available"
            video["transcript_status"] = "downloaded"
            video["transcript_segments"] = result["segments"]
            video.pop("last_error", None)
            summary["downloaded"] += 1
        elif result["status"] == "no-ai-zh":
            video["official_subtitle_status"] = "unavailable"
            video["bilibili_ai_status"] = "unavailable"
            # Preserve an OCR failure so it remains visible in the retry queue.
            video["transcript_status"] = "ocr-error" if prior_status == "ocr-error" else "needs-ocr-asr"
            video["available_tracks"] = [track.get("language") for track in result.get("tracks", [])]
            summary["no_ai_zh"] += 1
        else:
            video["transcript_status"] = "ocr-error" if prior_status == "ocr-error" else "error"
            video["last_error"] = result.get("error", "unknown error")
            summary["errors"] += 1

        manifest["last_batch"] = {**summary, "progress": f"{index}/{len(candidates)}", "last_bvid": bvid}
        save_manifest(args.manifest, manifest)
        print(json.dumps({"progress": f"{index}/{len(candidates)}", **result}, ensure_ascii=False), flush=True)
        if index < len(candidates):
            time.sleep(args.delay)

    manifest["last_batch"] = {**summary, "finished_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()}
    save_manifest(args.manifest, manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
