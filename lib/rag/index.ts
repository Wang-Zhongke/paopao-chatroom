import { z } from "zod";
import { RAG_CONFIG } from "./config";
const range = z.tuple([
  z.number().int().positive(),
  z.number().int().positive(),
]);
export const unitSchema = z.object({
  id: z.string(),
  type: z.enum(["qa_case", "viewpoint", "transcript"]),
  title: z.string(),
  question: z.string(),
  context: z.string(),
  answer: z.string(),
  claim: z.string(),
  content: z.string().min(1).max(RAG_CONFIG.maxUnitChars),
  topics: z.array(z.string()),
  annotations: z.literal("editorial-paraphrase-not-quotation"),
  source: z.object({
    id: z.string().regex(/^BV[a-zA-Z0-9]+$/),
    title: z.string(),
    date: z.string(),
    quality: z.enum(["machine-subtitle", "machine-ocr"]),
    transcript: z.string(),
    transcriptHash: z.string(),
    ranges: z.array(range).min(1),
    start: z.string(),
    end: z.string(),
    questionRanges: z.array(range),
    answerRanges: z.array(range),
    limitations: z.string(),
    review: z.enum([
      "text-boundaries-reviewed-audio-unverified",
      "model-boundaries-audio-unverified",
      "source-card-boundaries-audio-unverified",
    ]),
  }),
});
export type Unit = z.infer<typeof unitSchema>;
export const indexSchema = z.object({
  version: z.literal(1),
  digest: z.string(),
  builtAt: z.string(),
  documents: z.array(
    z.object({
      unit: unitSchema,
      terms: z.record(z.number()),
      length: z.number().positive(),
    }),
  ),
  df: z.record(z.number()),
  averageLength: z.number().nonnegative(),
});
export type RagIndex = z.infer<typeof indexSchema>;
const stop = new Set(
  "什么 怎么 为什么 现在 一个 自己 觉得 可以 没有 但是 一直 最近 应该 老师 泡泡 之前 以前 说过 讲过 这个 那个 这种 有没有 到底 关于 请问 如何 这是 观点 根据 依据 其实 然后 因为 所以 我们 你们 他们 能够 不要 时候 认为 有用 比较 怎么办 想要 一下 先做 已经 还是 可能".split(
    " ",
  ),
);
const segmenter = new Intl.Segmenter("zh-CN", { granularity: "word" });
export function tokenize(text: string): string[] {
  return [...segmenter.segment(text.toLowerCase())]
    .filter((s) => s.isWordLike)
    .flatMap(({ segment: word }) => {
      if (stop.has(word) || /^[零一二三四五六七八九十百0-9]+年$/.test(word))
        return [];
      if (/^[a-z][a-z0-9_]+$/.test(word)) return [word];
      if (!/^[\u4e00-\u9fff]{2,}$/.test(word)) return [];
      return word.length > 2
        ? [
            word,
            ...Array.from({ length: word.length - 1 }, (_, i) =>
              word.slice(i, i + 2),
            ).filter((t) => !stop.has(t)),
          ]
        : [word];
    });
}
export function searchText(u: Unit) {
  return [u.title, u.source.title, u.question, u.claim, u.context].join("\n");
}
export function createIndex(units: Unit[], digest: string): RagIndex {
  const df: Record<string, number> = {};
  const documents = units.map((unit) => {
    // Metadata directs discovery; the returned evidence remains the original transcript.
    const terms: Record<string, number> = {};
    for (const token of tokenize(
      searchText(unit) +
        "\n" +
        searchText(unit) +
        "\n" +
        unit.content.replace(/\[.*?\]/g, ""),
    ))
      terms[token] = (terms[token] || 0) + 1;
    for (const token of Object.keys(terms)) df[token] = (df[token] || 0) + 1;
    return {
      unit,
      terms,
      length: Object.values(terms).reduce((a, b) => a + b, 0),
    };
  });
  return {
    version: 1,
    digest,
    builtAt: new Date().toISOString(),
    documents,
    df,
    averageLength:
      documents.reduce((n, d) => n + d.length, 0) / (documents.length || 1),
  };
}
