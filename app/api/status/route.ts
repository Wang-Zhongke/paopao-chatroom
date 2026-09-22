export const dynamic = "force-dynamic";
export function GET() {
  return Response.json({ configured: !!process.env.DEEPSEEK_API_KEY });
}
