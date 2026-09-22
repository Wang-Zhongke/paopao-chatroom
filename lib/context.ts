import { readFile } from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import type { Source } from "./types";
import { retrieve, evidenceContext, type PriorMessage } from "./rag/retrieve";
const root = path.join(process.cwd(), "paopao-perspective-skill");
const read = (file: string) => readFile(path.join(root, file), "utf8");
const topics: [RegExp, string][] = [
  [/AI|人工智能|转型|工具|产品经理|agent|mcp/i, "ai-career"],
  [/offer|面试|简历|求职|招聘|薪资/i, "job-evaluation"],
  [/内容|自媒体|品牌|流量|视频/, "personal-brand"],
  [/设计|产品|用户|交互|UI|UX/i, "design-product"],
  [/创业|商业|管理|老板|团队|生意/, "business"],
  [/职业|工作|跳槽|转行|运营|行业/, "career"],
];
export async function buildContext(
  query: string,
  history: PriorMessage[] = [],
  options: Parameters<typeof retrieve>[2] = {},
) {
  const frameworkQuery = [
    ...history
      .filter((m) => m.role === "user")
      .slice(-3)
      .map((m) => m.content),
    query,
  ].join("\n");
  const [skill, dna, rag] = await Promise.all([
    read("SKILL.md"),
    read("references/expression-dna.md"),
    retrieve(query, history, options),
  ]);
  const frameworks = topics
    .filter(([re]) => re.test(frameworkQuery))
    .map(([, name]) => name);
  if (!frameworks.length) frameworks.push("career");
  const extra = await Promise.all(
    frameworks.map((f) => read(`references/${f}-framework.md`)),
  );
  const sources: Source[] = [
    ...new Map(
      rag.evidence.map(({ unit }) => [
        unit.source.id,
        {
          id: unit.source.id,
          title: unit.source.title,
          url: `https://www.bilibili.com/video/${unit.source.id}/`,
          date: unit.source.date,
          quality:
            unit.source.quality === "machine-ocr"
              ? "画面文字识别，未逐句校正"
              : "机器字幕，未逐句校正",
        },
      ]),
    ).values(),
  ];
  const base =
    "应用交互要求优先：你是公开资料蒸馏的 AI 视角体验，不冒充本人现实身份。采用第一人称口语表达判断，不把素材中的讲者经历说成自己亲历，不编造“我见过/我教过”的经历。简单情绪交流先承接感受，不把疲惫等同努力或价值，不强行拆前提、审问或推断动机。先回应具体事实，给有用观察，必要时只追问一个关键变量；不要机械否定合理前提。使用新增事实，纠正时修改判断，不重复追问。用户要结论时明确当前倾向和可能反转的未知事实。用户不知道时提供获取信息的动作。允许转向新话题。短段落，不套报告模板。没有联网能力；最新事实留待核验。用户陈述与推测分开。未完成回复不是既定判断。";
  return {
    sources,
    rag: rag.trace,
    version: createHash("sha256")
      .update(skill + dna + extra.join(""))
      .digest("hex")
      .slice(0, 12),
    system: `${base}\n${skill}\n${dna}\n${extra.join("\n")}\n应用补充要求（优先于资料中的旧回退话术）：\n${base}\n${evidenceContext(rag)}`,
  };
}
