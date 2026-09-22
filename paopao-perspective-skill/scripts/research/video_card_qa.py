#!/usr/bin/env python3
"""Validate structure and transcript citations in per-video research cards."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED = ["核心问题", "内容摘要", "主要判断与推理", "例子与类比", "可蒸馏候选", "时间与语境", "证据限制"]
CITATION = re.compile(r"\[(\d{1,5})(?:[–-](\d{1,5}))?\]")
PROSE_CITATION = re.compile(r"(?:对应)?转录(?:约)?\s*(\d{1,5})(?:[–-](\d{1,5}))?\s*行")
TRANSCRIPT_LINE = re.compile(r"^\[(\d+)\] \[")


def section(text: str, heading: str) -> str:
    found = re.search(rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    return found.group(1).strip() if found else ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--card-dir", type=Path, required=True)
    parser.add_argument("--transcript-dir", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for card in sorted(args.card_dir.glob("BV*.md")):
        bvid = card.stem
        text = card.read_text(encoding="utf-8")
        transcript = args.transcript_dir / f"{bvid}.md"
        max_line = 0
        if transcript.exists():
            for line in transcript.read_text(encoding="utf-8").splitlines():
                found = TRANSCRIPT_LINE.match(line)
                if found:
                    max_line = max(max_line, int(found.group(1)))
        issues = []
        for heading in REQUIRED:
            if not section(text, heading):
                issues.append(f"missing:{heading}")
        summary_length = len(re.sub(r"\s+", "", section(text, "内容摘要")))
        if not 80 <= summary_length <= 350:
            issues.append(f"summary-length:{summary_length}")
        citations = []
        for start, end in CITATION.findall(text) + PROSE_CITATION.findall(text):
            citations.append(int(start))
            if end:
                citations.append(int(end))
        if not citations:
            issues.append("no-line-citations")
        if any(value < 1 or value > max_line for value in citations):
            issues.append(f"citation-out-of-range:max={max_line}")
        if not transcript.exists():
            issues.append("missing-transcript")
        results.append({
            "bvid": bvid, "summary_chars": summary_length, "citations": len(citations),
            "max_transcript_line": max_line, "issues": issues,
        })
    bad = [result for result in results if result["issues"]]
    print(json.dumps({
        "cards": len(results), "passed": len(results) - len(bad), "failed": len(bad),
        "failures": bad,
    }, ensure_ascii=False, indent=2))
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
