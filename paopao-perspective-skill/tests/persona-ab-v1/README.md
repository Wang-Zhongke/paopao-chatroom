# 人物模拟 A/B v1

状态：**完成。24次响应全部完整，两名独立Judge分别在10/12和12/12题偏好Skill；四维均分ON 3.46、OFF 2.66（0–5）。本轮支持人物还原度增益，非高保真认证。**

**[完整评测报告](run/EVAL-REPORT.md) · [12题完整回答与评分](run/CASE-INDEX.md) · [执行与隔离记录](run/EXECUTION.md)**

下方审批阻塞为历史记录，不再表示尚未调用。

两组使用同样人物模拟指令，A仅凭模型自带知识，B额外加载当前Skill、表达DNA和六份框架。共享指令见 `shared-system.txt`；完整协议见 [PROTOCOL.md](PROTOCOL.md)。这次不沿用普通顾问标准。

- [12道冻结问题](holdout.jsonl)：8 known、4 transfer，均单轮。
- [Judge原始参考](judge-reference.md)：8条视频机器字幕的原始片段和上下文；仅供独立Judge，不发送给DeepSeek回答模型。
- [来源与哈希](reference-manifest.json)：未在注入文档中显式引用所选BVID，不代表研究史或训练集从未见过。
- [无网络冻结检查](input-review/config.json)：已核对外发目的地、8份文档、共享指令及8192上限；run_requested=false。

首次提交和复核均被自动审批拒绝。随后再次明确询问外发与付费，用户答“允许”，同一命令获准执行。没有换路径、换工具或绕过拒绝。24个请求均成功，无补试。两名独立Judge已完成基于真实字幕参照的四维人物忠实度评分，原始结果和分歧完整保留。

已获批范围：向 `https://api.deepseek.com/chat/completions` 发送当前SKILL.md、expression-dna.md、六份framework与12道测试题，使用现有API key，预计24次付费请求（失败项最多补试一次）。不发送原始字幕/视频、完整语料、真实简历或浏览器数据。

运行命令（外层仓库根目录；须先获准）：

```sh
SSL_CERT_FILE=/etc/ssl/cert.pem python3 scripts/eval_release.py --run --max-tokens 8192 --pilot-first --cases-file paopao-perspective-skill/tests/persona-ab-v1/holdout.jsonl --base-system-file paopao-perspective-skill/tests/persona-ab-v1/shared-system.txt --output paopao-perspective-skill/tests/persona-ab-v1/run
```

本轮未修改Skill、框架或研究语料，未发布GitHub。
