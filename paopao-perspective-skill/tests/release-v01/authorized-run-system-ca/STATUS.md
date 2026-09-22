# 已授权运行：中止，不能计分

2026-09-18 用户明确授权将 Skill、Expression DNA、六份框架及 12 道虚构测试发送给 DeepSeek，执行约 30 次付费请求。未授权发布 GitHub。

首次授权运行 `../authorized-run/` 仍在 TLS 校验处失败。无认证首页诊断确认 Python 默认 CA 缺失；采用 `SSL_CERT_FILE=/etc/ssl/cert.pem` 后 HTTPS 校验正常。没有禁用证书校验。

本目录保存实际 DeepSeek 回答。运行中发现 `max_tokens=2200` 包含推理 token，三个 baseline 回答均因 `finish_reason=length` 截断。因此主动中止本轮，避免继续消耗不适合比较的请求；不是接口不支持模型，也不是 Skill 的能力结论。

已保存 6 个 arm、8 次 API 响应：R02 ON、R03 ON（各两轮）和 R12 ON 完整；R08 OFF、R09 OFF、R11 OFF 截断。没有任何完整配对，不能计算 ON/OFF 胜率，未执行 Judge。中止前若有尚未落盘请求，服务商仍可能计费；本地统计不是账单。

已保存响应用量：prompt_tokens 59,875；completion_tokens 12,199；total_tokens 72,074。模型响应为 `deepseek-flash`。未将费用换算成金额。

建议另开冻结批次，两臂统一提高 token 上限（例如 8,192），保持题目、上下文和其他参数不变。先用一个配对检查完整性，再完成剩余问题；不把本批次的不完整回答混入正式评分。重跑会产生额外 API 费用，尚未执行。

核心 Skill 和框架没有修改。此前 rc2 ZIP 是本次执行前的快照，未重新打包。
