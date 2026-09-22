#!/usr/bin/env python3
"""Attach reproducible transcript-quality labels to the corpus manifest."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path


REVIEWED_CORE = {
    "BV1DkHYzEEYg", "BV1t6aPzWEnG", "BV1rqhdzWEBQ", "BV1kVe8zREeP",
    "BV1cPY4z3EV8", "BV1p9tmzfED9", "BV12rTiz1EEw", "BV1mpq8YFEmR",
    "BV1NqMbzFEZJ", "BV1RJ4m1p7vc",
}
WEAK = {
    "BV1BKfcB5ECu", "BV1PgnozvEao", "BV1SktizqEpe", "BV1nvtczxEUn",
    "BV1h7jhzFEi4", "BV13BTKzTEpb", "BV1Lq4y1x7QK", "BV1Xf4y1h74e",
}
COVERAGE_GAP = set()
UNUSABLE = set()


def write_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    fields: list[str] = []
    for video in manifest["videos"]:
        for key in video:
            if key not in fields:
                fields.append(key)
    with path.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(manifest["videos"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--qa-csv", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    with args.qa_csv.open(encoding="utf-8-sig", newline="") as handle:
        qa = {row["bvid"]: row for row in csv.DictReader(handle)}
    counts: dict[str, int] = {}
    for video in manifest["videos"]:
        bvid = video["bvid"]
        flags = qa.get(bvid, {}).get("flags", "")
        if bvid in UNUSABLE:
            quality, eligible = "unusable", False
        elif bvid in COVERAGE_GAP:
            quality, eligible = "coverage-gap", False
        elif bvid in WEAK:
            quality, eligible = "weak-evidence", False
        elif bvid in REVIEWED_CORE:
            quality, eligible = "reviewed-usable", True
        elif flags:
            quality, eligible = "needs-review", False
        else:
            quality, eligible = "machine-usable", True
        video["transcript_quality_status"] = quality
        video["core_evidence_eligible"] = eligible
        video["transcript_qa_flags"] = flags
        counts[quality] = counts.get(quality, 0) + 1

    if args.apply:
        write_manifest(args.manifest, manifest)
    print(json.dumps({"apply": args.apply, "quality_counts": counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
