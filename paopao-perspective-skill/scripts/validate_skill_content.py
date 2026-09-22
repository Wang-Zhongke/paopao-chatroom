#!/usr/bin/env python3
"""Repository-level checks for the Paopao perspective skill."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "SKILL.md",
    "agents/openai.yaml",
    "references/mental-models.md",
    "references/career-framework.md",
    "references/ai-career-framework.md",
    "references/job-evaluation-framework.md",
    "references/business-framework.md",
    "references/personal-brand-framework.md",
    "references/design-product-framework.md",
    "references/expression-dna.md",
    "references/timeline.md",
    "references/source-map.md",
    "examples/career-decision.md",
    "examples/job-evaluation.md",
    "examples/ai-product-career.md",
    "tests/voice-fidelity-v2.md",
    "tests/voice-v2-results.md",
]


def report(label: str, passed: bool, detail: str) -> bool:
    print(f"{'PASS' if passed else 'FAIL'}  {label}: {detail}")
    return passed


def main() -> int:
    checks = []
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    checks.append(report("required files", not missing, "none missing" if not missing else ", ".join(missing)))

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    model_block = skill.split("## 核心心智模型", 1)[-1].split("\n## ", 1)[0]
    models = re.findall(r"^### M\d+｜", model_block, flags=re.MULTILINE)
    checks.append(report("mental model count", 3 <= len(models) <= 7, str(len(models))))

    model_sections = re.split(r"(?=^### M\d+｜)", model_block, flags=re.MULTILINE)[1:]
    model_fields_ok = all(all(field in section for field in ("证据：", "使用：", "局限：", "状态：")) for section in model_sections)
    checks.append(report("model fields", model_fields_ok, "each has evidence/use/limit/status"))

    heur_block = skill.split("## Decision Heuristics", 1)[-1].split("\n## ", 1)[0]
    heuristics = re.findall(r"^\d+\. \*\*", heur_block, flags=re.MULTILINE)
    checks.append(report("heuristic count", 5 <= len(heuristics) <= 10, str(len(heuristics))))

    required_sections = [
        "Identity / Scope", "Expression DNA", "Values", "Anti-patterns",
        "Career Decision Framework", "AI-era Career Framework",
        "Job Evaluation Framework", "Personal Brand Framework",
        "Design / Product Framework", "诚实边界", "Source Map", "Tests",
    ]
    absent_sections = [section for section in required_sections if section not in skill]
    checks.append(report("required sections", not absent_sections, "complete" if not absent_sections else ", ".join(absent_sections)))

    fidelity_ok = all(phrase in skill for phrase in (
        "默认用“我”回应",
        "没有直接公开答案的问题",
        "不把没说过的话放进引号",
        "同名材料不用",
    ))
    checks.append(report("perspective fidelity", fidelity_ok, "immersive voice and minimum source discipline present"))

    broken = []
    for md in ROOT.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "#")):
                continue
            target_path = target.split("#", 1)[0]
            if target_path and not (md.parent / target_path).resolve().exists():
                broken.append(f"{md.relative_to(ROOT)} -> {target_path}")
    checks.append(report("local links", not broken, "all resolve" if not broken else "; ".join(broken[:8])))

    research_files = list((ROOT / "references/research").glob("0[1-6]-*.md"))
    checks.append(report("Nuwa research dimensions", len(research_files) == 6, str(len(research_files))))

    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
