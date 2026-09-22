# 安装与首次使用

## 下载哪一份

只想使用人物 Skill：选择 `paopao-perspective-skill-v0.1.0.zip`，解压后找到含有 `SKILL.md` 的文件夹。想运行网页连麦室：使用完整项目源码包，按其根目录 README 启动。

本项目不要求先安装 Nuwa。人物 Skill 由宿主模型运行；字幕、OCR 和视频下载脚本只服务研究，不是运行依赖。

## Codex 本地安装

在解压后的 Skill 文件夹打开终端：

```sh
python3 scripts/install.py
```

需要 Python 3.10 或以上，无须额外安装 Python 包。默认目标是个人目录下 `.agents/skills/paopao-perspective-skill`。目标已存在时安装器会停止，避免覆盖自己的修改。

也可以手动将完整 Skill 文件夹复制到 `.agents/skills`，最终布局应是：

```text
.agents/skills/paopao-perspective-skill/SKILL.md
.agents/skills/paopao-perspective-skill/references/
```

Codex 当前官方本地目录是个人或项目的 `.agents/skills`，见 [官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills)。某些旧版环境仍使用 `.codex/skills`；请按宿主显示的实际 Skill 根目录安装，避免同名副本同时出现。

指定其他完整目标目录：

```sh
python3 scripts/install.py --destination /absolute/path/to/skills/paopao-perspective-skill
```

安装器的验证范围是临时目录中的复制、拒绝覆盖和安装后文件检查；不代表全部客户端版本的自动发现都已验证。

## 首次调用

在 Codex CLI / IDE 中用 `$` 选择该 Skill，或输入：

```text
使用 $paopao-perspective-skill。
我有四年 B 端设计经验，现在考虑一个需要直接访谈客户的产品岗位。
薪资相同，但工作内容不同。先帮我判断需要问清哪些关键事实。
```

若宿主没有出现此 Skill，先确认 `SKILL.md` 的目录层级，再刷新或重启宿主。在提供 Skill 选择器的桌面版本中，也可用界面直接选择。仅粘贴调用语句而未安装文件，不会自动获得框架和资料。

## 常见问题

**需要 DeepSeek API key 吗？** 使用 Skill 本身不需要；使用网页连麦室或运行 DeepSeek 对照评测需要。

**可以只复制 SKILL.md 吗？** 不建议。正文引用了表达 DNA 和领域框架，保留整个轻量包才能得到完整行为。

**能联网核验薪资、公司和新闻吗？** 取决于宿主工具。无联网工具时应提供当前资料，不把模型记忆当作实时检索。

**Claude Code 或其他 Agent 能用吗？** 文件使用常见 Skill 结构，但本轮没有进行这些客户端的端到端验证。按其官方文档安装，并报告版本与实际行为。

**怎么更新？** 先备份已有目录，再比较新版；安装器不会自动删除或覆盖旧版。

**怎么移除？** 在宿主中禁用，或将这个 Skill 的单独目录移出 Skill 根目录即可。

## 本地检查

```sh
python3 scripts/validate_skill_content.py
```

检查文件、引用和结构，不需要外部 skill-creator 路径。通过不等于人物保真度或职业建议质量已被证明。
