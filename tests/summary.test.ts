import { test } from "node:test";
import assert from "node:assert/strict";
import { parseSummary } from "../lib/summary";
import { POST } from "../app/api/summary/route";
const messages = [
  {
    id: "u1",
    role: "user" as const,
    content: "想找实习",
    status: "complete" as const,
  },
  {
    id: "a1",
    role: "assistant" as const,
    content: "建议试用项目",
    status: "complete" as const,
  },
];
const base = {
  decision: "找实习",
  judgment: "",
  unknowns: "",
  actions: "",
  messageIds: ["u1"],
  evidence: [{ text: "想找实习", messageIds: ["u1"], kind: "user-stated" }],
};
function request() {
  return new Request("http://localhost/api/summary", {
    method: "POST",
    body: JSON.stringify({ messages }),
  });
}
test("summary converts string lists without losing text, including empty lists", () => {
  const result = parseSummary(
    JSON.stringify({
      ...base,
      unknowns: [],
      actions: ["找人试用", "记录反馈"],
    }),
    messages,
  );
  assert.equal(result.unknowns, "");
  assert.equal(result.actions, "• 找人试用\n• 记录反馈");
  assert.deepEqual(parseSummary(JSON.stringify(base), messages), base);
});
test("summary compatibility still rejects objects, fabricated references, assistant facts and stopped evidence", () => {
  for (const value of [
    { ...base, actions: [{ text: "不可隐式转成字符串" }] },
    { ...base, messageIds: ["invented"] },
    { ...base, evidence: [{ ...base.evidence[0], messageIds: ["a1"] }] },
  ])
    assert.throws(() => parseSummary(JSON.stringify(value), messages));
  assert.throws(() =>
    parseSummary(
      JSON.stringify(base),
      messages.map((m) => ({ ...m, status: "stopped" })),
    ),
  );
});
test("summary endpoint repairs schema errors and rejects persistent invalid evidence", async (t) => {
  const originalKey = process.env.DEEPSEEK_API_KEY;
  process.env.DEEPSEEK_API_KEY = "synthetic-test";
  t.after(() => {
    if (originalKey === undefined) delete process.env.DEEPSEEK_API_KEY;
    else process.env.DEEPSEEK_API_KEY = originalKey;
  });
  const calls: { messages: { content: string }[] }[] = [];
  const outputs: unknown[] = [
    { ...base, actions: { bad: true } },
    { ...base, actions: ["试用"] },
  ];
  t.mock.method(
    globalThis,
    "fetch",
    async (_input: unknown, init: RequestInit) => {
      calls.push(JSON.parse(init.body as string));
      return Response.json({
        choices: [
          {
            finish_reason: "stop",
            message: { content: JSON.stringify(outputs.shift()) },
          },
        ],
      });
    },
  );
  const response = await POST(request());
  assert.equal(response.status, 200);
  assert.equal((await response.json()).actions, "• 试用");
  assert.equal(calls.length, 2);
  assert.match(calls[1].messages[0].content, /actions: Expected string/);
  outputs.push(
    { ...base, messageIds: ["fake"] },
    { ...base, messageIds: ["fake"] },
  );
  const rejected = await POST(request());
  assert.equal(rejected.status, 400);
  assert.match((await rejected.json()).error, /校验失败/);
});
