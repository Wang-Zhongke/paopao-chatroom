/** Local-only ingestion. No provider imports, network calls or API key needed. */
import { readFile, writeFile, mkdir, rename } from "node:fs/promises";
import { createHash } from "node:crypto";
import {
  entrySchema,
  parseTranscript,
  validateEntry,
  validatePartition,
  type Entry,
  type Subtitle,
} from "../lib/rag/ingest";
import { RAG_CONFIG, getTopics } from "../lib/rag/config";
const root = "paopao-perspective-skill/references/sources/bilibili";
const hash = (s: string) => createHash("sha256").update(s).digest("hex");
const section = (card: string, name: string) =>
  card.split(`## ${name}`)[1]?.split(/\n## /)[0]?.trim() || "";
const plain = (s: string) => s.replace(/[*`]/g, "").trim();
async function atomic(file: string, value: unknown) {
  const tmp = `${file}.${process.pid}.tmp`;
  await writeFile(tmp, JSON.stringify(value, null, 2));
  await rename(tmp, file);
}
// Source cards use both [0010–0040] and [0010] [00:10]–[0040] [01:00].
export function cardRanges(text: string, last: number): [number, number][] {
  const found: [number, number][] = [];
  const pattern =
    /\[(\d{3,5})\s*[–—-]\s*(\d{3,5})\]|\[(\d{3,5})\](?:\s*\[[\d:.]+\])?\s*[–—-]\s*`?\[(\d{3,5})\]|\[(\d{3,5})\]/g;
  for (const m of text.replace(/`/g, "").matchAll(pattern)) {
    const a = Number(m[1] || m[3] || m[5]),
      b = Number(m[2] || m[4] || m[5]);
    if (a >= 1 && b >= a && b <= last) found.push([a, b]);
  }
  for (const m of text.matchAll(
    /(?:转录|字幕)\s*(\d+)\s*[–—-]\s*(\d+)\s*行/g,
  )) {
    const a = Number(m[1]),
      b = Number(m[2]);
    if (a >= 1 && b >= a && b <= last) found.push([a, b]);
  }
  return found;
}
export function partitionTranscript(lines: Subtitle[], anchors: number[]) {
  const starts = new Set([
    1,
    ...anchors.filter((n) => n > 1 && n <= lines.length),
  ]);
  // Explicit discourse transitions are only fallback boundaries, never fixed token cuts.
  for (const l of lines)
    if (
      /(?:接下来(?:我们|咱们|我|说|讲)|下一个(?:问题|话题)|(?:第[一二三四五六七八九十]+个)(?:问题|话题|方面)|换一个(?:问题|话题)|再说一个|然后我们来|我们再来看|那我们来|回到(?:刚才|这个)|总结一下)/.test(
        l.text,
      )
    )
      starts.add(l.n);
  const candidates = [...starts].sort((a, b) => a - b);
  const result: [number, number][] = [];
  let start = 1;
  while (start <= lines.length) {
    if (
      lines
        .slice(start - 1)
        .map((l) => l.text)
        .join("\n").length <= RAG_CONFIG.maxUnitChars
    ) {
      result.push([start, lines.length]);
      break;
    }
    // Select the furthest existing semantic boundary that fits, not a character cut.
    const next = candidates
      .filter(
        (n) =>
          n > start &&
          lines
            .slice(start - 1, n - 1)
            .map((l) => l.text)
            .join("\n").length <= RAG_CONFIG.maxUnitChars,
      )
      .at(-1);
    if (!next) throw new Error(`needs-manual-topic-boundary-at-${start}`);
    result.push([start, next - 1]);
    start = next;
  }
  return result;
}
export async function prepareRag() {
  const videos = JSON.parse(await readFile(`${root}/corpus-index.json`, "utf8"))
    .videos as {
    bvid: string;
    title: string;
    core_evidence_eligible: boolean;
    transcript_status: string;
    transcript_qa_flags?: string;
  }[];
  const archive: string[] = [],
    entries: Entry[] = [],
    records: Record<string, unknown>[] = [];
  await mkdir("data/rag", { recursive: true });
  for (const meta of videos) {
    try {
      const raw = await readFile(
          `${root}/transcripts/clean/${meta.bvid}.md`,
          "utf8",
        ),
        transcriptHash = hash(raw);
      const lines = parseTranscript(raw);
      archive.push(JSON.stringify({ ...meta, transcriptHash, raw }));
      if (!meta.core_evidence_eligible) {
        records.push({
          bvid: meta.bvid,
          status: "quarantined-quality",
          subtitles: lines.length,
          reason: meta.transcript_qa_flags || "weak-evidence",
        });
        continue;
      }
      const card = await readFile(
        `${root}/video-cards/${meta.bvid}.md`,
        "utf8",
      );
      const discussion = section(card, "主要判断与推理");
      const blocks = discussion
        .split(/\n(?=\d+[.、]\s)/)
        .filter((b) => /^\d+[.、]\s/.test(b.trim()));
      const claims = blocks.flatMap((block, i) => {
        const evidence = block;
        const spans = cardRanges(evidence, lines.length);
        const bold = block.match(/\*\*([^*]+)\*\*/)?.[1];
        const claim = plain(
          bold && !/^判断/.test(bold) ? bold : block.split("\n")[0],
        )
          .replace(/^\d+[.、]\s*/, "")
          .replace(/^判断[（(]转述[）)][:：]?\s*/, "");
        return spans.length && claim ? [{ i, claim, spans }] : [];
      });
      const base = {
        bvid: meta.bvid,
        questionRanges: [],
        answerRanges: [],
        review: "source-card-boundaries-audio-unverified",
        transcriptHash,
      };
      // Codex checked subtitles 1618–1692: [1674] explicitly introduces a new example.
      const extraBoundaries = meta.bvid === "BV1Mn6NYKEBe" ? [1674] : [];
      const full = partitionTranscript(lines, [
        ...claims.flatMap((c) => c.spans.map((s) => s[0])),
        ...extraBoundaries,
      ]).map(([a, b], i) =>
        entrySchema.parse({
          ...base,
          id: `full-${meta.bvid.toLowerCase()}-${i + 1}`,
          type: "transcript",
          title: meta.title,
          ranges: [[a, b]],
          claim: "",
          context: `${a === 1 && b === lines.length ? `视频议题（来源卡转述）：${section(card, "核心问题")}。` : ""}本单元为${a === 1 && b === lines.length ? "完整视频原文" : "长视频的原始讨论子段，不能当作独立完整连麦"}；说话人未逐句分离。`,
          topics: getTopics(meta.title + section(card, "核心问题")),
          boundaryNote:
            "本地按既有来源卡议题起点和明确话题转折整理；片段可能包含来电者、第三方播放和宣传，不应将全部第一人称归于泡泡。需核对正文再归因，未重新逐句人工/音视频校验。",
        }),
      );
      validatePartition(full, lines);
      entries.push(...full);
      let added = 0;
      const skippedClaims: string[] = [];
      for (const c of claims) {
        const a = Math.min(...c.spans.map((s) => s[0])),
          b = Math.max(...c.spans.map((s) => s[1]));
        // Keep the continuous discussion between all references for a claim, not stitched quotes.
        const entry = entrySchema.parse({
          ...base,
          id: `card-${meta.bvid.toLowerCase()}-${c.i + 1}`,
          type: "viewpoint",
          title: c.claim,
          claim: c.claim,
          ranges: [[a, b]],
          context:
            "既有研究来源卡的判断转述，仅用于定位；正文保留该判断首尾引用之间的连续字幕，可能含双方发言，不能把转述当原话。",
          topics: getTopics(meta.title + c.claim),
          boundaryNote:
            "来源卡范围自动核对编号，不代表重新人工审核语义或说话人；先核对字幕是否直接支持当前问题。",
        });
        try {
          validateEntry(entry, lines);
          entries.push(entry);
          added++;
        } catch (e) {
          skippedClaims.push(
            `${c.i + 1}:${e instanceof Error ? e.message : "invalid"}`,
          );
        }
      }
      records.push({
        bvid: meta.bvid,
        status: "indexed",
        subtitles: lines.length,
        contentChars: lines.map((l) => l.text).join("\n").length,
        fullUnits: full.length,
        viewpoints: added,
        skippedClaims,
        transcriptHash,
        cardHash: hash(card),
      });
    } catch (e) {
      records.push({
        bvid: meta.bvid,
        status: "failed",
        reason: e instanceof Error ? e.message : "failed",
      });
    }
  }
  const summary = {
    version: "local-source-cards-v1",
    generatedAt: new Date().toISOString(),
    total: videos.length,
    archived: archive.length,
    searchable: records.filter((r) => r.status === "indexed").length,
    quarantined: records.filter((r) => r.status === "quarantined-quality")
      .length,
    failed: records.filter((r) => r.status === "failed"),
    units: entries.length,
    records,
  };
  await atomic("data/rag/ingestion-report.json", summary);
  await writeFile("data/rag/corpus.jsonl.tmp", archive.join("\n") + "\n");
  await rename("data/rag/corpus.jsonl.tmp", "data/rag/corpus.jsonl");
  if (summary.failed.length) throw new Error(JSON.stringify(summary.failed));
  await atomic("data/rag/auto-units.json", entries);
  console.log(JSON.stringify({ ...summary, records: undefined }, null, 2));
}
if (process.argv[1]?.endsWith("prepare-rag.ts"))
  prepareRag().catch((e) => {
    console.error(e.message);
    process.exitCode = 1;
  });
