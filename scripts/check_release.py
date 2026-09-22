#!/usr/bin/env python3
"""Verify a built release directory; never print matched credential contents."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

SKILL = "paopao-perspective-skill"
BILI = "references/sources/bilibili"
FORBIDDEN_PARTS = {".git", ".next", ".next-dev", "node_modules", ".pnpm-store", "transcripts", "bilibili-metadata", "__pycache__", "test-results"}
SECRETS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "api-key": re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "credential-assignment": re.compile(r"(?i)(?:DEEPSEEK_API_KEY|OPENAI_API_KEY|SESSDATA|bili_jct)\s*[=:]\s*[\"']?([a-zA-Z0-9%_-]{24,})"),
}
LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+\"[^\"]*\")?\)")


def check(directory: Path) -> list[str]:
    issues = []
    if directory.is_symlink():
        return ["package: symlink-root"]
    directory = directory.resolve()
    files = {}
    for path in sorted(directory.rglob("*")):
        rel = path.relative_to(directory).as_posix()
        if path.is_symlink():
            issues.append(f"{rel}: symlink")
            continue
        if not path.is_file():
            continue
        if any(part in FORBIDDEN_PARTS for part in path.relative_to(directory).parts) or path.name == ".DS_Store" or (path.name.startswith(".env") and path.name != ".env.example") or (path.suffix.lower() in {".mp4", ".m4s", ".mp3", ".srt", ".png"} and rel != "docs/assets/chatroom.png"):
            issues.append(f"{rel}: forbidden-path")
        data = path.read_bytes()
        if len(data) > 5 * 1024 * 1024:
            issues.append(f"{rel}: exceeds-5-MiB-file-limit")
        if path.name != "MANIFEST.json":
            files[rel] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        if rel == "docs/assets/chatroom.png":
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                issues.append(f"{rel}: invalid-png")
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            issues.append(f"{rel}: unexpected-binary")
            continue
        for label, pattern in SECRETS.items():
            if pattern.search(content):
                issues.append(f"{rel}: {label}")
        if "aisubtitle.hdslb.com" in content and path.suffix in {".json", ".jsonl"}:
            issues.append(f"{rel}: temporary-subtitle-url")
        if path.suffix == ".md":
            # Ignore fenced code examples; they are not rendered navigation links.
            prose = re.sub(r"```.*?```", "", content, flags=re.S)
            for match in LINK.finditer(prose):
                href = match.group(1).strip("<>")
                if href.startswith(("#", "//")) or urlsplit(href).scheme:
                    continue
                target = (path.parent / unquote(href.split("#")[0])).resolve()
                if not target.is_relative_to(directory) or not target.exists():
                    issues.append(f"{rel}: broken-or-external-local-link")
    manifest_file = directory / "MANIFEST.json"
    if not manifest_file.is_file():
        issues.append("MANIFEST.json: missing")
    else:
        try:
            declared = json.loads(manifest_file.read_text())
            expected = {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]} for row in declared["files"]}
            for name in sorted(files.keys() | expected.keys()):
                if files.get(name) != expected.get(name):
                    issues.append(f"{name}: manifest-mismatch")
        except (KeyError, TypeError, json.JSONDecodeError):
            issues.append("MANIFEST.json: invalid")
    skill = directory if (directory / "SKILL.md").is_file() else directory / SKILL
    page = directory / "app/page.tsx"
    if page.is_file():
        content = page.read_text()
        if "/paopao-avatar.png" in content:
            issues.append("app/page.tsx: excluded-portrait-reference")
        if "/paopao-mark.svg" in content and not (directory / "public/paopao-mark.svg").is_file():
            issues.append("public/paopao-mark.svg: missing-runtime-asset")
    for name in ("SKILL.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "references/expression-dna.md"):
        if not (skill / name).is_file():
            issues.append(f"{name}: missing-required-skill-file")
    try:
        corpus = json.loads((skill / BILI / "corpus-index.json").read_text())
        cards = [json.loads(line) for line in (skill / BILI / "video-card-index.jsonl").read_text().splitlines() if line.strip()]
        ids = {v["bvid"] for v in corpus["videos"]}
        if len(ids) != len(corpus["videos"]) or ids != {c["bvid"] for c in cards}:
            issues.append("corpus-index.json: duplicate-or-mismatched-video-ids")
        for v in corpus["videos"]:
            if not isinstance(v.get("core_evidence_eligible"), bool):
                issues.append("corpus-index.json: missing-evidence-eligibility")
                break
        for card in cards:
            if not all(isinstance(card.get(k), str) for k in ("bvid", "title", "published_at", "core_question", "summary", "transcript_status")):
                issues.append("video-card-index.jsonl: missing-runtime-field")
            if not (skill / BILI / "video-cards" / (card["bvid"] + ".md")).is_file():
                issues.append("video-card-index.jsonl: missing-source-card")
        for name in ("career", "ai-career", "job-evaluation", "personal-brand", "design-product", "business"):
            if not (skill / "references" / f"{name}-framework.md").is_file():
                issues.append(f"{name}-framework.md: missing-runtime-framework")
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        issues.append("source-indexes: invalid-or-missing")
    if sum(f["bytes"] for f in files.values()) > 30 * 1024 * 1024:
        issues.append("package: exceeds-30-MiB-uncompressed-limit")
    return sorted(set(issues))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    if not args.directory.is_dir():
        parser.exit(1, "Release directory does not exist\n")
    result = check(args.directory)
    for finding in result:
        print(finding)
    print(f"{'FAIL' if result else 'PASS'}: {len(result)} release issues")
    raise SystemExit(bool(result))
