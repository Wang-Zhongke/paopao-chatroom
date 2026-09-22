# 执行记录

2026-09-18。用户明确授权外发指定资料及提高 token 上限。没有发布 GitHub；没有修改 SKILL.md 或领域框架。

## 实际调用

- 模型请求与返回 ID：`deepseek-flash`。服务未提供不可变权重版本，因此不能声称严格复现同一权重快照。
- 两臂统一 `max_tokens=8192`、`reasoning_effort=low`、`stream=false`，温度等未指定参数使用服务默认值。
- ON：共享顾问任务 + SKILL.md、表达 DNA、六份领域框架。OFF：仅共享顾问任务。均无联网工具，不发送预期检查点。
- 输入文档哈希和题目哈希与原冻结批次完全一致；与 2200 token 批次隔离，不混用旧回答。
- 先跑 R01 配对，完整后继续其他 11 题；两个并发。12 题含 3 道双轮纠正，总计 24 个完整 arm、30 次有效响应，所有最终回答 finish_reason=stop。
- 首轮 R10 ON 在 41.37 秒发生 RemoteDisconnected，没有响应体。仅对该项补试一次并成功，原记录保存在 answer-R10-on-attempt1.json。总网络尝试 31 次。冻结 config 中的 no retries 描述是初始协议，本条明确记录唯一偏离；不隐去故障。
- run-summary.json 统计最终选用的 30 个响应，不包括无响应的首次失败。可见用量：输入 181,268、输出 62,937、合计 244,205 token。未知失败请求是否被计费，实际账单以服务商为准。未估算金额。
- HTTPS 使用系统 CA `/etc/ssl/cert.pem`，没有关闭证书校验。未保存认证头或密钥。

## 评审及适用范围

独立上下文 Judge 只拿到 X/Y 盲包、题目检查点和评分协议，不读取 Skill、臂名映射或先前回答。输出可泄露风格，因此这是匿名配对、单 Judge 评审，不是完全双盲实验。

这是新版本 12 题小样本产品价值测试，不是旧请求中的 65 题全量门禁，也没有重跑已清理的旧 Phase 5 行为回归。没有原语料对照评分，不能计算 known-position accuracy 或证明人物声音忠实度。统一注入全部框架，没有真实文件选择/工具路由记录，因此 model routing accuracy 为 N/A。无联网工具，不可计算 unnecessary research 的发生率。

本次按同预算比较，不等于同成本：ON 额外输入文档明显增加 token。每题仅运行一次，尚无多 seed、多模型、多 Judge 或真人泡泡老师观众评分。

## 本地回归

- validate_skill_content.py：8 项通过（结构、字段、链接检查，不是人物行为准确率）。
- tests/release-packaging.test.py：4 项通过。
- 应用 tests/*.test.ts：5 项通过。
- 评测与渲染脚本 Python 语法检查通过。
- SKILL.md SHA256：5236676eb916fc74bc81de04d1569a3bc593d53ccd37c7954882f30d24a0f25c。

rc2 ZIP 仍为此前快照；本次评测文件在工作目录，没有自动重打包、Git 提交或推送。
