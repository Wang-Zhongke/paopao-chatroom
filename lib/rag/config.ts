import path from "node:path";
// All retrieval/corpus budgets live here. Scores are lexical relevance, not probabilities.
export const RAG_CONFIG = {
  version: "persona-rag-v0.1",
  indexVersion: 1,
  topK: 40,
  maxEvidence: 3,
  minCoverage: 0.26,
  minScore: 0.4,
  minRelativeScore: 0.75,
  compactEvidenceScoreTolerance: 0.03,
  minMatchedTerms: 2,
  maxPerSource: 2,
  maxUnitChars: 18000,
  maxContextChars: 24000,
  maxQueryChars: 2000,
  maxIndexBytes: 64 * 1024 * 1024,
  timeoutMs: 1200,
  bm25: { k1: 1.2, b: 0.75, scale: 10 },
  weights: { coverage: 0.65, bm25: 0.25, topic: 0.1 },
};
export function ragSettings() {
  return {
    enabled: process.env.RAG_ENABLED !== "false",
    debug:
      process.env.RAG_DEBUG === "true" && process.env.NODE_ENV !== "production",
    indexPath: path.resolve(
      process.cwd(),
      process.env.RAG_INDEX_PATH || "data/rag/index.json",
    ),
  };
}
export const TOPICS: [string, RegExp][] = [
  [
    "career",
    /职业|工作|求职|招聘|跳槽|转行|转型|学历|岗位|简历|面试|offer|薪资|手牌|销售/i,
  ],
  ["AI_PM", /\bai\b|人工智能|agent|mcp|产品经理|AI产品|AI求职/i],
  [
    "learning",
    /学习|读书|输出型|输入型|成功记忆|成长|工具|练习|培训|探索|以教代学|困难模式/i,
  ],
  ["product", /产品|项目|设计|用户|交互|作品|需求/i],
  ["business", /创业|商业|生意|客户|付费|老板|团队|管理|生产资料|控制权/i],
  ["brand", /自媒体|内容创作|品牌|流量|创作者/i],
];
export const getTopics = (query: string) =>
  TOPICS.filter(([, re]) => re.test(query)).map(([name]) => name);
