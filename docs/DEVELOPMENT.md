# 开发与发布检查

先按根目录 [README](../README.md)安装依赖。使用 Node.js 24+、pnpm 11.19.0，并以 `pnpm install --frozen-lockfile` 安装。常规命令：

```sh
pnpm typecheck
pnpm test
pnpm build
```

浏览器测试需独立终端运行 `pnpm dev`，再运行 `pnpm exec playwright install chromium` 和 `pnpm test:e2e`。不使用个人浏览器会话，模型请求由测试模拟。`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 可选，用于指定现有浏览器；默认使用 Playwright Chromium。

Skill 与发布工具检查需要 Python 3.10+，无需额外 Python 包：

```sh
python3 paopao-perspective-skill/scripts/validate_skill_content.py
python3 tests/release-packaging.test.py
```

本地完整素材的 RAG 构建和检索验收见 [全量入库说明](persona-rag-full-ingestion.md)。`rag:eval --live` 才会进行真实模型调用并产生 API 费用，普通工程和检索测试不执行该步骤。

## 更新 README 截图

保持本地开发服务运行，执行：

```sh
node scripts/capture-readme.mjs
```

脚本使用隔离浏览器、本地自定义泡泡老师头像和 `examples/voice-samples.md` 中已有的 Q1 回答生成 `docs/assets/chatroom.png`。拦截聊天和小结请求，不调用模型，不读取或更改个人聊天历史。需要已安装 Playwright Chromium，或设置上述浏览器路径变量。截图同时展示聊天与本次小结；小结为对应的演示内容，不是新的模型验收结果。公开源码不附头像原文件，重截前请设置 `PAOPAO_PREVIEW_AVATAR=/absolute/path/to/avatar.png` 指向自己的 PNG 头像。

发布过程见 [发布说明](PUBLISH.md)。截图是公开包唯一允许的 PNG 路径，个人头像原文件和其他本地 PNG 仍不分发；README 截图按用户要求展示该头像。

验收独立公开副本时，可用 `pnpm start --port 3101` 启动，再以 `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3101 pnpm test:e2e` 指定测试地址，避免占用当前开发服务。
