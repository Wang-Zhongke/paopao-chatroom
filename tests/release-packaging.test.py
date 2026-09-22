"""Publication-copy regressions: exclusions, source links, hashes and safe output."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("build_release")
check = load("check_release")


class PublicationTests(unittest.TestCase):
    def test_allowlist_excludes_private_inputs(self):
        for name in (".env.local", ".git/config", "node_modules/package/index.js", "public/paopao-avatar.png", "data/rag/index.json", "data/rag/auto-units.json", "data/rag/corpus.jsonl", "data/rag/ingestion-report.json"):
            self.assertFalse(build.source_allowed(Path(name)), name)
        for name in ("references/sources/bilibili/transcripts/clean/BV1234567890.md", "references/sources/articles/bilibili-metadata/raw.json", "references/research/input.json"):
            self.assertFalse(build.skill_allowed(Path(name)), name)
        self.assertTrue(build.source_allowed(Path(".github/workflows/ci.yml")))
        self.assertFalse(build.source_allowed(Path(".github/private.json")))
        self.assertTrue(build.source_allowed(Path("docs/assets/chatroom.png")))
        self.assertFalse(build.source_allowed(Path("docs/assets/personal.png")))
        self.assertTrue(build.source_allowed(Path("scripts/capture-readme.mjs")))
        self.assertTrue(build.source_allowed(Path("data/rag/units.json")))
        self.assertTrue(build.source_allowed(Path("scripts/build-rag.ts")))
        self.assertTrue(build.skill_allowed(Path("references/research/01-writings.md")))
        self.assertTrue(build.skill_allowed(Path("references/sources/bilibili/video-cards/BV1234567890.md")))

    def test_metadata_allowlist_and_link_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            original = base / "original/README.md"
            original.parent.mkdir()
            released = base / "release/README.md"
            released.parent.mkdir()
            text = "[片段](references/transcripts/BV1234567890.md)\n[原始输入](private/input.json)\n"
            original.write_text(text)
            released.write_text(text)
            changes = []
            build.rewrite_links({original: released}, released.parent, changes)
            self.assertIn("https://www.bilibili.com/video/BV1234567890/", released.read_text())
            self.assertIn("仅本地研究环境可用", released.read_text())
            self.assertEqual(original.read_text(), text)
            index_dir = released.parent / build.BILI
            index_dir.mkdir(parents=True)
            (index_dir / "corpus-index.json").write_text(json.dumps({"videos": [{"bvid": "BV1234567890", "core_evidence_eligible": True, "available_tracks": [{"url": "private"}], "unexpected": "private"}]}))
            (index_dir / "video-card-index.jsonl").write_text(json.dumps({"bvid": "BV1234567890", "summary": "note", "raw_response": "private"}) + "\n")
            build.sanitize_indexes(released.parent, changes)
            self.assertNotIn("private", (index_dir / "corpus-index.json").read_text())
            self.assertNotIn("private", (index_dir / "video-card-index.jsonl").read_text())

    def test_nonempty_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            sentinel = Path(tmp) / "keep.txt"
            sentinel.write_text("keep")
            with self.assertRaisesRegex(ValueError, "never overwritten"):
                build.build(Path(tmp).resolve())
            self.assertEqual(sentinel.read_text(), "keep")

    def test_checker_detects_tampering_and_redacts_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "README.md"
            file.write_text("initial")
            build.manifest(root, [], 0, "test")
            secret = "sk-" + "A" * 30
            file.write_text(secret)
            issues = check.check(root)
            self.assertIn("README.md: manifest-mismatch", issues)
            self.assertIn("README.md: api-key", issues)
            self.assertNotIn(secret, "\n".join(issues))


if __name__ == "__main__":
    unittest.main()
