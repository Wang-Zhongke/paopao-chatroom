import { mkdir, writeFile } from "node:fs/promises";
import { buildContext } from "../lib/context";
import { completion } from "../lib/server";
import { readSSE } from "../lib/sse";
const cases = [
  {
    id: 1,
    name: "明确历史观点",
    query: "泡泡以前讲过输出型学习吗？他为什么认为输出有用？请给出来源。",
    enabled: true,
    expected: "output-learning",
  },
  {
    id: 2,
    name: "相似场景",
    query: "我做了五年运营，想转 AI 产品，先做什么项目比较好？",
    enabled: true,
    expected: "ai-pm-projects",
  },
  {
    id: 3,
    name: "知识库外",
    query: "解释一下量子纠缠，为什么它不能用来超光速通信？",
    enabled: true,
    expected: null,
  },
  { id: 4, name: "普通聊天", query: "今天好累", enabled: true, expected: null },
  {
    id: 5,
    name: "关闭 RAG",
    query: "我做了五年运营，想转 AI 产品，先做什么项目比较好？",
    enabled: false,
    expected: null,
  },
];
async function main() {
  const live = process.argv.includes("--live");
  if (live && !process.env.DEEPSEEK_API_KEY)
    throw new Error("DEEPSEEK_API_KEY is required for --live");
  const results = [];
  for (const c of cases) {
    const context = await buildContext(c.query, [], {
      enabled: c.enabled,
      log: false,
    });
    const selected = context.rag.retrieved_sources
      .filter((s) => s.selected)
      .map((s) => s.id);
    const retrievalPass = c.expected
      ? selected.includes(c.expected)
      : selected.length === 0;
    let answer = "",
      error = "",
      complete = false;
    const start = Date.now();
    if (live) {
      try {
        const res = await completion(
          [
            { role: "system", content: context.system },
            { role: "user", content: c.query },
          ],
          AbortSignal.timeout(120000),
          true,
        );
        for await (const data of readSSE(res.body!)) {
          if (data === "[DONE]") break;
          const chunk = JSON.parse(data);
          answer += chunk.choices?.[0]?.delta?.content || "";
          if (chunk.choices?.[0]?.finish_reason === "stop") complete = true;
        }
        if (!complete) error = "incomplete";
      } catch {
        error = "generation-failed";
      }
    }
    const row = {
      ...c,
      trace: context.rag,
      retrievalPass,
      live,
      answer,
      error,
      complete,
      elapsedMs: Date.now() - start,
    };
    results.push(row);
    console.log(
      JSON.stringify({
        id: c.id,
        selected,
        reason: context.rag.reason,
        retrievalPass,
        live,
        complete,
        error,
      }),
    );
  }
  await mkdir(".local-archive/persona-rag", { recursive: true });
  const output = `.local-archive/persona-rag/${live ? "live" : "retrieval"}-latest.json`;
  await writeFile(
    output,
    JSON.stringify(
      {
        date: new Date().toISOString(),
        model: live ? "deepseek-flash" : null,
        results,
      },
      null,
      2,
    ),
  );
  console.log(`Results: ${output}`);
  if (
    results.some(
      (r) => !r.retrievalPass || (live && (!r.complete || !r.answer)),
    )
  )
    process.exitCode = 1;
}
main().catch((e) => {
  console.error(e.message);
  process.exitCode = 1;
});
