#!/usr/bin/env python3
"""Read Bilibili public video metadata and signed in-product AI summaries."""

from __future__ import annotations

import hashlib
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

import certifi


MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.bilibili.com/",
}

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=25, context=SSL_CONTEXT) as response:
        return json.load(response)


def wbi_keys() -> tuple[str, str]:
    data = get_json("https://api.bilibili.com/x/web-interface/nav")["data"]["wbi_img"]
    img_key = data["img_url"].rsplit("/", 1)[-1].split(".", 1)[0]
    sub_key = data["sub_url"].rsplit("/", 1)[-1].split(".", 1)[0]
    return img_key, sub_key


def sign(params: dict[str, object], img_key: str, sub_key: str) -> str:
    mixin_source = img_key + sub_key
    mixin_key = "".join(mixin_source[i] for i in MIXIN_KEY_ENC_TAB)[:32]
    params = {**params, "wts": int(time.time())}
    filtered = {}
    for key, value in params.items():
        filtered[key] = re.sub(r"[!'()*]", "", str(value))
    query = urllib.parse.urlencode(sorted(filtered.items()))
    return query + "&w_rid=" + hashlib.md5((query + mixin_key).encode()).hexdigest()


def probe(bvid: str, img_key: str, sub_key: str) -> dict:
    info_url = "https://api.bilibili.com/x/web-interface/view?" + urllib.parse.urlencode({"bvid": bvid})
    info = get_json(info_url)
    if info.get("code") != 0:
        return {"bvid": bvid, "info_error": info}
    video = info["data"]
    summaries = []
    for page in video["pages"]:
        params = {
            "bvid": bvid,
            "cid": page["cid"],
            "up_mid": video["owner"]["mid"],
        }
        url = "https://api.bilibili.com/x/web-interface/view/conclusion/get?" + sign(params, img_key, sub_key)
        try:
            result = get_json(url)
        except Exception as exc:  # public endpoint occasionally rate-limits
            result = {"exception": repr(exc)}
        summaries.append({
            "page": page["page"],
            "part": page["part"],
            "cid": page["cid"],
            "duration": page["duration"],
            "conclusion": result,
        })
        time.sleep(0.2)
    return {
        "bvid": bvid,
        "title": video["title"],
        "description": video["desc"],
        "published_unix": video["pubdate"],
        "duration": video["duration"],
        "owner": video["owner"],
        "stat": video["stat"],
        "pages": summaries,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: bili_wbi_probe.py BV... [BV...]")
    img_key, sub_key = wbi_keys()
    results = [probe(bvid, img_key, sub_key) for bvid in sys.argv[1:]]
    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
