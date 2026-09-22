#!/usr/bin/env python3
"""Download Bilibili's public AI Chinese subtitle track for UGC videos.

The web player returns subtitle-track metadata as protobuf and obfuscates the
subtitle path. This script mirrors the decoding routine shipped in Bilibili's
official web-player JavaScript, then saves raw JSON, SRT, and line-addressable
Markdown. It does not read or store browser cookies.
"""

from __future__ import annotations

import argparse
import datetime as dt
import functools
import json
import re
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import certifi

from bili_wbi_probe import sign, wbi_keys


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

# Extracted from Bilibili's official web player. The player XOR-decodes the
# path and accepts whichever prefix matches.
PATH_CODECS = [
    (
        'nP](wOFRvU.+<fjS{jn-!$D|Dz&",zT`',
        '=CFxYRn{.y|uVyO$uh&sikph?N.ilF/`',
    ),
    (
        'Bn"q~|albg@]Go~ACgyDvKnd+)_D}^&J?',
        "Cu~L!xs~f^&r@'vh=q]q{eeng*sEg^kp#J",
    ),
]


def fetch_bytes(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30, context=SSL_CONTEXT) as response:
        return response.read(), response.headers.get("content-type", "")


def fetch_json(url: str) -> dict:
    raw, _ = fetch_bytes(url)
    return json.loads(raw.decode("utf-8"))


@functools.lru_cache(maxsize=1)
def cached_wbi_keys() -> tuple[str, str]:
    return wbi_keys()


def read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7
        if shift > 70:
            raise ValueError("varint too long")
    raise ValueError("truncated varint")


def protobuf_fields(data: bytes) -> list[tuple[int, int, int | bytes]]:
    fields: list[tuple[int, int, int | bytes]] = []
    offset = 0
    while offset < len(data):
        key, offset = read_varint(data, offset)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, offset = read_varint(data, offset)
            fields.append((number, wire, value))
        elif wire == 1:
            end = offset + 8
            fields.append((number, wire, data[offset:end]))
            offset = end
        elif wire == 2:
            length, offset = read_varint(data, offset)
            end = offset + length
            if end > len(data):
                raise ValueError("truncated length-delimited field")
            fields.append((number, wire, data[offset:end]))
            offset = end
        elif wire == 5:
            end = offset + 4
            fields.append((number, wire, data[offset:end]))
            offset = end
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")
    return fields


def length_values(data: bytes, field_number: int) -> list[bytes]:
    return [value for number, wire, value in protobuf_fields(data)
            if number == field_number and wire == 2 and isinstance(value, bytes)]


def first_text(data: bytes, field_number: int) -> str:
    values = length_values(data, field_number)
    return values[0].decode("utf-8") if values else ""


def first_varint(data: bytes, field_number: int) -> int:
    for number, wire, value in protobuf_fields(data):
        if number == field_number and wire == 0 and isinstance(value, int):
            return value
    return 0


def xor_decode(value: str, key: str) -> str:
    return "".join(chr(ord(char) ^ ord(key[index % len(key)]))
                   for index, char in enumerate(value))


def decode_subtitle_url(obfuscated: bytes) -> str:
    encoded_url = obfuscated.decode("latin-1")
    marker = "//subtitle.bilibili.com/"
    if marker not in encoded_url:
        raise ValueError("unexpected subtitle host")
    encoded_path_and_query = encoded_url.split(marker, 1)[1]
    encoded_path, separator, query = encoded_path_and_query.partition("?")
    if not separator:
        raise ValueError("subtitle URL has no auth query")
    decoded_path = urllib.parse.unquote(encoded_path)
    for prefix, key in PATH_CODECS:
        clear = xor_decode(decoded_path, key + "bilibili")
        if clear.startswith(prefix):
            path = clear[len(prefix):]
            return "https://aisubtitle.hdslb.com" + path + "?" + query
    raise ValueError("no Bilibili subtitle path codec matched")


def video_info(bvid: str) -> dict:
    url = "https://api.bilibili.com/x/web-interface/view?" + urllib.parse.urlencode({"bvid": bvid})
    payload = fetch_json(url)
    if payload.get("code") != 0:
        raise RuntimeError(payload)
    return payload["data"]


def subtitle_tracks(aid: int, cid: int) -> list[dict]:
    params = {
        "oid": cid,
        "pid": aid,
        "context_ext": '{"video_type":1}',
        "type": 1,
        "cur_production_type": 0,
        "playlist_switch": 0,
        "web_location": 1315873,
    }
    query = sign(params, *cached_wbi_keys())
    raw, content_type = fetch_bytes("https://api.bilibili.com/x/v2/subtitle/web/view?" + query)
    if "json" in content_type:
        raise RuntimeError(json.loads(raw.decode("utf-8")))

    top_messages = length_values(raw, 1)
    if not top_messages:
        return []
    track_messages = length_values(top_messages[0], 3)
    tracks = []
    for message in track_messages:
        url_values = length_values(message, 5)
        tracks.append({
            "id": first_varint(message, 1),
            "id_str": first_text(message, 2),
            "language": first_text(message, 3),
            "language_label": first_text(message, 4),
            "subtitle_url": decode_subtitle_url(url_values[0]) if url_values else "",
        })
    return tracks


def srt_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def compact_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    return f"{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def normalize_content(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def save_outputs(output_dir: Path, info: dict, track: dict, payload: dict) -> dict:
    bvid = info["bvid"]
    raw_dir = output_dir / "transcripts" / "raw"
    srt_dir = output_dir / "transcripts" / "srt"
    clean_dir = output_dir / "transcripts" / "clean"
    for directory in (raw_dir, srt_dir, clean_dir):
        directory.mkdir(parents=True, exist_ok=True)

    raw_record = {
        "source": "bilibili-ai-subtitle",
        "retrieved_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        "video": {
            "bvid": bvid,
            "aid": info["aid"],
            "cid": info["pages"][0]["cid"],
            "title": info["title"],
            "owner": info["owner"],
            "published_at": dt.datetime.fromtimestamp(
                info["pubdate"], tz=dt.timezone(dt.timedelta(hours=8))
            ).isoformat(),
            "duration_seconds": info["duration"],
            "url": f"https://www.bilibili.com/video/{bvid}/",
        },
        "track": {key: value for key, value in track.items() if key != "subtitle_url"},
        "subtitle_payload": payload,
    }
    raw_path = raw_dir / f"{bvid}.json"
    raw_path.write_text(json.dumps(raw_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    body = payload.get("body", [])
    srt_lines = []
    md_lines = [
        f"# {info['title']}",
        "",
        f"- BVID: `{bvid}`",
        f"- 视频：<https://www.bilibili.com/video/{bvid}/>",
        f"- 发布：{raw_record['video']['published_at']}",
        "- 字幕来源：Bilibili `ai-zh` AI 中文字幕轨道",
        "- 文本状态：机器生成；未人工逐句校正",
        "",
        "## Transcript",
        "",
    ]
    for index, item in enumerate(body, start=1):
        start = float(item.get("from", 0))
        end = float(item.get("to", start))
        content = normalize_content(str(item.get("content", "")))
        srt_lines.extend([
            str(index),
            f"{srt_timestamp(start)} --> {srt_timestamp(end)}",
            content,
            "",
        ])
        md_lines.append(
            f"[{index:04d}] [{compact_timestamp(start)}–{compact_timestamp(end)}] {content}"
        )

    srt_path = srt_dir / f"{bvid}.srt"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    clean_path = clean_dir / f"{bvid}.md"
    clean_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {
        "bvid": bvid,
        "title": info["title"],
        "track": track["language"],
        "segments": len(body),
        "raw": str(raw_path),
        "srt": str(srt_path),
        "clean": str(clean_path),
    }


def process(bvid: str, output_dir: Path) -> dict:
    info = video_info(bvid)
    tracks = subtitle_tracks(info["aid"], info["pages"][0]["cid"])
    chinese = next((track for track in tracks if track["language"] == "ai-zh"), None)
    if not chinese:
        return {"bvid": bvid, "title": info["title"], "status": "no-ai-zh", "tracks": tracks}
    payload = fetch_json(chinese["subtitle_url"])
    result = save_outputs(output_dir, info, chinese, payload)
    result["status"] = "downloaded"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bvid", nargs="+")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for bvid in args.bvid:
        try:
            results.append(process(bvid, args.output_dir))
        except Exception as exc:
            results.append({"bvid": bvid, "status": "error", "error": repr(exc)})
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(result["status"] == "error" for result in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
