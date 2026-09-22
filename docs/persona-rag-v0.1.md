# Persona RAG v0.1

> 2026-09-23 已扩展到 345 份可用视频、1,794 个单元，另 8 份弱证据隔离。下文首批数据和 Top 12 描述为初版记录；当前加工方式、Top 40 检索配置和限制见 [全量入库说明](persona-rag-full-ingestion.md)。

## 现有流程与改动范围

前端 `app/page.tsx` 将消息 POST 到 `app/api/chat/route.ts`。`lib/context.ts` 加载原始 `paopao-perspective-skill/SKILL.md`、`references/expression-dna.md` 和主题 framework；`lib/server.ts` 调用 DeepSeek Flash，聊天路由将内容流回前端。浏览器 `lib/storage.ts` 的 IndexedDB 保存会话、草稿、小结和小结旧版；服务端使用本轮传入的已完成历史，没有新增长期记忆。

原先每轮都在 Context Builder 里读卡片、跑关键词匹配，读取失败会使整轮请求失败。现在只替换该检索段，Skill 文件、前端布局、存储及小结接口未改写。

## 数据与真实性

- 编辑清单：`data/rag/units.json`。第一批 **7 个语义单元：1 场完整 qa_case、6 个 viewpoint，来自 5 条视频**，不是全部 353 条视频的全量索引。
- 原始内容：`paopao-perspective-skill/references/sources/bilibili/transcripts/clean/<BVID>.md`。
- 元信息与质量：同目录上层的 `corpus-index.json`，以及 `video-cards/<BVID>.md` 的证据限制。
- 生成索引：`data/rag/index.json`。包含实际字幕文本，已加入 Git 忽略并排除公开分发；绝不放入 public。

Skill 和研究者总结不作为原话知识库。每条 `content` 是指定连续字幕编号范围的原文（去掉重复时间标签，保留编号），标题、claim、context 明确标为编辑转述。来源记录原文件路径、SHA-256、时间范围、字幕编号、字幕/OCR 质量和限制。

连麦案例保留从开场到道别的完整讨论。`question` 是开场提问字幕，`answer` 是老师结论段的摘录；完整问答往返在 `content`，不能将其中全部第一人称归于老师。说话人边界按文本核对，**尚未逐句回看音视频**，不宣称人工校正原话。

观点按完整论点/讨论标范围；脚本不做固定 token 切块，超预算时拒绝构建该单元，要求重新标注语义边界。缺失原文或质量不合格会明确记录 skipped，不拿卡片摘要冒充字幕填进去。字幕编号缺失、QA 摘录越界、非法清单会中止构建，旧索引保持不变。

## 构建、更新、开关

在项目根目录：

```sh
pnpm rag:build
pnpm rag:debug -- "泡泡以前讲过输出型学习吗？"
pnpm rag:eval
```

更新清单的 BVID、语义范围、问题/回答片段、主题与限制，再运行 `pnpm rag:build`。写入临时文件后原子替换索引；运行服务按修改时间/大小自动加载新版，读取失败不会永久缓存。构建摘要包含数量、跳过原因与输入哈希。默认命令会加载 `.env.local`。

在 `.env.local` 中设置：

```dotenv
RAG_ENABLED=true
RAG_DEBUG=false
# 可选：RAG_INDEX_PATH=data/rag/index.json
```

`RAG_ENABLED=false` 是纯 Skill + 历史 + LLM：不读取索引，不走旧版卡片检索。默认开启；环境变量变更后重启服务。未构建索引也能聊天。

公开源码包不含原字幕和生成索引。没有本地原始素材时，构建会列出 skipped，聊天退回 Skill-only；不声称公开包自带完整 RAG 原文。

## 一次请求的实际路径

1. 聊天路由校验请求，并分开最新 query 和旧消息；此前把最近四条用户消息直接拼成 query 的做法不再用于触发判断。
2. 根据最新 query 的主题/来源追问规则判断；“谢谢”“今天好累”不因旧职业话题而检索。指代型追问可借最近两条历史补主题。
3. 开启且值得检索时读取本地索引。使用 Node 内置中文分词、词内双字项与英文词，执行 BM25；没有下载 embedding 模型或调用向量 API。
4. 取 Top 12，按查询对标题/问题/背景/观点的 IDF 加权覆盖率、BM25 饱和分数和主题匹配重排。未知查询词仍计入覆盖率分母，防止陌生具体事实被泛化为某个相同关键词。
5. 只选 score ≥ 0.40、coverage ≥ 0.26、至少 2 个匹配项的证据；最多 3 条、每视频最多 2 条、序列化证据总计不超过 24000 字符，不截断单元。所有阈值集中在 `lib/rag/config.ts`。**分数是词项相关度，不是证据置信概率。**
6. Context Builder 合并应用要求、原 Skill/DNA/framework、可选 evidence，再由路由附上已有原始消息和最新问题，调用原来的 DeepSeek Flash 流式接口。
7. 来源继续复用现有“相关公开内容”入口。仅给传入上下文的来源；内部 trace 随消息 metadata 保存，不增加用户界面。

关闭、不触发、空结果、低相关、缺文件、坏 JSON、模式错误和读取超时都会继续正常生成。检索超时预算 1200ms。Skill 本身缺失、LLM 网络/API 故障仍按原有错误处理，不伪造成功。

## 对话与证据边界

应用追加规则覆盖 Skill 中旧的“未知问题先说明没有公开答案”话术，而不改写 Skill。普通问题自然融合已有知识，不因 RAG 状态改变开场或格式。只有明确追问历史说法/出处时才按证据回答；无直接依据就说当前素材没有找到，而不是说本人绝对没讲过。相关案例不等于当前具体个案的直接答案。机器文本只能谨慎转述，不能冒充已听录音核对的精确原话。

## Debug 与验证

`RAG_DEBUG=true` 且非生产时，服务端仅打印 `rag_triggered`、reason、retrieved_count、selected_count、来源/单元 ID、BM25/coverage/score 和选中标志；不打印用户 query、原文、prompt 或密钥。要查看 query → 候选 → 筛选 → 内容片段，用 `rag:debug` CLI。CLI 是显式本地调试，不对外开 debug HTTP 接口。

```sh
pnpm test
pnpm typecheck
pnpm build
python3 tests/release-packaging.test.py
pnpm rag:eval
# 五个合成问题，实际调用现有 DeepSeek，产生正常 API 用量：
pnpm rag:eval --live
```

`rag:eval` 默认只验证真实本地索引；`--live` 复用相同 Context Builder 与流式 LLM 调用，保存五题输出到 `.local-archive/persona-rag/live-latest.json`。这些是测试问题，不读取个人历史。完整工程测试还覆盖关闭不读文件、闲聊不读文件、低相关过滤、文件损坏/修复、超时、来源边界和聊天 API 的 fail-open 流程。

## 限制

v0.1 有意从小批明确边界材料开始，1 个连麦案例不足以代表所有职业问题。词项检索没有稠密语义向量，改写和同义词召回有限；阈值只经过这批样本调试。以后可替换 `search/loadIndex` 而无需改聊天接口。

未实现自动说话人分离、自动批量切分 353 条视频、音视频人工校正、事实核验或逐句生成后引用验证。模型有证据也可能错误归因；提示约束和小样本验收不等于形式保证。涉及最新公司、工资和工具状态仍须另行查证。
