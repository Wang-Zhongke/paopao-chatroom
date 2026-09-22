export type Source = {
  id: string;
  title: string;
  url: string;
  date: string;
  quality: string;
};
export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  status: "complete" | "streaming" | "stopped" | "error";
  sources?: Source[];
  meta?: Record<string, unknown>;
};
export type Summary = {
  decision: string;
  judgment: string;
  unknowns: string;
  actions: string;
  messageIds: string[];
  basedOn: string;
  edited: boolean;
  evidence: {
    text: string;
    messageIds: string[];
    kind: "user-stated" | "inference" | "project-evidence" | "action-feedback";
    supersedes?: string;
  }[];
};
export type Session = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  topic: string;
  messages: Message[];
  summary?: Summary;
  summaryHistory?: Summary[];
  draft: string;
};
