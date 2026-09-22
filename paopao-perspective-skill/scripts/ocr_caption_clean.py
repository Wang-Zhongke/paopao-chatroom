#!/usr/bin/env python3
"""Turn frame-level Vision OCR JSONL into deduplicated SRT and Markdown."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import difflib
import json
import re
from pathlib import Path

from bili_ai_subtitles import compact_timestamp, srt_timestamp


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).strip()


def strip_parallel_english(value: str) -> str:
    """Drop a long appended English translation when Chinese comes first.

    Some vertical exports render Chinese and English as adjacent caption lines,
    and Vision occasionally merges both into one observation. Short technical
    tokens (AI, UI, GPU, Cursor) are intentionally preserved.
    """
    for match in re.finditer(r"[A-Za-z][A-Za-z'’.,?]{9,}", value):
        prefix = value[: match.start()]
        if len(re.findall(r"[\u3400-\u9fff]", prefix)) >= 2:
            return prefix.rstrip("，。！？、,:;；")
    return value


def detect_caption_band(rows: list[dict]) -> float:
    bins: dict[int, dict[str, object]] = collections.defaultdict(
        lambda: {"frames": 0, "texts": set(), "cjk_texts": set()}
    )
    for row in rows:
        seen_bins: set[int] = set()
        for item in row.get("observations", []):
            text = normalize(str(item.get("text", "")))
            x = float(item.get("x", 0))
            width = float(item.get("width", 0))
            center_x = x + width / 2
            if len(text) < 2 or float(item.get("confidence", 0)) < 0.25:
                continue
            if x + width < 0.12 or x > 0.88:
                continue
            if width < 0.07:
                continue
            # The series' burned-in speech captions are horizontally centred.
            # Text inside an embedded vertical clip, slide, app UI, or watermark
            # is often confined to a side column and can otherwise win solely
            # because it contains many distinct strings.
            if not 0.22 <= center_x <= 0.78:
                continue
            key = round(float(item.get("y", 0)) / 0.04)
            bins[key]["texts"].add(text)
            if re.search(r"[\u3400-\u9fff]", text):
                bins[key]["cjk_texts"].add(text)
            seen_bins.add(key)
        for key in seen_bins:
            bins[key]["frames"] += 1
    if not bins:
        return 0.10
    # Captions occupy many frames but continually change. A static watermark
    # may be frequent, yet has very low text diversity and therefore loses.
    winner = max(
        bins,
        # This corpus is Chinese. Some later vertical exports have simultaneous
        # Chinese and English subtitles; without a language preference, noisy
        # English OCR fragments can appear more "diverse" and win the band.
        key=lambda key: (
            len(bins[key]["cjk_texts"]),
            len(bins[key]["texts"]),
            int(bins[key]["frames"]),
        ),
    )
    return winner * 0.04


def frame_caption(row: dict, band_y: float, band_radius: float = 0.09) -> tuple[str, float]:
    items = [
        item for item in row.get("observations", [])
        if float(item.get("confidence", 0)) >= 0.25
        and abs(float(item.get("y", 1)) - band_y) <= band_radius
        and float(item.get("x", 0)) + float(item.get("width", 0)) >= 0.12
        and float(item.get("x", 1)) <= 0.88
        and float(item.get("width", 0)) >= 0.07
        and 0.22 <= float(item.get("x", 0)) + float(item.get("width", 0)) / 2 <= 0.78
    ]
    if not items:
        return "", 0.0

    # Vision uses bottom-left coordinates. Caption lines should read from the
    # visually higher line to the lower line, and left to right within a line.
    items.sort(key=lambda item: (-round(float(item.get("y", 0)) / 0.055), float(item.get("x", 0))))
    text = strip_parallel_english(normalize("".join(str(item.get("text", "")) for item in items)))
    confidence = sum(float(item.get("confidence", 0)) for item in items) / len(items)
    return text, confidence


def similar(left: str, right: str) -> bool:
    if left == right:
        return True
    if min(len(left), len(right)) >= 4 and (left in right or right in left):
        return True
    return difflib.SequenceMatcher(a=left, b=right, autojunk=False).ratio() >= 0.82


def read_segments(path: Path, step: float, band_y_override: float | None = None) -> tuple[list[dict], float]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    band_y = band_y_override if band_y_override is not None else detect_caption_band(rows)
    segments: list[dict] = []
    current: dict | None = None
    for row in rows:
        timestamp = float(row.get("actual_seconds", row.get("requested_seconds", 0)))
        text, confidence = frame_caption(row, band_y)
        if len(text) < 2:
            if current and timestamp - current["last_seen"] > step * 1.6:
                current["end"] = current["last_seen"] + step
                segments.append(current)
                current = None
            continue

        if current and timestamp - current["last_seen"] <= step * 2.1 and similar(current["text"], text):
            current["last_seen"] = timestamp
            score = confidence + min(len(text), 80) / 1000
            if score > current["score"]:
                current["text"] = text
                current["confidence"] = confidence
                current["score"] = score
            continue

        if current:
            current["end"] = current["last_seen"] + step
            segments.append(current)
        current = {
            "start": timestamp,
            "last_seen": timestamp,
            "end": timestamp + step,
            "text": text,
            "confidence": confidence,
            "score": confidence + min(len(text), 80) / 1000,
        }
    if current:
        current["end"] = current["last_seen"] + step
        segments.append(current)

    for segment in segments:
        segment.pop("last_seen", None)
        segment.pop("score", None)
    return segments, band_y


def write_outputs(
    raw_path: Path, output_dir: Path, video: dict, step: float,
    band_y_override: float | None = None,
) -> dict:
    bvid = video["bvid"]
    segments, band_y = read_segments(raw_path, step, band_y_override)
    srt_dir = output_dir / "transcripts" / "srt"
    clean_dir = output_dir / "transcripts" / "clean"
    srt_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    srt_lines: list[str] = []
    md_lines = [
        f"# {video['title']}",
        "",
        f"- BVID: `{bvid}`",
        f"- 视频：<https://www.bilibili.com/video/{bvid}/>",
        f"- 发布：{video['published_at']}",
        "- 字幕来源：视频画面烧录字幕，经 macOS Vision OCR 提取",
        f"- OCR 采样间隔：{step:.2f} 秒",
        f"- 自动检测字幕带（裁剪区域坐标）：y≈{band_y:.2f}",
        "- 文本状态：机器提取并自动去重；未人工逐句校正",
        "",
        "## Transcript",
        "",
    ]
    for index, segment in enumerate(segments, start=1):
        start, end, text = segment["start"], segment["end"], segment["text"]
        srt_lines.extend([
            str(index),
            f"{srt_timestamp(start)} --> {srt_timestamp(end)}",
            text,
            "",
        ])
        md_lines.append(f"[{index:04d}] [{compact_timestamp(start)}–{compact_timestamp(end)}] {text}")

    srt_path = srt_dir / f"{bvid}.srt"
    clean_path = clean_dir / f"{bvid}.md"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    clean_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {
        "segments": len(segments),
        "srt": str(srt_path),
        "clean": str(clean_path),
        "mean_confidence": (
            sum(segment["confidence"] for segment in segments) / len(segments) if segments else 0
        ),
        "caption_band_y": band_y,
        "cleaned_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_jsonl", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--video-json", required=True, help="JSON object with bvid/title/published_at")
    parser.add_argument("--step", type=float, default=0.8)
    parser.add_argument("--band-y", type=float, help="override automatic caption-band y coordinate")
    args = parser.parse_args()
    result = write_outputs(
        args.raw_jsonl, args.output_dir, json.loads(args.video_json), args.step, args.band_y
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
