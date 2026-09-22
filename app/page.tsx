"use client";
import { useEffect, useRef, useState } from "react";
import type { Message, Session, Summary } from "@/lib/types";
import { allSessions, writeSession, deleteSession } from "@/lib/storage";
import { editMessage } from "@/lib/edit-message";
import { readSSE } from "@/lib/sse";
const examples = [
  {
    title: "想转 AI",
    text: "做了五年运营，想转 AI 产品，但一直在学工具，还没做出项目。",
    detail: "经验怎么带过去，第一步怎么走？",
  },
  {
    title: "想换工作",
    text: "现在的工作很熟悉，但觉得没有成长。拿到一个新 Offer，又担心只是换个地方做重复的事。",
    detail: "留下还是离开，什么值得比较？",
  },
  {
    title: "想做内容",
    text: "想把自己的专业经验做成内容，但不知道写给谁，也担心没有人看。",
    detail: "有经验，却还没找到表达的起点。",
  },
];
const fields = [
  ["decision", "你正在决定的事"],
  ["judgment", "当前判断及理由"],
  ["unknowns", "需要确认的事实"],
  ["actions", "下一步行动"],
] as const;
function newSession(): Session {
  return {
    id: crypto.randomUUID(),
    title: "新的连麦",
    topic: "",
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [],
    draft: "",
  };
}
function Avatar({ small = false }: { small?: boolean }) {
  return (
    <img
      className={small ? "avatar small" : "avatar"}
      src="/paopao-mark.svg"
      alt="泡泡老师"
      width={small ? 42 : 112}
      height={small ? 42 : 112}
    />
  );
}
function MessageIcon({ kind }: { kind: "copy" | "edit" | "check" }) {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {kind === "copy" ? (
        <>
          <rect x="8" y="8" width="12" height="12" rx="2" />
          <path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" />
        </>
      ) : kind === "edit" ? (
        <>
          <path d="m15 4 5 5M4 20l5-1L20 8a2.1 2.1 0 0 0-4-4L5 15l-1 5Z" />
        </>
      ) : (
        <path d="m5 12 4 4L19 6" />
      )}
    </svg>
  );
}
function download(name: string, text: string, type = "text/plain") {
  const url = URL.createObjectURL(
    new Blob([text], { type: `${type};charset=utf-8` }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export default function Room() {
  const [sessions, setSessions] = useState<Session[]>([]),
    [active, setActive] = useState<Session | null>(null),
    [configured, setConfigured] = useState<boolean | null>(null),
    [busy, setBusy] = useState(false),
    [summaryBusy, setSummaryBusy] = useState(false),
    [summaryConfirm, setSummaryConfirm] = useState(false),
    [panel, setPanel] = useState<"summary" | "sources" | "settings" | null>(
      null,
    ),
    [menu, setMenu] = useState(false),
    [notice, setNotice] = useState(""),
    [summaryError, setSummaryError] = useState(""),
    [copied, setCopied] = useState<string | null>(null),
    [deleteTarget, setDeleteTarget] = useState<{
      id?: string;
      title: string;
    } | null>(null),
    [deleting, setDeleting] = useState(false),
    [deleteError, setDeleteError] = useState(""),
    [editing, setEditing] = useState<{ id: string; content: string } | null>(
      null,
    );
  const activeRef = useRef<Session | null>(null),
    abort = useRef<AbortController | null>(null),
    scroll = useRef<HTMLDivElement>(null),
    follow = useRef(true),
    input = useRef<HTMLTextAreaElement>(null),
    panelRef = useRef<HTMLElement>(null);
  const saving = useRef(Promise.resolve());
  const sending = useRef(false);
  const deleteDialog = useRef<HTMLDialogElement>(null);
  const deleteLock = useRef(false);
  const summaryDialog = useRef<HTMLDialogElement>(null);
  const summaryLock = useRef(false);
  useEffect(() => {
    if (summaryConfirm) summaryDialog.current?.showModal();
    else summaryDialog.current?.close();
  }, [summaryConfirm]);
  useEffect(() => {
    if (deleteTarget) deleteDialog.current?.showModal();
    else deleteDialog.current?.close();
  }, [deleteTarget]);
  function requestDelete(target: { id?: string; title: string }) {
    setDeleteError("");
    setDeleteTarget(target);
  }
  async function confirmDelete() {
    if (!deleteTarget || deleteLock.current || busy || summaryBusy) return;
    deleteLock.current = true;
    setDeleting(true);
    setDeleteError("");
    try {
      await saving.current;
      await deleteSession(deleteTarget.id);
      setSessions((prev) =>
        deleteTarget.id ? prev.filter((s) => s.id !== deleteTarget.id) : [],
      );
      if (!deleteTarget.id || activeRef.current?.id === deleteTarget.id) {
        const fresh = newSession();
        activeRef.current = fresh;
        setActive(fresh);
        setEditing(null);
        setPanel(null);
      }
      setDeleteTarget(null);
      setMenu(false);
      setNotice(deleteTarget.id ? "这场连麦已删除。" : "本地记录已删除。");
    } catch {
      setDeleteError("删除失败，记录仍保留，请重试。");
    } finally {
      deleteLock.current = false;
      setDeleting(false);
    }
  }
  const copyFeedback = useRef<ReturnType<typeof setTimeout> | null>(null);
  async function copyMessage(message: Message) {
    try {
      await navigator.clipboard.writeText(message.content);
      if (copyFeedback.current) clearTimeout(copyFeedback.current);
      setCopied(message.id);
      copyFeedback.current = setTimeout(() => setCopied(null), 1800);
    } catch {
      setNotice("无法复制，请选择消息文字后复制。");
    }
  }
  useEffect(() => {
    setEditing(null);
  }, [active?.id]);
  function update(s: Session) {
    activeRef.current = s;
    setActive(s);
    setSessions((prev) =>
      [s, ...prev.filter((x) => x.id !== s.id)].sort(
        (a, b) => b.updatedAt - a.updatedAt,
      ),
    );
    saving.current = saving.current
      .then(() => writeSession(s))
      .catch(() => setNotice("本地保存失败，请先导出记录，避免丢失。"));
  }
  useEffect(() => {
    fetch("/api/status")
      .then((r) => r.json())
      .then((d) => setConfigured(d.configured))
      .catch(() => {
        setConfigured(false);
        setNotice("无法检查服务状态，请刷新重试。");
      });
    allSessions()
      .then((rows) => {
        const restored = rows
          .map((s) => ({
            ...s,
            messages: s.messages.map((m) =>
              m.status === "streaming"
                ? { ...m, status: "stopped" as const }
                : m,
            ),
          }))
          .sort((a, b) => b.updatedAt - a.updatedAt);
        setSessions(restored);
        const s = restored[0] || newSession();
        setActive(s);
        activeRef.current = s;
      })
      .catch(() => {
        setNotice("浏览器无法保存历史，当前内容请及时导出。");
        const s = newSession();
        setActive(s);
        activeRef.current = s;
      });
    return () => {
      abort.current?.abort();
      if (copyFeedback.current) clearTimeout(copyFeedback.current);
    };
  }, []);
  useEffect(() => {
    if (active?.messages.length && follow.current && scroll.current)
      scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [active?.messages]);
  useEffect(() => {
    if (panel) panelRef.current?.focus();
  }, [panel]);
  useEffect(() => {
    const close = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (deleteDialog.current?.open || summaryDialog.current?.open) return;
        setPanel(null);
        setMenu(false);
        setEditing(null);
        input.current?.focus();
      }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  function start() {
    if (busy || summaryBusy) return;
    const s = newSession();
    update(s);
    setPanel(null);
    setMenu(false);
    setNotice("");
    input.current?.focus();
  }
  async function send(retry = false, edit?: { id: string; content: string }) {
    let current = activeRef.current;
    if (
      !current ||
      busy ||
      sending.current ||
      summaryBusy ||
      !configured ||
      (editing && !edit)
    )
      return;
    let previous: Session | undefined;
    if (edit) {
      try {
        const revision = editMessage(current, edit.id, edit.content);
        previous = revision.previous;
        current = revision.revised;
      } catch (error) {
        setNotice(
          error instanceof Error ? error.message : "修改失败，请重试。",
        );
        return;
      }
    }
    let messages = current.messages;
    const draft = current.draft.trim();
    if (!retry && !edit && !draft) return;
    if (retry) {
      const last = messages.at(-1);
      if (last?.role !== "assistant" || last.status === "complete") return;
      messages = messages.slice(0, -1);
    } else if (!edit)
      messages = [
        ...messages,
        {
          id: crypto.randomUUID(),
          role: "user",
          content: draft,
          createdAt: Date.now(),
          status: "complete",
        },
      ];
    sending.current = true;
    setBusy(true);
    if (previous) {
      try {
        await saving.current;
        await writeSession(previous);
      } catch {
        sending.current = false;
        setBusy(false);
        setNotice("无法保存修改前的记录，消息尚未修改。请重试或先导出记录。");
        return;
      }
      setSessions((rows) => [previous!, ...rows]);
      setEditing(null);
      setPanel(null);
      setSummaryError("");
    }
    const reply: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      createdAt: Date.now(),
      status: "streaming",
    };
    let running = {
      ...current,
      title: current.messages.length ? current.title : draft.slice(0, 25),
      topic: current.topic || draft.slice(0, 60),
      draft: retry || edit ? current.draft : "",
      messages: [...messages, reply],
      updatedAt: Date.now(),
    };
    update(running);
    setBusy(true);
    setNotice("");
    follow.current = true;
    const controller = new AbortController();
    abort.current = controller;
    const patch = (partial: Partial<Message>) => {
      running = {
        ...activeRef.current!,
        messages: running.messages.map((m) =>
          m.id === reply.id ? { ...m, ...partial } : m,
        ),
      };
      update(running);
    };
    let text = "";
    let complete = false;
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages }),
        signal: controller.signal,
      });
      if (!response.ok) {
        const e = await response.json();
        throw new Error(e.error);
      }
      if (!response.body) throw new Error("连接中断，请重试。");
      for await (const data of readSSE(response.body)) {
        const event = JSON.parse(data);
        if (event.type === "sources")
          patch({ sources: event.sources, meta: event.meta });
        if (event.type === "usage")
          patch({
            meta: { ...running.messages.at(-1)?.meta, usage: event.usage },
          });
        if (event.type === "delta") {
          text += event.text;
          patch({ content: text });
        }
        if (event.type === "error") throw new Error(event.error);
        if (event.type === "done") complete = true;
      }
      if (!complete || !text) throw new Error("连接中断，重试。");
      patch({ status: "complete" });
    } catch (e) {
      patch({ status: controller.signal.aborted ? "stopped" : "error" });
      if (!controller.signal.aborted)
        setNotice(e instanceof Error ? e.message : "连接中断，重试。");
    } finally {
      setBusy(false);
      sending.current = false;
      abort.current = null;
      input.current?.focus();
    }
  }
  async function summarize(confirmed = false) {
    const s = activeRef.current;
    if (!s || busy || summaryBusy || summaryLock.current || editing) return;
    if (s.summary?.edited && !confirmed) {
      setSummaryConfirm(true);
      return;
    }
    setSummaryConfirm(false);
    summaryLock.current = true;
    setSummaryBusy(true);
    setSummaryError("");
    setPanel("summary");
    try {
      const res = await fetch("/api/summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: s.messages
            .filter((m) => m.status === "complete")
            .map(({ id, role, content, status }) => ({
              id,
              role,
              content,
              status,
            })),
        }),
        signal: AbortSignal.timeout(120000),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      update({
        ...activeRef.current!,
        summaryHistory: [
          ...(s.summaryHistory || []),
          ...(s.summary ? [s.summary] : []),
        ],
        summary: {
          ...data,
          basedOn: s.messages.at(-1)?.id || "",
          edited: false,
        },
      });
    } catch (e) {
      setSummaryError(
        e instanceof Error ? e.message : "小结整理失败，请重试。",
      );
    } finally {
      summaryLock.current = false;
      setSummaryBusy(false);
    }
  }
  function summaryText() {
    return active?.summary
      ? fields
          .map(([k, label]) => `${label}\n${active.summary![k] || "待补充"}`)
          .join("\n\n")
      : "";
  }
  const messages = active?.messages || [],
    hasChat = messages.length > 0,
    sources = Array.from(
      new Map(
        messages.flatMap((m) => m.sources || []).map((s) => [s.id, s]),
      ).values(),
    ),
    stale = active?.summary && active.summary.basedOn !== messages.at(-1)?.id;
  return (
    <div className="room">
      <aside className={`sidebar ${menu ? "open" : ""}`} aria-label="会话导航">
        <a className="brand" href="/" aria-label="泡泡连麦室首页">
          <span className="brandmark">▦</span>
          <span>泡泡连麦室</span>
        </a>
        <div className="host">
          <div className="host-art">
            <Avatar />
          </div>
          <strong>泡泡老师</strong>
          <p>聊聊处境，想清下一步。</p>
        </div>
        <button
          className="new-session"
          onClick={start}
          disabled={busy || summaryBusy}
        >
          <span>＋</span> 新开一场
        </button>
        <div className="history-heading">
          最近连麦 <span>本机保存</span>
        </div>
        <nav className="history">
          {sessions.filter((s) => s.messages.length || s.draft).length === 0 ? (
            <p className="empty-history">
              第一场连麦，从这里开始。
              <br />
              聊过的事，会留在这里。
            </p>
          ) : (
            sessions
              .filter((s) => s.messages.length || s.draft)
              .map((s) => (
                <div
                  className={`history-row ${active?.id === s.id ? "selected" : ""}`}
                  key={s.id}
                >
                  <button
                    disabled={busy || summaryBusy}
                    onClick={() => {
                      setActive(s);
                      activeRef.current = s;
                      setMenu(false);
                      setNotice("");
                      setPanel(null);
                      follow.current = true;
                    }}
                  >
                    <span>{s.title}</span>
                    <small>
                      {new Date(s.updatedAt).toLocaleDateString("zh-CN", {
                        month: "short",
                        day: "numeric",
                      })}
                    </small>
                  </button>
                  <button
                    className="delete"
                    disabled={busy || summaryBusy}
                    aria-label={`删除 ${s.title}`}
                    onClick={() => requestDelete({ id: s.id, title: s.title })}
                  >
                    ×
                  </button>
                </div>
              ))
          )}
        </nav>
        <button
          className="settings"
          onClick={() => {
            setPanel("settings");
            setMenu(false);
          }}
        >
          ⚙ <span>记录与隐私</span>
        </button>
        <div className="sidebar-foot">一个问题，一次认真讨论。</div>
      </aside>
      {menu && (
        <button
          className="scrim"
          aria-label="关闭会话菜单"
          onClick={() => setMenu(false)}
        />
      )}
      <main className={panel ? "main with-panel" : "main"}>
        <header className="topbar">
          <div>
            <button
              className="menu-button"
              aria-label="打开会话菜单"
              onClick={() => setMenu(true)}
            >
              ☰
            </button>
            <span className="status-dot" />
            <span>{busy ? "正在回复" : hasChat ? "这次连麦" : "文字连麦"}</span>
          </div>
          <button
            className="summary-toggle"
            disabled={!hasChat}
            onClick={() => setPanel(panel === "summary" ? null : "summary")}
          >
            ▤ <span>本次小结</span>
            {stale && <i />}
          </button>
        </header>
        <div
          className={`reading ${hasChat ? "conversation" : ""}`}
          ref={scroll}
          onScroll={() => {
            const e = scroll.current;
            if (e)
              follow.current =
                e.scrollHeight - e.scrollTop - e.clientHeight < 100;
          }}
        >
          {!hasChat ? (
            <section className="welcome">
              <div className="welcome-icon">
                <Avatar small />
              </div>
              <h1>
                你最近，
                <br />
                在纠结什么？
              </h1>
              <p className="intro">
                说说你的处境，先从最纠结的地方开始。
                <br />
                不用组织得很完整，我们边聊边理清楚。
              </p>
              <div className="examples-heading">也可以从这些话题开始</div>
              <div className="examples">
                {examples.map((ex, i) => (
                  <button
                    key={ex.title}
                    disabled={!active}
                    onClick={() => {
                      if (active) update({ ...active, draft: ex.text });
                      input.current?.focus();
                    }}
                  >
                    <span className={`example-icon icon-${i}`}>
                      {["↗", "⇄", "✎"][i]}
                    </span>
                    <strong>{ex.title}</strong>
                    <p>{ex.detail}</p>
                  </button>
                ))}
              </div>
              <p className="identity">基于泡泡老师公开内容的 AI 视角体验</p>
            </section>
          ) : (
            <div className="messages">
              <div className="session-heading">
                <span>从你的处境开始</span>
                <span>
                  {new Date(active!.createdAt).toLocaleDateString("zh-CN")}
                </span>
              </div>
              {messages.map((m) => (
                <article
                  className={`message ${m.role}`}
                  key={m.id}
                  id={`message-${m.id}`}
                >
                  {m.role === "assistant" && <Avatar small />}
                  <div className="message-body">
                    <div className="speaker">
                      {m.role === "user" ? "你" : "泡泡老师"}
                      <span>
                        {m.status === "streaming"
                          ? "正在回复"
                          : m.status === "stopped"
                            ? "回复已停止"
                            : m.status === "error"
                              ? "回复未完成"
                              : ""}
                      </span>
                    </div>
                    {editing?.id === m.id ? (
                      <form
                        className="message-editor"
                        onSubmit={(e) => {
                          e.preventDefault();
                          send(false, editing);
                        }}
                      >
                        <label className="sr-only" htmlFor={`edit-${m.id}`}>
                          修改消息
                        </label>
                        <textarea
                          id={`edit-${m.id}`}
                          autoFocus
                          rows={5}
                          maxLength={12000}
                          value={editing.content}
                          disabled={busy}
                          onChange={(e) =>
                            setEditing({ ...editing, content: e.target.value })
                          }
                          onKeyDown={(e) => {
                            if (
                              e.key === "Enter" &&
                              (e.metaKey || e.ctrlKey) &&
                              !e.nativeEvent.isComposing
                            ) {
                              e.preventDefault();
                              send(false, editing);
                            }
                          }}
                        />
                        <p>
                          从这里重新回答。原消息、后续对话和小结会保存在历史记录的“修改前”副本中。
                        </p>
                        <div className="edit-actions">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => {
                              setEditing(null);
                              input.current?.focus();
                            }}
                          >
                            取消
                          </button>
                          <button
                            type="submit"
                            className="primary"
                            disabled={
                              busy ||
                              summaryBusy ||
                              !configured ||
                              !editing.content.trim() ||
                              editing.content.trim() === m.content
                            }
                          >
                            保存并重新回答
                          </button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <div className="message-text">
                          {m.content ||
                            (m.status === "streaming"
                              ? "正在想你的问题…"
                              : "尚未收到回复")}
                        </div>
                        {m.content && m.status !== "streaming" && (
                          <div
                            className="message-actions"
                            aria-label="消息操作"
                          >
                            <time
                              dateTime={new Date(m.createdAt).toISOString()}
                              title={new Date(m.createdAt).toLocaleString(
                                "zh-CN",
                              )}
                            >
                              {new Date(m.createdAt).toLocaleTimeString(
                                "zh-CN",
                                {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                  hour12: false,
                                },
                              )}
                            </time>
                            <button
                              type="button"
                              className="message-action"
                              aria-label={copied === m.id ? "已复制" : "复制"}
                              data-tooltip={copied === m.id ? "已复制" : "复制"}
                              onClick={() => copyMessage(m)}
                            >
                              <MessageIcon
                                kind={copied === m.id ? "check" : "copy"}
                              />
                            </button>
                            {m.role === "user" && (
                              <button
                                type="button"
                                className="message-action"
                                aria-label="修改"
                                data-tooltip="修改"
                                disabled={
                                  busy ||
                                  summaryBusy ||
                                  !!editing ||
                                  !configured
                                }
                                onClick={() => {
                                  follow.current = false;
                                  setEditing({ id: m.id, content: m.content });
                                }}
                              >
                                <MessageIcon kind="edit" />
                              </button>
                            )}
                          </div>
                        )}
                      </>
                    )}
                    {(m.status === "stopped" || m.status === "error") &&
                      m.id === messages.at(-1)?.id && (
                        <button
                          className="text-button"
                          disabled={
                            busy || summaryBusy || !!editing || !configured
                          }
                          onClick={() => send(true)}
                        >
                          重新回复
                        </button>
                      )}
                  </div>
                </article>
              ))}
              {sources.length > 0 && (
                <button
                  className="source-trigger"
                  onClick={() => setPanel("sources")}
                >
                  ↗ 相关公开内容 <span>{sources.length}</span>
                </button>
              )}
            </div>
          )}
        </div>
        <div className="composer-wrap">
          {notice && (
            <div className="notice" role="alert">
              {notice}
            </div>
          )}
          {configured === false && (
            <div className="configuration" role="status">
              <span>服务尚未配置，暂时无法开始连麦。</span>
              <button onClick={() => setPanel("settings")}>查看说明</button>
            </div>
          )}
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
          >
            <label className="sr-only" htmlFor="message-input">
              {hasChat ? "补充你的情况" : "说说你的困惑"}
            </label>
            <textarea
              ref={input}
              id="message-input"
              disabled={!active || !!editing}
              rows={3}
              maxLength={12000}
              value={active?.draft || ""}
              placeholder={
                hasChat
                  ? "补充你的情况，或者说说你现在的想法…"
                  : "比如：做了五年运营，想转 AI 产品，但一直在学工具，还没做出项目。"
              }
              onChange={(e) =>
                active && update({ ...active, draft: e.target.value })
              }
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <div className="composer-bottom">
              <span>
                Enter 发送 <b> / </b> Shift + Enter 换行
              </span>
              {busy ? (
                <button
                  type="button"
                  className="primary stop"
                  onClick={() => abort.current?.abort()}
                >
                  ■ 停止回复
                </button>
              ) : (
                <button
                  type="submit"
                  className="primary"
                  disabled={
                    !configured ||
                    !active?.draft.trim() ||
                    summaryBusy ||
                    !!editing
                  }
                >
                  {hasChat ? "发送" : "开始聊"} <span>↗</span>
                </button>
              )}
            </div>
          </form>
          <p className="privacy-note">
            记录保存在这台设备；发送时，对话内容将交由 DeepSeek 处理。
          </p>
        </div>
      </main>
      {panel && (
        <>
          <button
            className="panel-scrim"
            aria-label="关闭侧栏"
            onClick={() => setPanel(null)}
          />
          <aside
            className="drawer"
            ref={panelRef}
            tabIndex={-1}
            aria-label={
              panel === "summary"
                ? "本次小结"
                : panel === "sources"
                  ? "相关公开内容"
                  : "记录与隐私"
            }
            onKeyDown={(e) => {
              if (e.key !== "Tab") return;
              const nodes = panelRef.current?.querySelectorAll<HTMLElement>(
                "button:not(:disabled), a, textarea",
              );
              if (!nodes?.length) return;
              const first = nodes[0],
                last = nodes[nodes.length - 1];
              if (
                e.shiftKey &&
                (document.activeElement === first ||
                  document.activeElement === panelRef.current)
              ) {
                e.preventDefault();
                last.focus();
              } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
              }
            }}
          >
            <div className="drawer-header">
              <h2>
                {panel === "summary"
                  ? "本次小结"
                  : panel === "sources"
                    ? "相关公开内容"
                    : "记录与隐私"}
              </h2>
              <button
                aria-label="关闭侧栏"
                onClick={() => {
                  setPanel(null);
                  input.current?.focus();
                }}
              >
                ×
              </button>
            </div>
            <div className="drawer-content">
              {panel === "summary" ? (
                <>
                  <p className="drawer-intro">把聊清楚的事，带回真实生活。</p>
                  {stale && <p className="notice">小结有新内容可更新</p>}
                  {active?.summary ? (
                    fields.map(([key, label]) => (
                      <label className="summary-field" key={key}>
                        <span>{label}</span>
                        <textarea
                          value={active.summary![key]}
                          rows={key === "judgment" ? 6 : 4}
                          placeholder="待补充"
                          disabled={summaryBusy}
                          onChange={(e) =>
                            update({
                              ...active,
                              summary: {
                                ...active.summary!,
                                [key]: e.target.value,
                                edited: true,
                              },
                            })
                          }
                        />
                      </label>
                    ))
                  ) : (
                    <div className="summary-empty">
                      <span>▤</span>
                      <h3>聊到这里，理一理。</h3>
                      <p>
                        整理当前判断、待确认的事实，
                        <br />
                        以及可以开始的下一步。
                        <br />
                        信息还不完整，也没关系。
                      </p>
                    </div>
                  )}
                  {summaryError && (
                    <p role="alert" className="notice">
                      {summaryError}
                    </p>
                  )}
                  <button
                    className="primary full"
                    disabled={
                      busy ||
                      summaryBusy ||
                      !configured ||
                      !hasChat ||
                      !!editing
                    }
                    onClick={() => summarize()}
                  >
                    {summaryBusy
                      ? "正在整理…"
                      : active?.summary
                        ? "更新连麦小结"
                        : "整理这次连麦"}
                  </button>
                  {active?.summary && (
                    <>
                      <div className="summary-actions">
                        <button
                          onClick={async () => {
                            try {
                              await navigator.clipboard.writeText(
                                summaryText(),
                              );
                              setNotice("小结已复制。");
                            } catch {
                              setNotice("无法复制，请导出文本。");
                            }
                          }}
                        >
                          复制小结
                        </button>
                        <button
                          onClick={() =>
                            download("连麦小结.txt", summaryText())
                          }
                        >
                          导出文本
                        </button>
                      </div>
                      <p className="muted">
                        可以直接编辑，修改会自动保存在本机。
                      </p>
                      <details>
                        <summary>查看小结引用的对话</summary>
                        {active.summary.messageIds.map((id) => {
                          const m = messages.find((m) => m.id === id);
                          return m ? (
                            <p className="evidence" key={id}>
                              {m.role === "user" ? "你" : "泡泡老师"}：
                              {m.content}
                            </p>
                          ) : null;
                        })}
                      </details>
                    </>
                  )}
                </>
              ) : panel === "sources" ? (
                <>
                  <p className="drawer-intro">
                    与你聊的话题相关的公开材料。
                    <br />
                    并不代表每条材料都支持当前判断。
                  </p>
                  {sources.length ? (
                    sources.map((s) => (
                      <a
                        className="source-card"
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        key={s.id}
                      >
                        <small>{s.date} · Bilibili</small>
                        <h3>{s.title} ↗</h3>
                        <p>{s.quality}</p>
                      </a>
                    ))
                  ) : (
                    <p>暂时没有匹配的公开材料。</p>
                  )}
                </>
              ) : (
                <>
                  <h3>只在这台设备保存</h3>
                  <p>
                    会话、小结和草稿保存在当前浏览器。清除浏览器数据后无法恢复；不同浏览器之间不会同步。
                  </p>
                  <h3>生成时会发送什么</h3>
                  <p>
                    你发送后，相关对话会传给 DeepSeek
                    用于生成回复。首版没有联网搜索，也没有真实语音通话。
                  </p>
                  {!configured && (
                    <div className="configuration-help">
                      <h3>尚未配置回复服务</h3>
                      <p>
                        请由本地开发者在项目的 .env.local 中设置
                        DEEPSEEK_API_KEY，并重启服务。密钥只在服务端使用。
                      </p>
                    </div>
                  )}
                  <button
                    className="secondary full"
                    onClick={() =>
                      download(
                        "泡泡连麦记录.json",
                        JSON.stringify(sessions, null, 2),
                        "application/json",
                      )
                    }
                  >
                    导出全部本地记录
                  </button>
                  <button
                    className="danger full"
                    disabled={busy || summaryBusy}
                    onClick={() => requestDelete({ title: "全部本地记录" })}
                  >
                    删除全部本地记录
                  </button>
                </>
              )}
            </div>
          </aside>
        </>
      )}
      <dialog
        ref={summaryDialog}
        className="delete-dialog"
        aria-labelledby="summary-dialog-title"
        aria-describedby="summary-dialog-description"
        onCancel={() => setSummaryConfirm(false)}
      >
        <h2 id="summary-dialog-title">更新连麦小结？</h2>
        <p id="summary-dialog-description">
          新小结将替换你编辑过的内容，旧版仍会随会话保留在导出记录中。
        </p>
        <div className="delete-dialog-actions">
          <button
            type="button"
            className="secondary"
            autoFocus
            onClick={() => setSummaryConfirm(false)}
          >
            取消
          </button>
          <button
            type="button"
            className="primary"
            onClick={() => summarize(true)}
          >
            确认更新
          </button>
        </div>
      </dialog>
      <dialog
        ref={deleteDialog}
        className="delete-dialog"
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
        onCancel={(e) => {
          e.preventDefault();
          if (!deleteLock.current) setDeleteTarget(null);
        }}
      >
        <h2 id="delete-dialog-title">
          {deleteTarget?.id ? "删除这场连麦？" : "删除全部本地记录？"}
        </h2>
        <p className="delete-dialog-name">{deleteTarget?.title}</p>
        <p id="delete-dialog-description">
          {deleteTarget?.id
            ? "这场连麦的对话和小结将被永久删除，无法恢复。"
            : "全部本地对话和小结将被永久删除，无法恢复。建议先导出记录。"}
        </p>
        {deleteError && (
          <p role="alert" className="delete-dialog-error">
            {deleteError}
          </p>
        )}
        <div className="delete-dialog-actions">
          <button
            type="button"
            className="secondary"
            autoFocus
            disabled={deleting}
            onClick={() => setDeleteTarget(null)}
          >
            取消
          </button>
          <button
            type="button"
            className="delete-confirm"
            disabled={deleting}
            onClick={confirmDelete}
          >
            {deleting ? "正在删除…" : "确认删除"}
          </button>
        </div>
      </dialog>
    </div>
  );
}
