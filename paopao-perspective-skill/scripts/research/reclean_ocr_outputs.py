#!/usr/bin/env python3
"""Rebuild OCR clean/SRT files with the current caption-band rules.

The raw frame OCR is the durable extraction artifact.  This script makes
cleaning upgrades reproducible and records which existing evidence cards need
their line references refreshed after a transcript changes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

from ocr_caption_clean import write_outputs


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def save_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    fields: list[str] = []
    for video in manifest.get("videos", []):
        for key in video:
            if key not in fields:
                fields.append(key)
    with path.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(manifest.get("videos", []))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--card-dir", type=Path, required=True)
    parser.add_argument("--step", type=float, default=0.8)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = {
        "cleaner_version": 4,
        "apply": args.apply,
        "processed": 0,
        "changed": [],
        "unchanged": [],
        "missing_raw": [],
        "stale_cards": [],
    }
    for video in manifest.get("videos", []):
        if video.get("transcript_status") != "downloaded-ocr":
            continue
        bvid = video["bvid"]
        raw_path = args.output_dir / "transcripts" / "ocr-raw" / f"{bvid}.jsonl"
        clean_path = args.output_dir / "transcripts" / "clean" / f"{bvid}.md"
        if not raw_path.exists():
            report["missing_raw"].append(bvid)
            continue
        old_text = clean_path.read_text(encoding="utf-8") if clean_path.exists() else ""
        old_hash = digest(old_text)
        old_segments = video.get("transcript_segments")
        old_confidence = video.get("ocr_mean_confidence")
        old_band = video.get("ocr_caption_band_y")
        if args.apply:
            result = write_outputs(raw_path, args.output_dir, video, args.step)
            new_text = clean_path.read_text(encoding="utf-8")
            new_hash = digest(new_text)
            video["transcript_segments"] = result["segments"]
            video["ocr_mean_confidence"] = round(result["mean_confidence"], 4)
            video["ocr_caption_band_y"] = round(result["caption_band_y"], 3)
            video["ocr_cleaner_version"] = 4
        else:
            # Dry-run intentionally reports candidates only; it does not create
            # temporary clean files that could race with an active batch.
            new_hash = old_hash
            result = {
                "segments": old_segments,
                "mean_confidence": old_confidence,
                "caption_band_y": old_band,
            }
        report["processed"] += 1
        record = {
            "bvid": bvid,
            "old_segments": old_segments,
            "new_segments": result["segments"],
            "old_confidence": old_confidence,
            "new_confidence": round(float(result["mean_confidence"] or 0), 4),
            "old_band": old_band,
            "new_band": round(float(result["caption_band_y"] or 0), 3),
        }
        target = "changed" if old_hash != new_hash else "unchanged"
        report[target].append(record)
        if target == "changed" and (args.card_dir / f"{bvid}.md").exists():
            report["stale_cards"].append(bvid)

    if args.apply:
        save_manifest(args.manifest, manifest)
    report_path = args.report or (args.output_dir / "transcripts" / "reclean-report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "processed": report["processed"],
        "changed": len(report["changed"]),
        "unchanged": len(report["unchanged"]),
        "missing_raw": len(report["missing_raw"]),
        "stale_cards": len(report["stale_cards"]),
        "report": str(report_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
