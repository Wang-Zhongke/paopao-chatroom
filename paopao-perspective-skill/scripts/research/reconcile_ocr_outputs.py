#!/usr/bin/env python3
"""Recover complete OCR outputs whose batch was interrupted before checkpointing."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from bili_ocr_batch import save_manifest
from ocr_caption_clean import write_outputs


def raw_extent(path: Path) -> tuple[int, float]:
    rows = 0
    last = -1.0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows += 1
        last = float(row.get("actual_seconds", row.get("requested_seconds", 0)))
    return rows, last


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--step", type=float, default=0.8)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    raw_dir = args.output_dir / "transcripts" / "ocr-raw"
    recovered = []
    for video in manifest["videos"]:
        if video.get("transcript_status") in {"downloaded", "downloaded-ocr"}:
            continue
        raw_path = raw_dir / f"{video['bvid']}.jsonl"
        if not raw_path.exists():
            continue
        rows, last = raw_extent(raw_path)
        duration = float(video.get("duration_seconds", 0))
        # AVFoundation may report a final sample slightly before container duration.
        complete = rows > 0 and duration > 0 and last >= duration - max(3.0, args.step * 4)
        if not complete:
            continue
        record = {"bvid": video["bvid"], "rows": rows, "last_seconds": last, "duration": duration}
        if args.apply:
            result = write_outputs(raw_path, args.output_dir, video, args.step)
            if result["segments"] < 1:
                continue
            video["transcript_status"] = "downloaded-ocr"
            video["transcript_method"] = "burned-in-caption-ocr"
            video["transcript_segments"] = result["segments"]
            video["ocr_mean_confidence"] = round(result["mean_confidence"], 4)
            video["ocr_caption_band_y"] = round(result["caption_band_y"], 3)
            video["ocr_sample_step_seconds"] = args.step
            video["processed_at"] = dt.datetime.now(
                dt.timezone(dt.timedelta(hours=8))
            ).isoformat()
            video["reconciled_after_interruption"] = True
            video.pop("last_error", None)
            record["segments"] = result["segments"]
        recovered.append(record)

    if args.apply and recovered:
        save_manifest(args.manifest, manifest)
    print(json.dumps({"apply": args.apply, "recovered": recovered}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
