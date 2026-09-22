#!/usr/bin/env python3
"""Probe Bilibili player subtitle endpoints for one public video."""

from __future__ import annotations

import argparse
import json
import urllib.parse

from bili_wbi_probe import get_json, sign, wbi_keys


def signed_get(base: str, params: dict[str, object], keys: tuple[str, str]) -> dict:
    return get_json(base + "?" + sign(params, *keys))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bvid")
    args = parser.parse_args()

    info = get_json(
        "https://api.bilibili.com/x/web-interface/view?"
        + urllib.parse.urlencode({"bvid": args.bvid})
    )
    if info.get("code") != 0:
        raise SystemExit(json.dumps(info, ensure_ascii=False))
    data = info["data"]
    aid = data["aid"]
    cid = data["pages"][0]["cid"]
    keys = wbi_keys()

    attempts = {}
    endpoints = {
        "player_wbi_v2": (
            "https://api.bilibili.com/x/player/wbi/v2",
            {"aid": aid, "cid": cid, "bvid": args.bvid},
        ),
        "subtitle_web_view": (
            "https://api.bilibili.com/x/v2/subtitle/web/view",
            {
                "oid": cid,
                "pid": aid,
                "context_ext": '{"video_type":1}',
                "type": 1,
                "cur_production_type": 0,
                "playlist_switch": 0,
                "web_location": 1315873,
            },
        ),
    }
    for name, (base, params) in endpoints.items():
        try:
            attempts[name] = signed_get(base, params, keys)
        except Exception as exc:
            attempts[name] = {"exception": repr(exc)}

    print(json.dumps({
        "bvid": args.bvid,
        "aid": aid,
        "cid": cid,
        "title": data["title"],
        "attempts": attempts,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
