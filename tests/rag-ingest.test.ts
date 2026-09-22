import { test } from "node:test";
import assert from "node:assert/strict";
import {
  entrySchema,
  parseTranscript,
  validatePartition,
  validateEntry,
} from "../lib/rag/ingest";
const lines = parseTranscript(
  "[0001] [00:00–00:01] 测试问题\n[0002] [00:01–00:02] 测试回答\n[0003] [00:02–00:03] 第二个观点",
);
const make = (start: number, end: number) =>
  entrySchema.parse({
    id: `test-${start}`,
    bvid: "BVtest123",
    type: "viewpoint",
    title: "合成测试",
    ranges: [[start, end]],
    context: "",
    claim: "",
    topics: [],
    boundaryNote: "",
  });
test("full video annotation must cover each original subtitle exactly once", () => {
  assert.doesNotThrow(() => validatePartition([make(1, 2), make(3, 3)], lines));
  assert.throws(
    () => validatePartition([make(1, 1), make(3, 3)], lines),
    /gap-or-overlap/,
  );
  assert.throws(
    () => validatePartition([make(1, 2), make(2, 3)], lines),
    /gap-or-overlap/,
  );
  assert.throws(() => validatePartition([make(1, 2)], lines), /incomplete/);
  assert.throws(
    () => validatePartition([make(1, 4)], lines),
    /missing-subtitles/,
  );
});
test("QA spans must exist within a complete case; no generated text substitutes for subtitles", () => {
  const qa = {
    ...make(1, 2),
    type: "qa_case" as const,
    questionRanges: [[1, 1]] as [number, number][],
    answerRanges: [[2, 2]] as [number, number][],
  };
  assert.equal(
    validateEntry(qa, lines)
      .map((l) => l.text)
      .join("\n"),
    "[1] 测试问题\n[2] 测试回答",
  );
  assert.throws(
    () => validateEntry({ ...qa, answerRanges: [] }, lines),
    /qa-needs/,
  );
  assert.throws(
    () => validateEntry({ ...qa, answerRanges: [[3, 3]] }, lines),
    /outside/,
  );
  assert.throws(
    () => parseTranscript("[0002] [00:01–00:02] missing start"),
    /nonconsecutive/,
  );
  assert.throws(
    () =>
      validateEntry(make(1, 1), [{ ...lines[0], text: "长".repeat(18001) }]),
    /exceeds/,
  );
});

test("local source-card parser supports citation formats and preserves semantic partitions", async () => {
  const { cardRanges, partitionTranscript } =
    await import("../scripts/prepare-rag");
  assert.deepEqual(
    cardRanges("transcript `[0001] [00:00]`–`[0003] [00:03]`", 3),
    [[1, 3]],
  );
  assert.deepEqual(cardRanges("[0001–0002]；[00:00–00:03，转录 3–3 行]", 3), [
    [1, 2],
    [3, 3],
  ]);
  const large = Array.from({ length: 4 }, (_, i) => ({
    n: i + 1,
    start: "00:00",
    end: "00:01",
    text: `[${i + 1}] ` + "词".repeat(5000),
  }));
  assert.deepEqual(partitionTranscript(large, [3]), [
    [1, 2],
    [3, 4],
  ]);
  assert.throws(
    () => partitionTranscript(large, []),
    /needs-manual-topic-boundary/,
  );
});
