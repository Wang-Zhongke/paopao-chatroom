import assert from "node:assert/strict";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import { loadIndex, retrieve } from "../lib/rag/retrieve";
import { parseTranscript, selectLines } from "../lib/rag/ingest";
import { RAG_CONFIG, ragSettings } from "../lib/rag/config";
const root = "paopao-perspective-skill/references/sources/bilibili";
async function main() {
  const start = performance.now();
  const index = await loadIndex(ragSettings().indexPath);
  const loadMs = performance.now() - start;
  const videos = JSON.parse(await readFile(`${root}/corpus-index.json`, "utf8"))
    .videos as { bvid: string; core_evidence_eligible: boolean }[];
  const docs = index.documents.map((d) => d.unit);
  let subtitles = 0,
    contentChars = 0;
  for (const video of videos) {
    const units = docs.filter((u) => u.source.id === video.bvid);
    if (!video.core_evidence_eligible) {
      assert.equal(units.length, 0);
      continue;
    }
    const raw = await readFile(
      `${root}/transcripts/clean/${video.bvid}.md`,
      "utf8",
    );
    const lines = parseTranscript(raw),
      hash = createHash("sha256").update(raw).digest("hex");
    const full = units
      .filter((u) => u.id.startsWith("full-"))
      .sort((a, b) => a.source.ranges[0][0] - b.source.ranges[0][0]);
    assert.ok(full.length, video.bvid);
    let next = 1;
    for (const u of full) {
      assert.equal(u.source.ranges[0][0], next);
      next = u.source.ranges[0][1] + 1;
    }
    assert.equal(next, lines.length + 1, video.bvid);
    for (const u of units) {
      assert.equal(u.source.transcriptHash, hash);
      assert.equal(
        u.content,
        selectLines(lines, u.source.ranges)
          .map((l) => l.text)
          .join("\n"),
      );
      assert.ok(u.content.length <= RAG_CONFIG.maxUnitChars);
    }
    subtitles += lines.length;
    contentChars += lines.map((l) => l.text).join("\n").length;
  }
  const cases: [string, string | null][] = [
    ["泡泡如何看待个人生产资料的控制权和可迁移性？", "BV1Mn6NYKEBe"],
    ["泡泡讲过不靠意志力而靠环境和承诺机制坚持深度学习吗？", "BV1w2d8BfEuY"],
    ["泡泡为什么认为伟大不能被计划，要靠新颖性探索？", "BV1Gr5gzKEh2"],
    ["泡泡怎么看视频剪辑的真实采购需求和完整交付？", "BV1sxTv6ZEbg"],
    ["泡泡讲过以教代学为什么能暴露知识缺口吗？", "BV1t9ZHYbEam"],
    ["泡泡怎么看困难模式与风口带来的个人能力错觉？", "BV1QnJJzuEpR"],
    ["泡泡以前说过月球土豆量子纠缠的创业工艺吗？", null],
    ["今天好累", null],
  ];
  const results = [];
  for (const [query, expectedSource] of cases) {
    const t = performance.now(),
      r = await retrieve(query, [], { enabled: true, log: false });
    const sources = r.evidence.map((h) => h.unit.source.id);
    const pass = expectedSource
      ? sources.includes(expectedSource)
      : sources.length === 0;
    const chars = r.evidence.reduce(
      (n, h) => n + JSON.stringify(h.unit).length,
      0,
    );
    assert.ok(chars <= RAG_CONFIG.maxContextChars);
    assert.ok(r.evidence.length <= RAG_CONFIG.maxEvidence);
    for (let i = 0; i < r.evidence.length; i++)
      for (let j = 0; j < i; j++) {
        const a = r.evidence[i].unit.source,
          b = r.evidence[j].unit.source;
        if (a.id === b.id)
          assert.ok(
            !a.ranges.some(([x, y]) =>
              b.ranges.some(([m, n]) => x <= n && m <= y),
            ),
          );
      }
    results.push({
      query,
      expectedSource,
      pass,
      sources,
      units: r.evidence.map((h) => h.unit.id),
      chars,
      elapsedMs: performance.now() - t,
    });
  }
  const report = {
    date: new Date().toISOString(),
    digest: index.digest,
    loadMs,
    sources: new Set(docs.map((u) => u.source.id)).size,
    documents: docs.length,
    subtitles,
    contentChars,
    results,
  };
  await mkdir(".local-archive/persona-rag", { recursive: true });
  await writeFile(
    ".local-archive/persona-rag/full-eval-latest.json",
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report, null, 2));
  assert.ok(
    results.every((r) => r.pass),
    "retrieval regression failed",
  );
}
main().catch((e) => {
  console.error(e.message);
  process.exitCode = 1;
});
