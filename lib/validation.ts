import { z } from "zod";
export const messageSchema = z.object({
  id: z.string().min(1).max(100),
  role: z.enum(["user", "assistant"]),
  content: z.string().min(1).max(12000),
  status: z.enum(["complete", "stopped", "error", "streaming"]),
});
export const requestSchema = z
  .object({ messages: z.array(messageSchema).min(1).max(160) })
  .refine(
    (v) => v.messages.reduce((n, m) => n + m.content.length, 0) <= 100000,
    "本场内容过长，请另开一场并带上小结。",
  );
export const summarySchema = z.object({
  decision: z.string().max(4000),
  judgment: z.string().max(6000),
  unknowns: z.string().max(4000),
  actions: z.string().max(4000),
  messageIds: z.array(z.string()),
  evidence: z
    .array(
      z.object({
        text: z.string(),
        messageIds: z.array(z.string()).min(1),
        kind: z.enum([
          "user-stated",
          "inference",
          "project-evidence",
          "action-feedback",
        ]),
        supersedes: z.string().optional(),
      }),
    )
    .max(30),
});
export function validateEvidence(
  value: unknown,
  messages: z.infer<typeof messageSchema>[],
) {
  const result = summarySchema.parse(value);
  const complete = new Set(
    messages.filter((m) => m.status === "complete").map((m) => m.id),
  );
  const user = new Set(
    messages
      .filter((m) => m.role === "user" && m.status === "complete")
      .map((m) => m.id),
  );
  if (
    result.messageIds.some((id) => !complete.has(id)) ||
    result.evidence.some((e) =>
      e.messageIds.some(
        (id) => !(e.kind === "inference" ? complete : user).has(id),
      ),
    )
  )
    throw new Error("小结引用无效，请重新整理。");
  return result;
}
