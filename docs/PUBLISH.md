# 发布与维护

公开仓库：[连麦室](https://github.com/Wang-Zhongke/paopao-chatroom) · [独立 Skill](https://github.com/Wang-Zhongke/paopao-skill)。源码发布不等于网站已上线。下载源码可使用 Code → Download ZIP。

## 内容边界

连麦室包含应用和内置 Skill；独立 Skill 可单独安装。公开包包含代码、框架、来源卡与正式评测材料，不包含密钥、个人聊天、完整字幕、原视频或生成的 RAG 索引。README 截图展示自定义头像，头像原文件不随包分发。归属见[第三方说明](../THIRD_PARTY_NOTICES.md)。

## 构建公开包

从连麦室仓库根目录运行；输出必须是不存在或为空的绝对目录：

```sh
python3 scripts/build_release.py --output /absolute/path/to/new-release
python3 scripts/check_release.py /absolute/path/to/new-release/paopao-room
python3 scripts/check_release.py /absolute/path/to/new-release/paopao-perspective-skill
```

脚本生成应用与 Skill 两份 ZIP，并附记录文件哈希的 MANIFEST.json。副本会净化来源索引、处理引用并使用公开版图标，不修改原始研究资料。

## 验证与同步

在新生成的应用副本执行 `pnpm install --frozen-lockfile`、`pnpm typecheck`、`pnpm test`、`pnpm build`，再按[开发指南](DEVELOPMENT.md)验证浏览器交互。无密钥应禁用发送；无 RAG 索引仍能通过 Skill 回答。

两个仓库分别提交对应公开副本，并核对连麦室的 [Actions](https://github.com/Wang-Zhongke/paopao-chatroom/actions)。维护 Skill 时统一修改来源，再同步内置副本，避免两份内容独立漂移。正式评测材料保留原始输入与结果；新实验使用新输出目录。当前工程验收见[发布检查](RELEASE-CHECK.md)。
