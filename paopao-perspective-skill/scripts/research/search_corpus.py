#!/usr/bin/env python3
"""Search line-addressable transcripts in the official 泡言泡语 corpus."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE = re.compile(r"^\[(\d+)\] \[([^]]+)\] (.*)$")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="regular expression, searched case-insensitively")
    parser.add_argument("--manifest", type=Path, default=Path("references/sources/bilibili/corpus-index.json"))
    parser.add_argument("--transcript-dir", type=Path, default=Path("references/sources/bilibili/transcripts/clean"))
    parser.add_argument("--year", type=int, action="append")
    parser.add_argument("--bvid", action="append")
    parser.add_argument("--context", type=int, default=1)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    pattern = re.compile(args.query, re.IGNORECASE)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    videos = {video["bvid"]: video for video in manifest["videos"]}
    selected = []
    for bvid, video in videos.items():
        if args.bvid and bvid not in set(args.bvid):
            continue
        year = int(video["published_at"][:4])
        if args.year and year not in set(args.year):
            continue
        path = args.transcript_dir / f"{bvid}.md"
        if path.exists():
            selected.append((video, path))

    matches: list[dict] = []
    for video, path in selected:
        segments = []
        for line in path.read_text(encoding="utf-8").splitlines():
            found = LINE.match(line)
            if found:
                segments.append({"line": int(found.group(1)), "time": found.group(2), "text": found.group(3)})
        for index, segment in enumerate(segments):
            if not pattern.search(segment["text"]):
                continue
            left, right = max(0, index - args.context), min(len(segments), index + args.context + 1)
            matches.append({
                "bvid": video["bvid"],
                "title": video["title"],
                "published_at": video["published_at"],
                "url": video["url"],
                "transcript_status": video.get("transcript_status"),
                "match": segment,
                "context": segments[left:right],
            })
            if len(matches) >= args.limit:
                break
        if len(matches) >= args.limit:
            break

    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
        return
    for item in matches:
        print(f"{item['published_at'][:10]} | {item['bvid']} | {item['title']}")
        for segment in item["context"]:
            marker = ">" if segment["line"] == item["match"]["line"] else " "
            print(f" {marker} [{segment['line']:04d}] [{segment['time']}] {segment['text']}")
        print(f"   {item['url']}")
        print()
    print(f"matches: {len(matches)}")


if __name__ == "__main__":
    main()
