# 人物模拟 A/B：预先冻结的评测协议

目的：相同模型和同样人物模拟指令下，加载当前 Skill 是否提高人物观点、思考路径和表达还原度。不是通用职业顾问能力竞赛。

## 回答生成

两臂均直接请求 DeepSeek API，不经过 Codex Skill 自动发现。共享 system 指令原文见 shared-system.txt。

A/OFF：仅共享指令+问题；不提供 Skill、参考字幕、工具或文件访问。
B/ON：共享指令+冻结的 SKILL.md、expression-dna、六领域框架+同一个问题。

模型 deepseek-flash，reasoning_effort=low，max_tokens=8192，stream=false。其他参数用服务默认值；每个请求独立，答案不共享。不额外让 A/B 看到来源参考、评分要点或另一个答案。先一对完整性检查，再运行剩余题；12 道单轮题，预计24次付费请求，服务失败最多补试一次且保留首轮。无工具但可能有预训练人物知识，这正是 baseline。

此前普通顾问对照与本批次不混算，也不依据结果修改 Skill。

## 题目与参考

独立 Agent 从本地机器字幕选8道已知话题、4道新场景迁移题。参考包仅交给 Judge。避开当前注入文档中显式引用的 BVID，具体重叠记录以 manifest 为准；整个既有研究史可能已见过资料，不宣称严格的未见训练语料 holdout。题目不是原听众逐字发问时须标为改写。AI/OCR字幕未逐字人工核音，不能据此证明语音语调或逐字准确性。

## Judge 评分

Judge使用独立上下文，只读本协议、原始字幕参考包和随机X/Y盲包。不读Skill、ON/OFF请求文件、映射密钥或旧分数。必须基于参考证据，不凭自己印象定义泡泡老师。

每候选四项0–5，等权：

1. position_fidelity：观点方向、取舍与适用条件是否接近原始参考；transfer题评有证据支持的延伸，不要求猜中本人唯一答案。
2. reasoning_fidelity：如何切入、拆前提、组织因果、举例类比和回到结论，是否接近可观察的原始路径。
3. expression_fidelity：口语节奏、直接程度、反问、例子与收束是否接近参考，不按口头禅数量/温和程度/篇幅评分。
4. persona_specificity：是否保留有依据的人物偏好和特点，而非任意顾问/泛化网红腔或夸张的刻板印象。

0=明显相反或无关，1=仅表面标签，2=部分贴近但重大偏差，3=总体方向贴近但不稳定，4=多项有据贴近，5=高度贴近且细微取舍也保留。分数不是客观概率。

人物真实的直接、偏见、强判断、商业取向、不全面，都不能因Judge不赞同而自动扣分。人物风格不是编造事实或本人经历的许可证；这种问题单列，不拿通用顾问分数替代忠实度。不要把roleplay中的第一人称本身判为违规。

每题输出 id、candidates.X/Y（scores上述四项、reason、reference_evidence数组[原片段ID/时间戳与对应理由]、flags{unsupported_public_quote_or_memory:boolean,contradicts_reference:boolean,caricature_without_support:boolean}、failure_reason）、preference X/Y/tie、reason。只能在参考足以支持时扣分；证据不足要在理由写清楚。数据存 blind-judge.jsonl，并写 JUDGE-NOTES.md说明限制和案例索引。

偏好由人物忠实度决定，不由通用可执行性或语气礼貌决定。报告分别统计known/transfer、四维均分和偏好。至少两名独立Judge各自评分，第二名不读第一名结果；不强行调和分歧。主Agent之后解盲并生成完整可读案例。

本轮不预设一定胜出。输出为人物模拟质量的探索性证据，不是本人认证；单次抽样、机器字幕和模型Judge限制必须保留。
