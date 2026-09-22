#!/usr/bin/env python3
"""Aggregate per-video research cards into a searchable JSONL/Markdown index."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def section(text: str, heading: str) -> str:
    found = re.search(rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    return re.sub(r"\s+", " ", found.group(1)).strip() if found else ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--card-dir", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = []
    for video in manifest["videos"]:
        path = args.card_dir / f"{video['bvid']}.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        records.append({
            "bvid": video["bvid"], "title": video["title"],
            "published_at": video["published_at"], "url": video["url"],
            "transcript_status": video.get("transcript_status"),
            "core_question": section(text, "核心问题"),
            "summary": section(text, "内容摘要"),
            "candidate_models": section(text, "可蒸馏候选"),
            "card": str(path),
        })
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    md = [
        "# 「泡言泡语」单视频研究卡索引",
        "",
        f"当前研究卡：{len(records)} / {len(manifest['videos'])}",
        "",
        "| 日期 | BVID | 核心问题 | 标题 |",
        "|---|---|---|---|",
    ]
    for record in records:
        question = record["core_question"].replace("|", "｜")
        title = record["title"].replace("|", "｜")
        md.append(
            f"| {record['published_at'][:10]} | [{record['bvid']}]({record['url']}) | {question} | {title} |"
        )
    args.output_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"cards": len(records), "videos": len(manifest["videos"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
