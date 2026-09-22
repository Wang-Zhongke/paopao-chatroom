import { test } from "node:test";
import assert from "node:assert/strict";
import { readSSE } from "../lib/sse";
import { validateEvidence, requestSchema } from "../lib/validation";
import { buildContext } from "../lib/context";
test("SSE preserves split UTF-8 and fragmented CRLF lines", async () => {
  const bytes = new TextEncoder().encode(
    'data: {"text":"你好"}\r\n\r\ndata: [DONE]\n',
  );
  const stream = new ReadableStream<Uint8Array>({
    start(c) {
      for (let i = 0; i < bytes.length; i += 2)
        c.enqueue(bytes.slice(i, i + 2));
      c.close();
    },
  });
  const got = [];
  for await (const line of readSSE(stream)) got.push(line);
  assert.deepEqual(got, ['{"text":"你好"}', "[DONE]"]);
});
test("summary rejects invented IDs and assistant claims represented as user facts", () => {
  const messages = [
    {
      id: "u1",
      role: "user" as const,
      content: "我做过运营",
      status: "complete" as const,
    },
    {
      id: "a1",
      role: "assistant" as const,
      content: "可以做个项目",
      status: "complete" as const,
    },
  ];
  const base = {
    decision: "转行",
    judgment: "",
    unknowns: "",
    actions: "",
    messageIds: ["u1"],
    evidence: [{ text: "运营经历", messageIds: ["u1"], kind: "user-stated" }],
  };
  assert.doesNotThrow(() => validateEvidence(base, messages));
  assert.throws(() =>
    validateEvidence({ ...base, messageIds: ["fake"] }, messages),
  );
  assert.throws(() =>
    validateEvidence(
      {
        ...base,
        evidence: [
          { text: "做完项目", messageIds: ["a1"], kind: "user-stated" },
        ],
      },
      messages,
    ),
  );
  assert.throws(() =>
    validateEvidence(base, [{ ...messages[0], status: "stopped" }]),
  );
});
test("requests reject excessive context instead of silently losing corrections", () => {
  assert.equal(
    requestSchema.safeParse({
      messages: Array.from({ length: 10 }, (_, i) => ({
        id: String(i),
        role: "user",
        status: "complete",
        content: "字".repeat(11000),
      })),
    }).success,
    false,
  );
});
test("Skill-only context works without retrieval files", async () => {
  const context = await buildContext("想转 AI 产品", [], { enabled: false });
  assert.deepEqual(context.sources, []);
  assert.match(context.system, /核心心智模型/);
});

test("origin validation uses the requested Host when Next normalizes the URL", async () => {
  const { parseRequest } = await import("../lib/server");
  const makeRequest = (origin: string, host?: string, forwardedHost?: string) =>
    new Request("http://localhost:3000/api/chat", {
      method: "POST",
      headers: {
        origin,
        "Content-Type": "application/json",
        ...(host ? { host } : {}),
        ...(forwardedHost ? { "x-forwarded-host": forwardedHost } : {}),
      },
      body: JSON.stringify({
        messages: [
          { id: "u1", role: "user", content: "测试问题", status: "complete" },
        ],
      }),
    });
  assert.equal(
    (await parseRequest(makeRequest("http://127.0.0.1:3000", "127.0.0.1:3000")))
      .length,
    1,
  );
  assert.equal(
    (await parseRequest(makeRequest("http://localhost:3000", "localhost:3000")))
      .length,
    1,
  );
  assert.equal(
    (await parseRequest(makeRequest("http://localhost:3000"))).length,
    1,
  );
  for (const origin of [
    "https://untrusted.example",
    "http://127.0.0.1:3001",
    "https://127.0.0.1:3000",
    "http://localhost:3000",
    "null",
  ]) {
    await assert.rejects(
      parseRequest(makeRequest(origin, "127.0.0.1:3000")),
      /请求来源不允许/,
    );
  }
  await assert.rejects(
    parseRequest(
      makeRequest(
        "https://untrusted.example",
        "127.0.0.1:3000",
        "untrusted.example",
      ),
    ),
    /请求来源不允许/,
  );
});
