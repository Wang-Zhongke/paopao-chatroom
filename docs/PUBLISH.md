# v0.1 发布候选说明

当前完成本地发布准备，不代表已经上传 GitHub。最新[人物模拟评测](../paopao-perspective-skill/tests/persona-ab-v1/run/EVAL-REPORT.md)在12题、两名独立Judge中观察到相对模型自行模拟的还原度增益；此前[通用顾问对照](../paopao-perspective-skill/tests/release-v01/token8192-run/EVAL-REPORT.md)未胜出。可准确描述实验条件与结果，不应笼统宣传“全面优于baseline”“高保真已验证”。正式发布时从当前源码重新构建 ZIP，不使用历史 rc2 包。

本轮工程与独立阅读审查记录见 [发布检查](RELEASE-CHECK.md)。

## 公开什么

- `paopao-perspective-skill-v0.1.0.zip`：可安装的 Skill、框架、研究摘要、来源卡与必要索引。
- `paopao-room-source-v0.1.0.zip`：网页源码及同一公开 Skill 资料。
- 两个包各自附 `MANIFEST.json`，记录文件哈希、资料净化和链接变换。

不分发完整字幕、OCR、原视频、抓取 API 原始响应、密钥、原有本地头像或嵌套 Git 元数据。README 截图展示使用者提供的本地头像，但头像原文件不随包提供。公开材料的摘要与原文引用分别保留归属。详见 [第三方声明](../THIRD_PARTY_NOTICES.md)。

## 构建与检查

在工作区根目录运行，输出路径必须是不存在或为空的绝对目录：

```sh
python3 scripts/build_release.py --output /absolute/path/to/new-release-directory
python3 scripts/check_release.py /absolute/path/to/new-release-directory/paopao-perspective-skill
python3 scripts/check_release.py /absolute/path/to/new-release-directory/paopao-room
```

构建脚本不会删除本地研究资料。它在副本内净化索引、改写指向未分发文本的引用，并给公开应用使用原创泡泡 SVG 标志。最终 manifest 可解释副本与本地源文件的差异。

## 仓库边界

以完整应用源码副本 `paopao-room` 作为统一公开仓库；其中 `paopao-perspective-skill` 是普通子目录，可独立打包安装。完整本地工作区还含研究私有输入，不能直接执行全量上传。

本地旧 Skill 空 Git 元数据已经可恢复地移到 `.local-archive/paopao-skill-git-20260918`；原始文件未删除，根工作区 Git 作为主仓库。归档不会进入公开包。

GitHub 仓库 URL 尚未设置，因此文档不提供虚构的克隆或一键远程安装命令。创建目标远程仓库后，再补实际地址及 release 下载链接。

## 独立安装验收

在新生成的 `paopao-room` 副本中验证，不复制本地 `.env.local`、`node_modules`、字幕或 RAG 索引：

```sh
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test
python3 tests/release-packaging.test.py
pnpm build
pnpm start
```

使用 Node.js 24+ 和 package.json 固定的 pnpm 版本。无密钥时应可打开界面、管理记录，并明确禁用发送。浏览器测试可在另一终端运行 `pnpm test:e2e`（需先安装 Playwright Chromium），模型回复由测试模拟。真实聊天需自行配置服务端密钥；公开副本没有索引时使用 Skill-only 回答。

`.github/workflows/ci.yml` 随公开包分发，会在 GitHub 上执行上述主要工程检查和浏览器测试。首次推送后仍需确认 Actions 实际运行成功。

## 发布前最后一步

检查打包报告、明确模型测试状态、审阅 MIT 与第三方分发范围，再从公开源码副本提交 GitHub。Git 提交、创建远程仓库、推送和上线托管尚未执行。

建议首次发布描述：基于公开资料的中文职业与商业决策人物 Skill，附可运行的 DeepSeek 连麦 Demo、来源卡和可复现评测工具。报告研究覆盖数量与实际分发范围，不把语料数量当作保真度分数。
