import { requestSchema } from "./validation";
export const MODEL = "deepseek-flash";
export async function parseRequest(req: Request) {
  const origin = req.headers.get("origin");
  // Next.js can normalize req.url to localhost even when the browser used
  // 127.0.0.1. Host retains the address actually requested by the browser.
  // Do not trust X-Forwarded-Host or broadly allow all loopback origins.
  const expected = new URL(req.url);
  const host = req.headers.get("host");
  if (host) expected.host = host;
  if (origin && origin !== expected.origin) throw new Error("请求来源不允许。");
  const text = await req.text();
  if (text.length > 180000) throw new Error("内容过长，请另开一场并带上小结。");
  return requestSchema.parse(JSON.parse(text)).messages;
}
export async function completion(
  messages: { role: string; content: string }[],
  signal: AbortSignal,
  stream: boolean,
) {
  if (!process.env.DEEPSEEK_API_KEY)
    throw new Error("尚未配置服务，请在服务端设置 API 密钥后重启。");
  const response = await fetch("https://api.deepseek.com/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.DEEPSEEK_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: MODEL,
      messages,
      stream,
      reasoning_effort: "low",
      max_tokens: 6000,
      ...(!stream
        ? { response_format: { type: "json_object" } }
        : { stream_options: { include_usage: true } }),
    }),
    signal,
  });
  if (!response.ok)
    throw new Error(
      response.status === 401
        ? "服务密钥无效，请检查配置。"
        : response.status === 429
          ? "服务繁忙，请稍后重试。"
          : "暂时无法连接回复服务，请重试。",
    );
  return response;
}
export function failure(error: unknown) {
  return Response.json(
    {
      error:
        error instanceof Error && !error.message.includes("[")
          ? error.message
          : "请求内容无效，请检查后重试。",
    },
    { status: 400 },
  );
}
