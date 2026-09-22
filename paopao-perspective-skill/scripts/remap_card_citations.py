#!/usr/bin/env python3
"""Remap evidence-card transcript line ranges from their stable time ranges.

OCR cleaning can merge or split adjacent captions, so line numbers are not a
durable identifier. Evidence cards already carry both line and time ranges;
this script treats timestamps as canonical and refreshes only the line range.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TRANSCRIPT = re.compile(
    r"^\[(\d+)\] \[(\d{2}:\d{2}(?::\d{2})?\.\d{3})[–-]"
    r"(\d{2}:\d{2}(?::\d{2})?\.\d{3})\]"
)
CARD_REF = re.compile(
    r"\[(\d{1,5})(?:[–-](\d{1,5}))?\]\s*"
    r"\[(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d{1,3})?)[–-]"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d{1,3})?)\]"
)


def seconds(value: str) -> float:
    parts = [float(part) for part in value.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def load_segments(path: Path) -> list[tuple[int, float, float]]:
    segments = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = TRANSCRIPT.match(raw_line)
        if match:
            segments.append((int(match.group(1)), seconds(match.group(2)), seconds(match.group(3))))
    return segments


def nearest_range(segments: list[tuple[int, float, float]], start: float, end: float) -> tuple[int, int]:
    overlapping = [line for line, seg_start, seg_end in segments if seg_end >= start and seg_start <= end]
    if overlapping:
        return min(overlapping), max(overlapping)
    # OCR can omit an entire embedded clip. In that case map to the closest
    # surviving caption so the card visibly collapses to a one-line anchor.
    nearest = min(segments, key=lambda item: min(abs(item[1] - start), abs(item[2] - end)))
    return nearest[0], nearest[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--card-dir", type=Path, required=True)
    parser.add_argument("--transcript-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--ocr-only", action="store_true", help="only refresh cards sourced from burned-in OCR")
    parser.add_argument("--bvid", nargs="*", help="limit refresh to explicit BVIDs")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = {"cards": 0, "cards_changed": 0, "references_seen": 0, "references_changed": 0, "missing": []}
    requested = set(args.bvid or [])
    for card_path in sorted(args.card_dir.glob("BV*.md")):
        if requested and card_path.stem not in requested:
            continue
        transcript_path = args.transcript_dir / card_path.name
        if not transcript_path.exists():
            report["missing"].append(card_path.stem)
            continue
        segments = load_segments(transcript_path)
        if not segments:
            report["missing"].append(card_path.stem)
            continue
        text = card_path.read_text(encoding="utf-8")
        if args.ocr_only and not any(label in text for label in ("burned-in-caption-ocr", "vision-ocr")):
            continue
        local_seen = 0
        local_changed = 0

        def replace(match: re.Match[str]) -> str:
            nonlocal local_seen, local_changed
            local_seen += 1
            start_line, end_line = nearest_range(segments, seconds(match.group(3)), seconds(match.group(4)))
            replacement = f"[{start_line:04d}–{end_line:04d}] [{match.group(3)}–{match.group(4)}]"
            if replacement != match.group(0):
                local_changed += 1
            return replacement

        revised = CARD_REF.sub(replace, text)
        report["cards"] += 1
        report["references_seen"] += local_seen
        report["references_changed"] += local_changed
        if revised != text:
            report["cards_changed"] += 1
            if args.apply:
                card_path.write_text(revised, encoding="utf-8")

    report_path = args.report
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
