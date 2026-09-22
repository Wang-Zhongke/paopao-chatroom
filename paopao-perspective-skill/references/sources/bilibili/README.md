# 「泡言泡语」本地研究语料

本目录只收录 Bilibili 官方账号「像素范」（MID `15741969`）下系列「泡言泡语」（series_id `1210820`）的研究材料，排除其他同名“泡泡老师”。系列清单以 `corpus-index.json` 为唯一状态源。

## 目录说明

- `corpus-index.json` / `.csv`：353 条视频的 BVID、日期、时长、文本状态与提取质量。
- `transcripts/raw/`：Bilibili `ai-zh` 原始字幕响应。
- `transcripts/srt/`：Bilibili AI 字幕或画面 OCR 生成的时间轴文本。
- `transcripts/clean/`：供检索和证据定位的带行号 Markdown。
- `transcripts/ocr-raw/`：逐帧 Vision OCR 观测值与置信度，供复核。
- `video-cards/`：逐视频研究卡；包含摘要、判断链、例子、候选模型、语境和证据限制。
- `topic-index.json` / `.csv`：按七个研究维度做的多标签路由，不代表观点结论。
- `transcript-qa.md` / `.csv`：机器文本异常提示。
- `video-card-index.md` / `.jsonl`：研究卡检索入口。
- `corpus-report.md`：当前覆盖率、年度分布和未完成项。

## 证据等级

1. `downloaded`：Bilibili 播放器提供的 `ai-zh` 机器字幕。
2. `downloaded-ocr`：从画面烧录字幕按 0.8 秒采样提取的机器 OCR。
3. `needs-ocr-asr` / `ocr-error`：尚未形成可用全文，不以标题推断正文。

机器字幕用于发现和定位证据，不默认等同精确逐字引语。重要模型必须由至少两个独立公开内容支持，并保留时间、语境、说话者和反例。

## 版权与分发

这些全文是为本地研究、检索与蒸馏建立的中间语料，不代表获得重新发布完整逐字稿的授权。若公开发布 Skill，优先只发布来源索引、必要短摘录、研究卡和蒸馏结果；完整文本的分发范围应另行评估。

## 刷新报告

```bash
python3 scripts/research/bili_corpus_report.py \
  --manifest references/sources/bilibili/corpus-index.json \
  --transcript-dir references/sources/bilibili/transcripts/clean \
  --output references/sources/bilibili/corpus-report.md
```
