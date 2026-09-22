import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { createIndex, type Unit } from "../lib/rag/index";
import {
  retrieve,
  routeQuery,
  loadIndex,
  search,
  selectEvidence,
  evidenceContext,
} from "../lib/rag/retrieve";
import { RAG_CONFIG } from "../lib/rag/config";
import { buildContext } from "../lib/context";
const unit: Unit = {
  id: "test-learning",
  type: "viewpoint",
  title: "测试材料：输出型学习",
  question: "",
  answer: "",
  claim: "测试材料：讲解和反馈帮助学习",
  context: "测试用途，不是泡泡老师原话",
  content: "[0001] 测试材料，讲解与反馈可以帮助学习。",
  topics: ["learning"],
  annotations: "editorial-paraphrase-not-quotation",
  source: {
    id: "BVtest123",
    title: "测试材料",
    date: "2026-01-01",
    quality: "machine-subtitle",
    transcript: "tests/fixture",
    transcriptHash: "test",
    ranges: [[1, 1]],
    questionRanges: [],
    answerRanges: [],
    start: "00:00",
    end: "00:10",
    limitations: "合成测试材料，禁止用于真实回答",
    review: "text-boundaries-reviewed-audio-unverified",
  },
};
const index = createIndex([unit], "fixture");
test("conditional retrieval uses current turn; thanks does not inherit old career topics", async () => {
  for (const q of ["你好", "今天好累", "解释一下量子纠缠"]) {
    assert.equal(
      routeQuery(q, [{ role: "user", content: "AI 产品求职" }]).triggered,
      false,
    );
  }
  assert.equal(routeQuery("泡泡以前说过月球土豆吗？").provenance, true);
  assert.equal(
    routeQuery("那这个岗位怎么选？", [{ role: "user", content: "AI 产品求职" }])
      .triggered,
    true,
  );
  assert.equal(
    routeQuery("谢谢", [{ role: "user", content: "职业选择" }]).triggered,
    false,
  );
});
test("disabled and casual requests never load the index", async () => {
  let calls = 0;
  const loader = async () => {
    calls++;
    throw new Error("unavailable");
  };
  assert.equal(
    (await retrieve("学习", [], { enabled: false, loader, log: false })).trace
      .reason,
    "disabled",
  );
  await retrieve("你好", [], { enabled: true, loader, log: false });
  assert.equal(calls, 0);
});
test("unknown or low relevance evidence never enters prompt", () => {
  const hits = search(index, "创业公司量子纠缠火星土豆的学习工艺");
  assert.equal(selectEvidence(hits).length, 0);
  const good = search(index, "输出型学习讲解反馈");
  assert.equal(selectEvidence(good).length, 1);
});
test("missing, malformed and schema-invalid indexes fail open; a repaired index recovers", async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), "paopao-rag-"));
  const file = path.join(dir, "index.json");
  try {
    for (const contents of [null, "{broken", '{"version":123}']) {
      if (contents !== null) await writeFile(file, contents);
      const context = await buildContext("输出型学习", [], {
        enabled: true,
        indexPath: file,
        log: false,
      });
      assert.equal(context.rag.reason, "retrieval-unavailable");
      assert.equal(context.sources.length, 0);
      assert.match(context.system, /核心心智模型/);
      assert.match(context.system, /可以用通用知识回答新问题/);
      assert.match(context.system, /<retrieved_evidence>\n\[\]/);
    }
    await writeFile(file, JSON.stringify(index));
    assert.equal((await loadIndex(file)).digest, "fixture");
    assert.equal(
      (
        await retrieve("输出型学习讲解反馈", [], {
          indexPath: file,
          enabled: true,
          log: false,
        })
      ).evidence.length,
      1,
    );
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
test("slow loader has bounded failure; Skill survives timeout", async () => {
  const start = Date.now();
  const result = await retrieve("学习", [], {
    enabled: true,
    log: false,
    loader: () => new Promise(() => {}),
  });
  assert.equal(result.trace.reason, "retrieval-unavailable");
  assert.ok(Date.now() - start < RAG_CONFIG.timeoutMs + 700);
});
test("enabled and disabled prompts retain same Skill and natural fallback contract", async () => {
  const off = await buildContext("输出型学习", [], {
    enabled: false,
    log: false,
  });
  const on = await buildContext("输出型学习", [], {
    enabled: true,
    loader: async () => index,
    log: false,
  });
  assert.equal(off.version, on.version);
  assert.equal(off.sources.length, 0);
  assert.equal(on.sources[0].id, "BVtest123");
  assert.match(off.system, /只有用户明确追问/);
  assert.match(on.system, /不能冒充已核对音视频的精确原话/);
  const missing = await retrieve("泡泡说过火星种土豆吗？", [], {
    enabled: true,
    loader: async () => index,
    log: false,
  });
  assert.match(evidenceContext(missing), /明确追问来源/);
  assert.equal(missing.evidence.length, 0);
});
test("selection respects per-source and complete-unit budgets without truncation", () => {
  const hits = Array.from({ length: 10 }, (_, i) => ({
    unit: {
      ...unit,
      id: String(i),
      source: {
        ...unit.source,
        ranges: [[i + 1, i + 1]] as [number, number][],
      },
    },
    score: 1,
    bm25: 10,
    coverage: 1,
    matched: ["输出", "学习"],
    selected: false,
  }));
  assert.equal(selectEvidence(hits).length, RAG_CONFIG.maxPerSource);
});

test("chat API still reaches the LLM when RAG is disabled or its index is corrupt", async () => {
  const { POST } = await import("../app/api/chat/route");
  const dir = await mkdtemp(path.join(os.tmpdir(), "paopao-rag-api-"));
  const file = path.join(dir, "index.json");
  await writeFile(file, "{broken");
  const saved = {
    key: process.env.DEEPSEEK_API_KEY,
    enabled: process.env.RAG_ENABLED,
    file: process.env.RAG_INDEX_PATH,
  };
  const originalFetch = globalThis.fetch;
  let calls = 0;
  try {
    process.env.DEEPSEEK_API_KEY = "test-not-a-real-key";
    process.env.RAG_INDEX_PATH = file;
    globalThis.fetch = async (url, init) => {
      assert.equal(url, "https://api.deepseek.com/chat/completions");
      const body = JSON.parse(String(init?.body));
      assert.match(body.messages[0].content, /核心心智模型/);
      assert.equal(body.messages.at(-1).content, "我想转 AI 产品");
      assert.equal(
        body.messages.some(
          (m: { content: string }) => m.content === "未完成的旧建议",
        ),
        false,
      );
      calls++;
      return new Response(
        'data: {"choices":[{"delta":{"content":"测试回复"},"finish_reason":null}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n',
        { headers: { "Content-Type": "text/event-stream" } },
      );
    };
    for (const enabled of ["false", "true"]) {
      process.env.RAG_ENABLED = enabled;
      const res = await POST(
        new Request("http://localhost:3000/api/chat", {
          method: "POST",
          headers: {
            host: "127.0.0.1:3000",
            origin: "http://127.0.0.1:3000",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            messages: [
              {
                id: "u0",
                role: "user",
                content: "我有运营经历",
                status: "complete",
              },
              {
                id: "a0",
                role: "assistant",
                content: "未完成的旧建议",
                status: "stopped",
              },
              {
                id: "u1",
                role: "user",
                content: "我想转 AI 产品",
                status: "complete",
              },
            ],
          }),
        }),
      );
      assert.equal(res.status, 200);
      const text = await res.text();
      assert.match(text, /测试回复/);
      assert.match(text, /"type":"done"/);
      assert.match(
        text,
        enabled === "false"
          ? /"reason":"disabled"/
          : /"reason":"retrieval-unavailable"/,
      );
    }
    assert.equal(calls, 2);
  } finally {
    globalThis.fetch = originalFetch;
    for (const [key, value] of Object.entries({
      DEEPSEEK_API_KEY: saved.key,
      RAG_ENABLED: saved.enabled,
      RAG_INDEX_PATH: saved.file,
    })) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    await rm(dir, { recursive: true, force: true });
  }
});

test("overlapping transcript evidence is sent once and weak secondary matches are dropped", () => {
  const hit = (
    id: string,
    range: [number, number],
    score: number,
    source = "BVtest123",
  ) => ({
    unit: {
      ...unit,
      id,
      source: { ...unit.source, id: source, ranges: [range] },
    },
    score,
    bm25: 10,
    coverage: 1,
    matched: ["学习", "反馈"],
    selected: false,
  });
  const chosen = selectEvidence([
    hit("a", [10, 20], 0.9),
    hit("duplicate", [1, 30], 0.89),
    hit("adjacent", [21, 30], 0.85),
    hit("weak", [1, 10], 0.45, "BVtest456"),
  ]);
  assert.deepEqual(
    chosen.map((h) => h.unit.id),
    ["a", "adjacent"],
  );
});
