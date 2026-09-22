# 人物视角 A/B 评测

12 道单轮题、24 条完整模型回答。两组使用相同人物模拟指令，仅一组额外加载 Skill。两名独立上下文评审分别在 10/12、12/12 题偏好 Skill 组，四维均分 3.46 对 2.66；这是小样本观察，不是本人认证。

[评测报告](run/EVAL-REPORT.md) · [逐题回答与评分](run/CASE-INDEX.md) · [实验设置](run/EXECUTION.md)

## 实验材料

- [共享指令](shared-system.txt)、[12 道题目](holdout.jsonl)、[评测协议](PROTOCOL.md)。
- [评审参考](judge-reference.md)、[来源与哈希](reference-manifest.json)。参考材料仅供评审，不发送给回答模型。
- `run/` 保存正式实验的输入快照、回答、评分、盲包、映射及指标。原始记录保持不变。

## 重跑回答生成

需要 Python 3.10+。独立 Skill 仓库在根目录运行；连麦室仓库先执行 `cd paopao-perspective-skill`，再使用相同命令。

先验证输入，不联网、不使用密钥：

```sh
python3 scripts/eval_persona.py --output .local-evals/input-check
```

真实调用前，在环境变量 `DEEPSEEK_API_KEY` 或当前 Skill 根目录的 `.env.local` 中配置自己的密钥，然后使用另一个不存在的输出目录：

```sh
python3 scripts/eval_persona.py --run --pilot-first --output .local-evals/new-run
```

默认使用已保存的 Skill 输入快照、共享指令和 8192 token 上限；`--current-skill` 可用于评估当前文件。每次必须选择新目录，避免覆盖已有实验；真实调用预计 24 次模型请求并产生费用。`.local-evals` 不应提交到 Git。

上述命令只重跑回答生成，不会自动复现两名独立评审。新回答需按协议重新盲评；模型服务的版本和采样变化也可能使结果不同。完整评审条件与限制见报告。
