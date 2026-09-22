import { z } from "zod";
import { RAG_CONFIG } from "./config";
export const spanSchema = z
  .tuple([z.number().int().positive(), z.number().int().positive()])
  .refine(([a, b]) => a <= b);
export const entrySchema = z.object({
  id: z.string().regex(/^[a-z0-9-]+$/),
  bvid: z.string().regex(/^BV[a-zA-Z0-9]+$/),
  type: z.enum(["qa_case", "viewpoint", "transcript"]),
  title: z.string().min(1),
  ranges: z.array(spanSchema).min(1),
  questionRanges: z.array(spanSchema).default([]),
  answerRanges: z.array(spanSchema).default([]),
  context: z.string(),
  claim: z.string(),
  topics: z.array(z.string()),
  boundaryNote: z.string(),
  review: z
    .enum([
      "text-boundaries-reviewed-audio-unverified",
      "model-boundaries-audio-unverified",
      "source-card-boundaries-audio-unverified",
    ])
    .default("text-boundaries-reviewed-audio-unverified"),
  transcriptHash: z.string().optional(),
});
export type Entry = z.infer<typeof entrySchema>;
export function parseTranscript(raw: string) {
  const lines = raw.split("\n").flatMap((line) => {
    const m = line.match(/^\[(\d+)\] \[([^–]+)–([^\]]+)\] (.*)$/);
    return m
      ? [
          {
            n: Number(m[1]),
            start: m[2],
            end: m[3],
            text: `[${Number(m[1])}] ${m[4]}`,
          },
        ]
      : [];
  });
  if (!lines.length || lines.some((l, i) => l.n !== i + 1))
    throw new Error("missing-or-nonconsecutive-subtitles");
  return lines;
}
export type Subtitle = ReturnType<typeof parseTranscript>[number];
export function selectLines(lines: Subtitle[], ranges: number[][]) {
  return ranges.flatMap(([a, b]) => {
    const chosen = lines.filter((l) => l.n >= a && l.n <= b);
    if (chosen.length !== b - a + 1)
      throw new Error(`missing-subtitles:${a}-${b}`);
    return chosen;
  });
}
export function validateEntry(entry: Entry, lines: Subtitle[]) {
  const chosen = selectLines(lines, entry.ranges);
  if (chosen.map((l) => l.text).join("\n").length > RAG_CONFIG.maxUnitChars)
    throw new Error("discussion-exceeds-unit-budget");
  const ids = new Set(chosen.map((l) => l.n));
  if (ids.size !== chosen.length) throw new Error("overlapping-ranges");
  if (
    entry.type === "qa_case" &&
    (!entry.questionRanges.length || !entry.answerRanges.length)
  )
    throw new Error("qa-needs-question-and-answer");
  for (const l of selectLines(lines, [
    ...entry.questionRanges,
    ...entry.answerRanges,
  ]))
    if (!ids.has(l.n)) throw new Error("qa-outside-case");
  return chosen;
}
export function validatePartition(entries: Entry[], lines: Subtitle[]) {
  let next = 1;
  for (const entry of entries) {
    if (entry.ranges.length !== 1 || entry.ranges[0][0] !== next)
      throw new Error("partition-gap-or-overlap");
    validateEntry(entry, lines);
    next = entry.ranges[0][1] + 1;
  }
  if (next !== lines.length + 1) throw new Error("partition-incomplete");
}
