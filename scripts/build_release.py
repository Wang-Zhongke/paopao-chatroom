#!/usr/bin/env python3
"""Build public copies without modifying the local research collection (stdlib only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKILL = "paopao-perspective-skill"
VERSION = "0.1.0"
BILI = "references/sources/bilibili/"
LINK = re.compile(r"(!?)\[([^\]\n]*)\]\((<[^>]+>|[^\s)]+)(?:\s+\"[^\"]*\")?\)")
INDEX_FIELDS = {
    "bvid", "title", "published_at", "duration_seconds", "owner_mid", "owner_name",
    "series_id", "series_name", "url", "transcript_status", "transcript_method",
    "core_evidence_eligible", "evidence_tier", "review_status", "quality_status",
}
CARD_FIELDS = {
    "bvid", "title", "published_at", "url", "transcript_status", "core_question",
    "summary", "candidate_models", "card",
}
SOURCE_ROOT_FILES = {
    "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CONTRIBUTING.md", ".gitignore", ".env.example",
    "package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", "tsconfig.json",
    "next.config.ts", "next-env.d.ts", "playwright.config.ts",
}


def skill_allowed(path: Path) -> bool:
    p = path.as_posix()
    if path.name.startswith(".") or any(x.startswith(".") for x in path.parts):
        return False
    if p in {"SKILL.md", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "agents/openai.yaml"}:
        return True
    if path.parts[0] in {"examples", "tests", "docs"}:
        return path.suffix in {".md", ".json", ".jsonl"}
    if path.parts[0] == "scripts":
        return path.suffix in {".py", ".sh", ".m"}
    if path.parent.as_posix() in {"references", "references/research"}:
        return path.suffix == ".md"
    if p.startswith(BILI + "video-cards/"):
        return path.suffix == ".md"
    return p in {
        BILI + "README.md", BILI + "corpus-report.md", BILI + "manual-transcript-review.md",
        BILI + "transcript-qa.md", BILI + "video-card-index.md",
        BILI + "video-card-index.jsonl", BILI + "corpus-index.json",
    }


def source_allowed(path: Path) -> bool:
    if path.as_posix() == ".github/workflows/ci.yml":
        return True
    if path.as_posix() in SOURCE_ROOT_FILES:
        return True
    if any(x.startswith(".") for x in path.parts):
        return False
    if path.parts[0] in {"app", "lib"}:
        return path.suffix in {".ts", ".tsx", ".css"}
    if path.parts[0] == "public":
        return path.suffix == ".svg"
    if path.parts[0] == "docs":
        return path.suffix == ".md" or path.as_posix() == "docs/assets/chatroom.png"
    if path.parts[0] == "tests":
        return path.suffix in {".ts", ".py"}
    if path.as_posix() == "data/rag/units.json":
        return True
    if path.parts[0] == "scripts":
        return path.name in {"build_release.py", "check_release.py", "eval_release.py", "build-rag.ts", "prepare-rag.ts", "debug-rag.ts", "eval-rag.ts", "eval-rag-full.ts", "capture-readme.mjs"}
    return False


def selected_files(root: Path, allowed):
    # Traverse only explicit top-level directories; never crawl .git or node_modules.
    for entry in sorted(root.iterdir()):
        if entry.is_symlink():
            if allowed(Path(entry.name)):
                raise ValueError(f"Symlink rejected: {entry.relative_to(root)}")
            continue
        if entry.is_file():
            if allowed(Path(entry.name)):
                yield entry
        elif entry.name in {".github", "agents", "references", "examples", "tests", "docs", "scripts", "app", "lib", "public", "data"}:
            for child in sorted(entry.rglob("*")):
                relative = child.relative_to(root)
                if allowed(relative) and child.is_symlink():
                    raise ValueError(f"Symlink rejected: {relative}")
                if child.is_file() and allowed(relative):
                    if any(p.is_symlink() for p in child.parents if p != root and root in p.parents):
                        raise ValueError(f"Symlink ancestor rejected: {relative}")
                    yield child


def copy_files(root: Path, destination: Path, allowed):
    mappings = {}
    for source in selected_files(root, allowed):
        target = destination / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        mappings[source.resolve()] = target
    return mappings


def sanitize_indexes(destination: Path, changes: list):
    index = destination / BILI / "corpus-index.json"
    raw = json.loads(index.read_text())
    clean = {
        "generated_at": raw.get("generated_at"),
        "account_mid": raw.get("account_mid"),
        "video_count": len(raw["videos"]),
        "distribution": "Public metadata and evidence eligibility only; transcripts are local research inputs, not included.",
        "videos": [{k: v for k, v in video.items() if k in INDEX_FIELDS} for video in raw["videos"]],
    }
    index.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n")
    changes.append({"file": BILI + "corpus-index.json", "operation": "strict public metadata field allowlist; removed raw API/track URLs"})
    card_index = destination / BILI / "video-card-index.jsonl"
    cards = [json.loads(line) for line in card_index.read_text().splitlines() if line.strip()]
    card_index.write_text("".join(json.dumps({k: v for k, v in card.items() if k in CARD_FIELDS}, ensure_ascii=False) + "\n" for card in cards))
    changes.append({"file": BILI + "video-card-index.jsonl", "operation": "strict source-card field allowlist"})
    return len(raw["videos"])


def rewrite_links(mappings: dict[Path, Path], package: Path, changes: list):
    import os
    for original, published in mappings.items():
        if published.suffix != ".md":
            continue
        value = published.read_text()
        count = 0

        def replacement(match):
            nonlocal count
            image, label, raw = match.groups()
            href = raw.strip("<>")
            if href.startswith("#") or urlsplit(href).scheme or href.startswith("//"):
                return match.group(0)
            target_name, _, fragment = unquote(href).partition("#")
            # Codex's absolute local file links sometimes carry :line suffixes.
            target_name = re.sub(r":\d+$", "", target_name)
            original_target = (original.parent / target_name).resolve()
            copied_target = mappings.get(original_target)
            if copied_target is None:
                candidate = (published.parent / target_name).resolve()
                if candidate.is_relative_to(package.resolve()) and candidate.exists():
                    copied_target = candidate
            if copied_target is not None:
                relative = os.path.relpath(copied_target, published.parent).replace(os.sep, "/")
                if fragment:
                    relative += "#" + fragment
                result = f"{image}[{label}](<{relative}>)" if " " in relative else f"{image}[{label}]({relative})"
            else:
                bvid = re.search(r"BV[a-zA-Z0-9]{10}", target_name)
                if bvid:
                    result = f"[{label}](https://www.bilibili.com/video/{bvid.group()}/)"
                else:
                    result = f"{label}（仅本地研究环境可用；公开包不含此文件）"
            if result != match.group(0):
                count += 1
            return result

        rewritten = LINK.sub(replacement, value)
        if count:
            published.write_text(rewritten)
            changes.append({"file": published.relative_to(package).as_posix(), "operation": "rewrite local links to distributed files or public video; label excluded research", "count": count})


def manifest(package: Path, changes: list, video_count: int, kind: str):
    records = []
    for item in sorted(package.rglob("*")):
        if item.is_file():
            data = item.read_bytes()
            records.append({"path": item.relative_to(package).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    payload = {
        "version": VERSION, "kind": kind,
        "research_video_count": video_count,
        "full_transcripts_distributed": False,
        "distribution_note": "Original local research includes machine text; this public copy contains frameworks, original research notes, source cards and public metadata, not complete transcripts, raw OCR or API responses.",
        "transformations": changes, "files": records,
    }
    (package / "MANIFEST.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def zip_package(package: Path, output: Path):
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(package.rglob("*")):
            if item.is_file():
                archive.write(item, Path(package.name) / item.relative_to(package))


def build(output: Path):
    if not output.is_absolute():
        raise ValueError("--output must be an explicit absolute directory")
    if output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError("Output may not use symlinks")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output must be absent or empty; existing content is never overwritten")
    for base in (ROOT, ROOT / SKILL):
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            if not (base / name).is_file():
                raise ValueError(f"Required publication document missing: {base.relative_to(ROOT) / name}")
    output.mkdir(parents=True, exist_ok=True)
    lite = output / SKILL
    lite_map = copy_files(ROOT / SKILL, lite, skill_allowed)
    # A standalone Skill carries only its own installation/research docs.
    # Application maintenance instructions belong to the full source package.
    changes = []
    count = sanitize_indexes(lite, changes)
    rewrite_links(lite_map, lite, changes)
    manifest(lite, changes, count, "skill")

    source = output / "paopao-room"
    mappings = copy_files(ROOT, source, source_allowed)
    nested = source / SKILL
    nested_map = copy_files(ROOT / SKILL, nested, skill_allowed)
    mappings.update(nested_map)
    source_changes = []
    sanitize_indexes(nested, source_changes)
    for change in source_changes:
        change["file"] = SKILL + "/" + change["file"]
    page = source / "app/page.tsx"
    if page.exists() and "/paopao-avatar.png" in page.read_text():
        if not (source / "public/paopao-mark.svg").is_file():
            raise ValueError("public/paopao-mark.svg is required to replace excluded portrait")
        page.write_text(page.read_text().replace("/paopao-avatar.png", "/paopao-mark.svg"))
        source_changes.append({"file": "app/page.tsx", "operation": "replace local portrait with original abstract SVG mark"})
    rewrite_links(mappings, source, source_changes)
    manifest(source, source_changes, count, "application-source")
    from check_release import check
    for directory in (lite, source):
        issues = check(directory)
        if issues:
            for issue in issues:
                print(issue, file=sys.stderr)
            raise ValueError("Release validation failed; no ZIPs created. Inspect the output copies.")
    zip_package(lite, output / f"{SKILL}-v{VERSION}.zip")
    zip_package(source, output / f"paopao-room-source-v{VERSION}.zip")
    print(f"Built and verified: {output}")
    print(f"Research coverage: {count} videos. Public distribution: source cards + research notes + metadata; 0 full transcripts.")
    print("Original workspace research files were not modified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    try:
        build(options.output)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"Build failed: {error}\n")
