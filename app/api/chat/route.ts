import { buildContext } from "@/lib/context";
import { completion, parseRequest, failure, MODEL } from "@/lib/server";
import { readSSE } from "@/lib/sse";
export const runtime = "nodejs";
export async function POST(req: Request) {
  try {
    const messages = await parseRequest(req);
    if (messages.at(-1)?.role !== "user") throw new Error("请先输入你的问题。");
    const context = await buildContext(
      messages.at(-1)!.content,
      messages
        .slice(0, -1)
        .filter((m) => m.role === "user" || m.status === "complete"),
    );
    const upstream = await completion(
      [
        { role: "system", content: context.system },
        ...messages
          .filter((m) => m.role === "user" || m.status === "complete")
          .map(({ role, content }) => ({ role, content })),
      ],
      AbortSignal.any([req.signal, AbortSignal.timeout(120000)]),
      true,
    );
    const encoder = new TextEncoder();
    const body = new ReadableStream({
      async start(controller) {
        const send = (v: unknown) =>
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(v)}\n\n`));
        try {
          send({
            type: "sources",
            sources: context.sources,
            meta: {
              model: MODEL,
              skillVersion: context.version,
              promptVersion: "room-v1.1-rag",
              rag: context.rag,
              sourceIds: context.sources.map((s) => s.id),
            },
          });
          let finished = false;
          for await (const data of readSSE(upstream.body!)) {
            if (data === "[DONE]") break;
            const chunk = JSON.parse(data);
            const choice = chunk.choices?.[0];
            if (choice?.delta?.content)
              send({ type: "delta", text: choice.delta.content });
            if (choice?.finish_reason === "stop") finished = true;
            if (chunk.usage) send({ type: "usage", usage: chunk.usage });
          }
          if (!finished) throw new Error("连接中断或回复未完成，请重试。");
          send({ type: "done" });
        } catch {
          send({
            type: "error",
            error: "连接中断，已保留收到的内容。请重试。",
          });
        } finally {
          controller.close();
        }
      },
    });
    return new Response(body, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
      },
    });
  } catch (e) {
    return failure(e);
  }
}
