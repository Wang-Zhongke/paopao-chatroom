import type { Session, Message } from "./types";

// Keep the previous timeline independently restorable, including its summary.
// Only the revised prefix goes to the model; later replies depend on old facts.
export function editMessage(session: Session, messageId: string, text: string) {
  const position = session.messages.findIndex(
    (m) => m.id === messageId && m.role === "user",
  );
  const content = text.trim();
  if (position < 0 || !content || content.length > 12000)
    throw new Error("修改内容无效。");
  const original = session.messages[position];
  if (content === original.content) throw new Error("请先修改消息内容。");
  const now = Date.now();
  const message: Message = {
    id: crypto.randomUUID(),
    role: "user",
    content,
    createdAt: now,
    status: "complete",
    meta: { editedFrom: original.id },
  };
  const previous: Session = {
    ...session,
    id: crypto.randomUUID(),
    title: `${session.title}（修改前）`,
    updatedAt: now - 1,
  };
  const revised: Session = {
    ...session,
    title: position === 0 ? content.slice(0, 25) : session.title,
    topic: position === 0 ? content.slice(0, 60) : session.topic,
    messages: [...session.messages.slice(0, position), message],
    summary: undefined,
    summaryHistory: undefined,
    updatedAt: now,
  };
  return { previous, revised };
}
