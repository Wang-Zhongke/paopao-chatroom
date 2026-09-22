#!/usr/bin/env python3
"""Build a heuristic topic-routing index for the 泡言泡语 corpus.

Tags route research; they are not evidence that a video endorses a position.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path


TOPICS = {
    "career": ["职业", "行业", "工作", "岗位", "选择", "年轻人", "学历", "大学", "毕业", "转行", "大厂", "上班", "职场"],
    "ai-career": ["AI", "人工智能", "大模型", "Agent", "RAG", "MCP", "AGI", "Claude", "GPT", "数据标注", "训练师", "提示词"],
    "job-search": ["求职", "简历", "面试", "招聘", "薪资", "工资", "背调", "offer", "跳槽", "离职", "裁员"],
    "personal-growth": ["内向", "外向", "表达", "自信", "信息差", "认知", "年龄", "焦虑", "成长", "主体性", "学习", "努力"],
    "personal-brand": ["自媒体", "个人品牌", "个人IP", "流量", "内容", "直播", "博主", "账号", "粉丝", "朋友圈"],
    "business-management": ["商业", "生意", "创业", "公司", "老板", "员工", "管理", "团队", "知识付费", "盈利", "赚钱", "现金流", "成本", "企业"],
    "design-product": ["UI", "UX", "设计", "产品", "审美", "用户体验", "作品集", "交互", "Figma", "Sketch", "B端"],
}
LINE = re.compile(r"^\[\d+\] \[[^]]+\] (.*)$")


def occurrences(text: str, term: str) -> int:
    return len(re.findall(re.escape(term), text, flags=re.IGNORECASE))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--transcript-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = []
    counts: collections.Counter[str] = collections.Counter()
    for video in manifest["videos"]:
        transcript_path = args.transcript_dir / f"{video['bvid']}.md"
        transcript_parts = []
        if transcript_path.exists():
            for line in transcript_path.read_text(encoding="utf-8").splitlines():
                found = LINE.match(line)
                if found:
                    transcript_parts.append(found.group(1))
        transcript = "".join(transcript_parts)
        title = video.get("title", "")
        description = video.get("description", "")
        scores = {}
        for topic, terms in TOPICS.items():
            score = 0
            for term in terms:
                score += 5 * min(occurrences(title, term), 2)
                score += 2 * min(occurrences(description, term), 5)
                score += min(occurrences(transcript, term), 20)
            if score:
                scores[topic] = score
        tags = [topic for topic, score in scores.items() if score >= 4]
        if not tags:
            tags = ["other"]
        for tag in tags:
            counts[tag] += 1
        records.append({
            "bvid": video["bvid"], "published_at": video["published_at"],
            "title": title, "url": video["url"],
            "transcript_status": video.get("transcript_status"),
            "tags": tags, "scores": scores,
        })

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps({
        "method": "heuristic keyword routing; tags are not viewpoint evidence",
        "topic_counts": counts,
        "videos": records,
    }, ensure_ascii=False, default=dict, indent=2) + "\n", encoding="utf-8")
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "bvid", "published_at", "title", "url", "transcript_status", "tags", "scores",
        ])
        writer.writeheader()
        for record in records:
            writer.writerow({**record, "tags": ";".join(record["tags"]),
                             "scores": json.dumps(record["scores"], ensure_ascii=False)})
    print(json.dumps({"videos": len(records), "topic_counts": counts}, ensure_ascii=False,
                     default=dict, indent=2))


if __name__ == "__main__":
    main()
