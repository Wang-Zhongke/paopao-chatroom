import { readFile, writeFile, mkdir, rename } from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { z } from "zod";
import {
  entrySchema,
  parseTranscript,
  validateEntry,
  selectLines,
} from "../lib/rag/ingest";
import { createIndex, unitSchema, type Unit } from "../lib/rag/index";
import { RAG_CONFIG, ragSettings } from "../lib/rag/config";
const root = process.cwd();
const sourceRoot = path.join(
  root,
  "paopao-perspective-skill/references/sources/bilibili",
);
export async function buildRag() {
  const manifestText = await readFile(
    path.join(root, "data/rag/units.json"),
    "utf8",
  );
  let autoText = "[]";
  try {
    autoText = await readFile(
      path.join(root, "data/rag/auto-units.json"),
      "utf8",
    );
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code !== "ENOENT") throw e;
  }
  const entries = z
    .array(entrySchema)
    .parse([...JSON.parse(manifestText), ...JSON.parse(autoText)]);
  if (new Set(entries.map((e) => e.id)).size !== entries.length)
    throw new Error("Duplicate unit IDs");
  const corpus = JSON.parse(
    await readFile(path.join(sourceRoot, "corpus-index.json"), "utf8"),
  ).videos as {
    bvid: string;
    core_evidence_eligible: boolean;
    title: string;
    published_at: string;
    transcript_status: string;
  }[];
  const units: Unit[] = [];
  const skipped: { id: string; reason: string }[] = [];
  const digest = createHash("sha256")
    .update(RAG_CONFIG.version)
    .update(manifestText)
    .update(autoText)
    .update(await readFile(path.join(root, "lib/rag/index.ts")))
    .update(await readFile(path.join(root, "lib/rag/config.ts")));
  for (const entry of entries) {
    const meta = corpus.find((v) => v.bvid === entry.bvid);
    if (!meta?.core_evidence_eligible) {
      skipped.push({ id: entry.id, reason: "not-evidence-eligible" });
      continue;
    }
    const transcriptPath = `paopao-perspective-skill/references/sources/bilibili/transcripts/clean/${entry.bvid}.md`;
    let raw: string;
    try {
      raw = await readFile(path.join(root, transcriptPath), "utf8");
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code === "ENOENT") {
        skipped.push({ id: entry.id, reason: "missing-raw-transcript" });
        continue;
      }
      throw e;
    }
    const hash = createHash("sha256").update(raw).digest("hex");
    if (entry.transcriptHash && entry.transcriptHash !== hash)
      throw new Error(`${entry.id}: stale annotation; prepare again`);
    const lines = parseTranscript(raw);
    const select = (ranges: number[][]) => selectLines(lines, ranges);
    const chosen = validateEntry(entry, lines);
    const content = chosen.map((l) => l.text).join("\n");
    const card = await readFile(
      path.join(sourceRoot, `video-cards/${entry.bvid}.md`),
      "utf8",
    );
    const limitations =
      card.split("## 证据限制")[1]?.split("\n## ")[0]?.trim() ||
      "机器文本未人工逐句校正。";
    digest.update(hash).update(JSON.stringify(meta)).update(limitations);
    units.push(
      unitSchema.parse({
        id: entry.id,
        type: entry.type,
        title: entry.title,
        claim: entry.claim,
        context: entry.context,
        question: select(entry.questionRanges)
          .map((l) => l.text)
          .join("\n"),
        answer: select(entry.answerRanges)
          .map((l) => l.text)
          .join("\n"),
        content,
        topics: entry.topics,
        annotations: "editorial-paraphrase-not-quotation",
        source: {
          id: entry.bvid,
          title: meta.title,
          date: meta.published_at.slice(0, 10),
          quality: meta.transcript_status.includes("ocr")
            ? "machine-ocr"
            : "machine-subtitle",
          transcript: transcriptPath,
          transcriptHash: hash,
          ranges: entry.ranges,
          start: chosen[0].start,
          end: chosen.at(-1)!.end,
          questionRanges: entry.questionRanges,
          answerRanges: entry.answerRanges,
          limitations: entry.boundaryNote + "\n" + limitations,
          review: entry.review,
        },
      }),
    );
  }
  const index = createIndex(units, digest.digest("hex"));
  const output = ragSettings().indexPath;
  await mkdir(path.dirname(output), { recursive: true });
  const tmp = output + `.${process.pid}.tmp`;
  const serialized = JSON.stringify(index);
  if (Buffer.byteLength(serialized) > RAG_CONFIG.maxIndexBytes)
    throw new Error("index-exceeds-loader-budget");
  await writeFile(tmp, serialized);
  await rename(tmp, output);
  console.log(
    JSON.stringify(
      {
        output,
        documents: units.length,
        sources: new Set(units.map((u) => u.source.id)).size,
        bytes: Buffer.byteLength(serialized),
        transcript: units.filter((u) => u.type === "transcript").length,
        qa_case: units.filter((u) => u.type === "qa_case").length,
        viewpoint: units.filter((u) => u.type === "viewpoint").length,
        skipped,
        digest: index.digest,
      },
      null,
      2,
    ),
  );
  return index;
}
if (process.argv[1]?.endsWith("build-rag.ts"))
  buildRag().catch((e) => {
    console.error(e.message);
    process.exitCode = 1;
  });
