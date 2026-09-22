import { completion, parseRequest, failure } from "@/lib/server";
import { parseSummary, summaryFeedback } from "@/lib/summary";
export const runtime = "nodejs";
export async function POST(req: Request) {
  try {
    const messages = (await parseRequest(req)).filter(
      (m) => m.status === "complete",
    );
    if (!messages.length) throw new Error("还没有可整理的内容。");
    const instruction =
      "整理对话，返回 JSON 对象，包含字符串 decision（正在决定的事，含目标约束选项）、judgment（当前判断及理由）、unknowns（待确认事实）、actions（下一步行动），以及 messageIds（引用的消息ID数组）、evidence（经历与行动线索数组，每条含 text、messageIds、kind）。kind 只能为 user-stated、inference、project-evidence、action-feedback。用户自述不等于已验证项目证据。用户陈述、项目证据、行动反馈只能引用用户消息，推测须标 inference。使用最新纠正，旧值如需保留明确说明已被取代。缺失信息用空字符串或空数组，不补造事实。不把助手建议写成用户已完成行动。只概括已完成对话。";
    const format =
      '\n严格使用以下结构：{"decision":"文本","judgment":"文本","unknowns":"文本","actions":"文本","messageIds":[],"evidence":[{"text":"线索","messageIds":["输入中的原始ID"],"kind":"user-stated"}]}。四个正文栏目必须是字符串，多项内容用换行分隔；每栏不超过1500字，证据不超过12条。没有证据时 evidence 为 []。不要添加对话中未讨论的新建议或虚构选项。';
    // Share a deadline across attempts so the server finishes before the client.
    const signal = AbortSignal.any([req.signal, AbortSignal.timeout(105000)]);
    let correction = "";
    let result;
    for (let attempt = 0; attempt < 2; attempt++) {
      const res = await completion(
        [
          { role: "system", content: instruction + format + correction },
          { role: "user", content: JSON.stringify(messages) },
        ],
        signal,
        false,
      );
      const data = await res.json();
      try {
        if (data.choices?.[0]?.finish_reason === "length") {
          correction =
            "\n上次输出超长被截断，请显著缩短各栏目和证据，返回完整 JSON。";
          if (attempt === 0) continue;
          throw new Error("输出截断");
        }
        const content = data.choices?.[0]?.message?.content;
        if (typeof content !== "string" || !content.trim())
          throw new SyntaxError("Empty output");
        result = parseSummary(content, messages);
        break;
      } catch (error) {
        correction =
          "\n上次输出未通过校验，请修正以下问题后重新生成完整 JSON：" +
          summaryFeedback(error);
        if (process.env.NODE_ENV === "development") {
          console.warn("[summary] validation_failed", {
            attempt: attempt + 1,
            issue: summaryFeedback(error),
          });
        }
        if (attempt === 1) throw new Error("小结格式校验失败，请重新整理。");
      }
    }
    return Response.json(result);
  } catch (e) {
    if (
      e instanceof Error &&
      (e.name === "TimeoutError" || e.name === "AbortError")
    ) {
      return failure(new Error("小结整理超时，请稍后重试。"));
    }
    return failure(e);
  }
}
