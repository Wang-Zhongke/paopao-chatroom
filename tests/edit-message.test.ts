import { test } from "node:test";
import assert from "node:assert/strict";
import { editMessage } from "../lib/edit-message";
import type { Session } from "../lib/types";
const session: Session = {
  id: "s1",
  title: "旧标题",
  topic: "旧主题",
  createdAt: 1,
  updatedAt: 2,
  draft: "未发送草稿",
  messages: [
    {
      id: "u1",
      role: "user",
      content: "第一条",
      status: "complete",
      createdAt: 1,
    },
    {
      id: "a1",
      role: "assistant",
      content: "第一次回答",
      status: "complete",
      createdAt: 2,
    },
    {
      id: "u2",
      role: "user",
      content: "第二条",
      status: "complete",
      createdAt: 3,
    },
    {
      id: "a2",
      role: "assistant",
      content: "旧判断",
      status: "complete",
      createdAt: 4,
    },
  ],
  summary: {
    decision: "旧问题",
    judgment: "旧判断",
    unknowns: "",
    actions: "手动编辑内容",
    messageIds: ["u2"],
    basedOn: "a2",
    edited: true,
    evidence: [],
  },
};
test("editing a past question keeps only its prefix and retains an independently restorable old timeline", () => {
  const untouched = structuredClone(session);
  const { previous, revised } = editMessage(session, "u2", " 更正第二条 ");
  assert.deepEqual(session, untouched);
  assert.notEqual(previous.id, session.id);
  assert.equal(previous.title, "旧标题（修改前）");
  assert.deepEqual(previous.messages, session.messages);
  assert.deepEqual(previous.summary, session.summary);
  assert.equal(revised.id, session.id);
  assert.deepEqual(revised.messages.slice(0, 2), session.messages.slice(0, 2));
  assert.equal(revised.messages.length, 3);
  assert.notEqual(revised.messages[2].id, "u2");
  assert.equal(revised.messages[2].content, "更正第二条");
  assert.equal(revised.messages[2].meta?.editedFrom, "u2");
  assert.equal(revised.summary, undefined);
  assert.equal(revised.summaryHistory, undefined);
  assert.equal(revised.draft, "未发送草稿");
});
test("editing the opening updates title/topic and rejects blank, unchanged, oversized or non-user edits", () => {
  const { revised } = editMessage(session, "u1", "新的问题");
  assert.equal(revised.title, "新的问题");
  assert.equal(revised.topic, "新的问题");
  assert.equal(revised.messages.length, 1);
  for (const [id, text] of [
    ["u1", "  "],
    ["u1", "第一条"],
    ["u1", "字".repeat(12001)],
    ["a1", "改回答"],
    ["missing", "不存在"],
  ])
    assert.throws(() => editMessage(session, id, text));
});
