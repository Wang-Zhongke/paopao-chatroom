#!/usr/bin/env python3
"""Inventory a named series on one Bilibili creator account.

Uses public account/series endpoints. It never reads browser cookies.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import certifi


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Referer": "https://space.bilibili.com/",
}
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def get_json(base: str, params: dict[str, object]) -> dict:
    url = base + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30, context=SSL_CONTEXT) as response:
        data = json.load(response)
    if data.get("code") != 0:
        raise RuntimeError(f"Bilibili API error for {base}: {data}")
    return data


def list_series(mid: int) -> list[dict]:
    page_num = 1
    series: list[dict] = []
    while True:
        payload = get_json(
            "https://api.bilibili.com/x/polymer/web-space/seasons_series_list",
            {"mid": mid, "page_num": page_num, "page_size": 20},
        )["data"]
        items = payload.get("items_lists", {})
        batch = items.get("series_list", [])
        series.extend(batch)
        page = items.get("page", {})
        total = int(page.get("total", len(series)))
        if not batch or len(series) >= total:
            return series
        page_num += 1


def list_archives(mid: int, series_id: int) -> list[dict]:
    page_num = 1
    videos: list[dict] = []
    while True:
        data = get_json(
            "https://api.bilibili.com/x/series/archives",
            {
                "mid": mid,
                "series_id": series_id,
                "only_normal": "true",
                "sort": "desc",
                "pn": page_num,
                "ps": 30,
            },
        )["data"]
        batch = data.get("archives", [])
        videos.extend(batch)
        page = data.get("page", {})
        total = int(page.get("total", len(videos)))
        if not batch or len(videos) >= total:
            return videos
        page_num += 1


def to_iso(timestamp: int) -> str:
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone(dt.timedelta(hours=8))).isoformat()


def normalize(video: dict, series_meta: dict, expected_mid: int) -> dict:
    owner = video.get("owner", {})
    series_upper = series_meta.get("upper", {})
    return {
        "bvid": video.get("bvid"),
        "aid": video.get("aid"),
        "title": video.get("title", ""),
        "published_at": to_iso(int(video.get("pubdate", 0))),
        "duration_seconds": int(video.get("duration", 0)),
        "description": video.get("desc", ""),
        "owner_mid": int(owner.get("mid") or series_upper.get("mid") or expected_mid),
        "owner_name": owner.get("name") or series_upper.get("name") or "像素范",
        "series_id": int(series_meta["series_id"]),
        "series_name": series_meta["name"],
        "url": f"https://www.bilibili.com/video/{video.get('bvid')}/",
        "official_subtitle_status": "unchecked",
        "bilibili_ai_status": "unchecked",
        "burned_in_subtitle_status": "user_reported_present",
        "transcript_status": "pending",
        "dedupe_status": "unchecked",
        "review_status": "pending",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mid", type=int, default=15741969)
    parser.add_argument("--series-name", default="泡言泡语")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    all_series = list_series(args.mid)
    matches = []
    for item in all_series:
        meta = item.get("meta", item)
        if args.series_name in meta.get("name", ""):
            matches.append(meta)
    if len(matches) != 1:
        names = [item.get("meta", item).get("name") for item in all_series]
        raise SystemExit(f"expected one series match, got {len(matches)}; available={names}")

    meta = matches[0]
    raw_videos = list_archives(args.mid, int(meta["series_id"]))
    videos = [normalize(video, meta, args.mid) for video in raw_videos]

    owner_mismatch = [video for video in videos if video["owner_mid"] != args.mid]
    if owner_mismatch:
        raise SystemExit(f"owner mismatch: {[video['bvid'] for video in owner_mismatch]}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        "account_mid": args.mid,
        "series": meta,
        "video_count": len(videos),
        "videos": videos,
    }
    (args.output_dir / "corpus-index.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    fields = list(videos[0].keys()) if videos else []
    with (args.output_dir / "corpus-index.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(videos)

    print(json.dumps({
        "series_id": meta["series_id"],
        "series_name": meta["name"],
        "declared_total": meta.get("total"),
        "retrieved": len(videos),
        "first": videos[-1] if videos else None,
        "latest": videos[0] if videos else None,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"inventory failed: {exc}", file=sys.stderr)
        raise
