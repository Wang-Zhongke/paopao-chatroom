#!/usr/bin/env python3
"""Flag suspicious transcript coverage without treating machine confidence as truth."""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

from ocr_caption_clean import read_segments


LINE = re.compile(r"^\[\d+\] \[[^]]+\] (.*)$")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--transcript-dir", type=Path, required=True)
    parser.add_argument("--ocr-raw-dir", type=Path)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = []
    for video in manifest["videos"]:
        path = args.transcript_dir / f"{video['bvid']}.md"
        texts = []
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                found = LINE.match(line)
                if found:
                    texts.append(found.group(1).strip())
        minutes = max(float(video.get("duration_seconds", 0)) / 60, 1 / 60)
        characters = sum(len(text) for text in texts)
        frequencies = collections.Counter(texts)
        max_repeat = frequencies.most_common(1)[0][1] if frequencies else 0
        low_confidence_fraction: float | str = ""
        flags = []
        status = video.get("transcript_status", "pending")
        if status in {"downloaded", "downloaded-ocr"} and not texts:
            flags.append("completed-status-but-empty")
        if texts and len(texts) / minutes < 5:
            flags.append("low-segments-per-minute")
        if texts and characters / minutes < 30:
            flags.append("low-characters-per-minute")
        if texts and characters / minutes > 500:
            flags.append("high-characters-per-minute")
        if texts and max_repeat / len(texts) > 0.08 and max_repeat >= 10:
            flags.append("repeated-overlay-risk")
        if status == "downloaded-ocr" and float(video.get("ocr_mean_confidence", 1)) < 0.75:
            flags.append("low-vision-confidence")
        if status == "downloaded-ocr" and args.ocr_raw_dir:
            raw_path = args.ocr_raw_dir / f"{video['bvid']}.jsonl"
            if raw_path.exists():
                raw_segments, _ = read_segments(
                    raw_path, float(video.get("ocr_sample_step_seconds", 0.8))
                )
                low_count = sum(float(segment.get("confidence", 0)) < 0.5 for segment in raw_segments)
                low_confidence_fraction = low_count / max(len(raw_segments), 1)
                if low_confidence_fraction > 0.05:
                    flags.append("many-low-confidence-segments")
        records.append({
            "bvid": video["bvid"], "published_at": video["published_at"],
            "title": video["title"], "status": status,
            "duration_minutes": round(minutes, 2), "segments": len(texts),
            "characters": characters, "segments_per_minute": round(len(texts) / minutes, 2),
            "characters_per_minute": round(characters / minutes, 2),
            "max_exact_repeat": max_repeat, "ocr_mean_confidence": video.get("ocr_mean_confidence", ""),
            "ocr_low_confidence_fraction": (
                round(low_confidence_fraction, 4) if isinstance(low_confidence_fraction, float)
                else low_confidence_fraction
            ),
            "flags": ";".join(flags),
        })

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = list(records[0]) if records else []
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    flagged = [record for record in records if record["flags"]]
    md = [
        "# Bilibili transcript QA",
        "",
        "启发式异常报告；flag 只表示需要复核，不表示字幕错误。",
        "",
        f"- 视频：{len(records)}",
        f"- 已有文本：{sum(bool(record['segments']) for record in records)}",
        f"- 有异常标记：{len(flagged)}",
        "",
        "| BVID | 日期 | 状态 | 段/分 | 字/分 | flag | 标题 |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for record in flagged:
        md.append(
            f"| `{record['bvid']}` | {record['published_at'][:10]} | `{record['status']}` | "
            f"{record['segments_per_minute']} | {record['characters_per_minute']} | "
            f"{record['flags']} | {record['title'].replace('|', '｜')} |"
        )
    args.output_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"videos": len(records), "with_text": sum(bool(r["segments"]) for r in records),
                      "flagged": len(flagged)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
