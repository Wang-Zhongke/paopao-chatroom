#!/usr/bin/env python3
"""Download one public Bilibili video for burned-in caption OCR.

The script uses public view/playurl endpoints and never reads browser cookies.
Downloaded media is a temporary research input; keep it outside the Skill corpus.
"""

from __future__ import annotations

import argparse
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
    "Referer": "https://www.bilibili.com/",
}
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def get_json(base: str, params: dict[str, object]) -> dict:
    url = base + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30, context=SSL_CONTEXT) as response:
        payload = json.load(response)
    if payload.get("code") != 0:
        raise RuntimeError(f"Bilibili API error for {base}: {payload}")
    return payload["data"]


def resolve_stream(
    bvid: str, quality: int, page_index: int = 0, dash_video: bool = False
) -> dict:
    view = get_json("https://api.bilibili.com/x/web-interface/view", {"bvid": bvid})
    pages = view.get("pages", [])
    if not pages:
        raise RuntimeError(f"no pages found for {bvid}")
    if page_index < 0 or page_index >= len(pages):
        raise RuntimeError(f"page index {page_index} out of range; page_count={len(pages)}")
    page = pages[page_index]
    cid = int(page["cid"])
    play_params = {
        "bvid": bvid,
        "cid": cid,
        "qn": quality,
        "fnver": 0,
        "fnval": 4048 if dash_video else 0,
        "fourk": 0,
    }
    if not dash_video:
        play_params["platform"] = "html5"
    play = get_json("https://api.bilibili.com/x/player/playurl", play_params)
    if dash_video:
        tracks = play.get("dash", {}).get("video", [])
        if not tracks:
            raise RuntimeError(f"no DASH video stream returned for {bvid}; keys={list(play)}")
        eligible = [track for track in tracks if int(track.get("id", 0)) <= quality] or tracks
        avc = [track for track in eligible if str(track.get("codecs", "")).startswith("avc1")]
        track = max(avc or eligible, key=lambda item: int(item.get("id", 0)))
        durl = [{
            "url": track.get("baseUrl") or track.get("base_url"),
            "backup_url": track.get("backupUrl") or track.get("backup_url") or [],
            "size": 0,
        }]
        quality_returned = int(track.get("id", 0))
        stream_format = "dash-video"
        dash_details = {
            "width": int(track.get("width", 0)), "height": int(track.get("height", 0)),
            "codecs": track.get("codecs", ""), "frame_rate": track.get("frameRate") or track.get("frame_rate"),
        }
    else:
        durl = play.get("durl", [])
        if not durl:
            raise RuntimeError(f"no progressive stream returned for {bvid}; keys={list(play)}")
        quality_returned = int(play.get("quality", 0))
        stream_format = play.get("format", "")
        dash_details = {}
    return {
        "bvid": bvid,
        "cid": cid,
        "page_index": page_index,
        "page_number": int(page.get("page", page_index + 1)),
        "page_count": len(pages),
        "page_part": page.get("part", ""),
        "page_duration_seconds": int(page.get("duration", 0)),
        "title": view.get("title", ""),
        "duration_seconds": int(view.get("duration", 0)),
        "quality_requested": quality,
        "quality_returned": quality_returned,
        "format": stream_format,
        "timelength_ms": int(play.get("timelength", 0)),
        "segments": durl,
        **dash_details,
    }


def download(stream: dict, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    total = 0
    with temporary.open("w+b") as output:
        for segment in stream["segments"]:
            segment_start = output.tell()
            urls = [segment["url"], *(segment.get("backup_url") or [])]
            expected_size = int(segment.get("size", 0) or 0)
            last_error: Exception | None = None
            for url in urls:
                output.seek(segment_start)
                output.truncate()
                total = segment_start
                has_nonzero_data = False
                request = urllib.request.Request(
                    url,
                    headers={**HEADERS, "Referer": f"https://www.bilibili.com/video/{stream['bvid']}/"},
                )
                try:
                    with urllib.request.urlopen(request, timeout=180, context=SSL_CONTEXT) as response:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            output.write(chunk)
                            total += len(chunk)
                            if not has_nonzero_data and any(chunk):
                                has_nonzero_data = True
                    segment_bytes = total - segment_start
                    if segment_bytes < 1024 or not has_nonzero_data:
                        raise RuntimeError(
                            f"invalid media payload from CDN: bytes={segment_bytes}, "
                            f"nonzero={has_nonzero_data}"
                        )
                    if expected_size and segment_bytes < int(expected_size * 0.9):
                        raise RuntimeError(
                            f"truncated media payload from CDN: bytes={segment_bytes}, "
                            f"expected={expected_size}"
                        )
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
            if last_error is not None:
                raise last_error
    temporary.replace(destination)
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bvid")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--quality",
        type=int,
        default=32,
        help="Bilibili quality id; 16=360p, 32=480p (default)",
    )
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--page-index", type=int, default=0, help="zero-based multipart page index")
    parser.add_argument("--dash-video", action="store_true", help="download a video-only DASH track")
    args = parser.parse_args()

    stream = resolve_stream(args.bvid, args.quality, args.page_index, args.dash_video)
    public = {key: value for key, value in stream.items() if key != "segments"}
    public["declared_bytes"] = sum(int(item.get("size", 0)) for item in stream["segments"])
    public["segment_count"] = len(stream["segments"])
    if not args.metadata_only:
        public["downloaded_bytes"] = download(stream, args.output)
        public["output"] = str(args.output)
    print(json.dumps(public, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"download failed: {exc}", file=sys.stderr)
        raise
