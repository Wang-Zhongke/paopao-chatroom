import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "泡泡连麦室 · 从你的处境开始",
  description:
    "一个把职业困惑聊清楚的空间。基于泡泡老师公开内容的 AI 视角体验。",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
