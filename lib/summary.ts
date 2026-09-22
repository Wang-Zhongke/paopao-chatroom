import { z } from "zod";
import { messageSchema, validateEvidence } from "./validation";

// Models sometimes return bullet lists despite JSON mode. Convert only lossless
// text lists; malformed objects and invalid evidence must still be rejected.
export function parseSummary(
  content: string,
  messages: z.infer<typeof messageSchema>[],
) {
  const value = JSON.parse(content);
  if (value && typeof value === "object" && !Array.isArray(value)) {
    for (const field of ["decision", "judgment", "unknowns", "actions"]) {
      if (
        Array.isArray(value[field]) &&
        value[field].every((item: unknown) => typeof item === "string")
      ) {
        value[field] = value[field]
          .map((item: string) => `• ${item}`)
          .join("\n");
      }
    }
  }
  return validateEvidence(value, messages);
}

export function summaryFeedback(error: unknown): string {
  if (error instanceof z.ZodError) {
    // Only paths and schema issues, never conversation content.
    return error.issues
      .map((issue) => `${issue.path.join(".")}: ${issue.message}`)
      .join("; ");
  }
  if (error instanceof SyntaxError)
    return "必须返回完整合法的 JSON 对象，不要 Markdown 代码块。";
  return "引用无效：所有 messageIds 必须原样来自输入消息；非 inference 的证据只能引用 user 消息。";
}
