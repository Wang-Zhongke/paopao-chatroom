#!/usr/bin/env python3
"""Generate a reproducible coverage report for the official Bilibili corpus."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path


TRANSCRIPT_LINE = re.compile(r"^\[\d+\] \[[^]]+\] (.*)$")


def hours(seconds: int) -> str:
    return f"{seconds / 3600:.2f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--transcript-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    videos = manifest["videos"]
    status = collections.Counter(video.get("transcript_status", "pending") for video in videos)
    quality = collections.Counter(video.get("transcript_quality_status", "unreviewed") for video in videos)
    by_year: dict[int, dict[str, int]] = collections.defaultdict(lambda: collections.defaultdict(int))
    characters = 0
    line_count = 0
    missing = []
    for video in videos:
        year = int(video["published_at"][:4])
        by_year[year]["videos"] += 1
        by_year[year]["seconds"] += int(video["duration_seconds"])
        by_year[year][video.get("transcript_status", "pending")] += 1
        transcript = args.transcript_dir / f"{video['bvid']}.md"
        if transcript.exists():
            for line in transcript.read_text(encoding="utf-8").splitlines():
                found = TRANSCRIPT_LINE.match(line)
                if found:
                    line_count += 1
                    characters += len(found.group(1))
        else:
            missing.append(video)

    generated = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
    output = [
        "# 「泡言泡语」官方 Bilibili 语料覆盖报告",
        "",
        f"- 生成时间：{generated}",
        f"- 官方账号 MID：`{manifest['account_mid']}`（像素范）",
        f"- 系列：`{manifest['series']['name']}`，series_id `{manifest['series']['series_id']}`",
        f"- 视频：{len(videos)} 条，总时长 {hours(sum(v['duration_seconds'] for v in videos))} 小时",
        f"- 已提取字幕行：{line_count}，正文字符：{characters}",
        "- 完整状态以 `corpus-index.json` 为准；本报告可重复生成。",
        "",
        "## 提取状态",
        "",
        "| 状态 | 视频数 | 说明 |",
        "|---|---:|---|",
    ]
    meanings = {
        "downloaded": "Bilibili ai-zh 字幕",
        "downloaded-ocr": "画面烧录字幕 OCR",
        "needs-ocr-asr": "等待 OCR",
        "ocr-error": "OCR/下载失败，等待重试",
        "pending": "尚未检查",
        "error": "Bilibili 字幕接口错误",
    }
    for key, count in sorted(status.items()):
        output.append(f"| `{key}` | {count} | {meanings.get(key, '')} |")

    output.extend([
        "", "## 质量分层", "",
        "机器文本存在不等于足以概括全片；人工抽样方法见 `manual-transcript-review.md`。", "",
        "| 质量状态 | 视频数 |", "|---|---:|",
    ])
    for key, count in sorted(quality.items()):
        output.append(f"| `{key}` | {count} |")

    all_statuses = sorted(status)
    output.extend(["", "## 年度覆盖", ""])
    header = "| 年份 | 视频 | 时长(h) | " + " | ".join(f"`{key}`" for key in all_statuses) + " |"
    output.append(header)
    output.append("|---:|---:|---:|" + "---:|" * len(all_statuses))
    for year in sorted(by_year):
        data = by_year[year]
        counts = " | ".join(str(data.get(key, 0)) for key in all_statuses)
        output.append(f"| {year} | {data['videos']} | {hours(data['seconds'])} | {counts} |")

    output.extend(["", "## 尚无文本", ""])
    if not missing:
        output.append("无。353 条视频均已有机器提取文本。")
    else:
        output.append(f"共 {len(missing)} 条：")
        output.append("")
        for video in missing:
            output.append(
                f"- `{video['bvid']}` · {video['published_at'][:10]} · "
                f"`{video.get('transcript_status')}` · {video['title']}"
            )

    ineligible = [video for video in videos if not video.get("core_evidence_eligible", False)]
    output.extend(["", "## 不可直接作为核心证据", ""])
    for video in ineligible:
        output.append(
            f"- `{video['bvid']}` · `{video.get('transcript_quality_status')}` · {video['title']}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(json.dumps({
        "videos": len(videos), "statuses": status, "lines": line_count,
        "characters": characters, "missing": len(missing), "quality": quality,
        "core_evidence_ineligible": len(ineligible), "output": str(args.output),
    }, ensure_ascii=False, default=dict, indent=2))


if __name__ == "__main__":
    main()
