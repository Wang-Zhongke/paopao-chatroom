#!/usr/bin/env python3
"""Measure character-level agreement between two line-addressable transcripts."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path


LINE = re.compile(r"^\[\d+\] \[[^]]+\] (.*)$")
STRIP = re.compile(r'[\s，。！？、,.!?：:；;“”"‘’（）()\[\]【】—…·]')


def transcript_text(path: Path) -> str:
    parts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        found = LINE.match(line)
        if found:
            parts.append(found.group(1))
    return STRIP.sub("", "".join(parts))


def edit_distance(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, start=1):
        current = [row]
        for column, right_char in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (left_char != right_char),
            ))
        previous = current
    return previous[-1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    reference = transcript_text(args.reference)
    candidate = transcript_text(args.candidate)
    distance = edit_distance(reference, candidate)
    denominator = max(len(reference), len(candidate), 1)
    print(json.dumps({
        "reference_chars": len(reference),
        "candidate_chars": len(candidate),
        "sequence_matcher_ratio": round(
            difflib.SequenceMatcher(None, reference, candidate, autojunk=False).ratio(), 4
        ),
        "edit_distance": distance,
        "normalized_edit_similarity": round(1 - distance / denominator, 4),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
