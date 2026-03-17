---
title: LLM 整合說明
tags: LLM, Claude, OpenAI, AI, 整合
updated: 2026-01-01
---

# LLM 整合說明

本系統支援 Claude (Anthropic) 與 OpenAI 兩種 LLM 提供商，可透過設定輕鬆切換。

## 支援的模型

### Anthropic Claude
- 預設模型：`claude-opus-4-6`
- 備選：`claude-haiku-4-5-20251001`（較便宜，適合高流量）

### OpenAI
- 預設模型：`gpt-4o`
- 備選：`gpt-4o-mini`（較便宜，適合高流量）

## 切換方式

在 GitHub Repository Variables 中修改 `LLM_PROVIDER`：
- `anthropic`：使用 Claude
- `openai`：使用 GPT

## AI 回答的結構

AI 回答以 JSON 格式輸出，包含：

```json
{
  "found_answer": true,
  "confidence": 0.85,
  "answer": "回答內容（Markdown 格式）",
  "source_docs": ["docs/technical/example.md"]
}
```

## 成本控制建議

- 知識庫文件量少時（< 50 篇）：使用預設模型即可
- 知識庫文件量多時（> 200 篇）：考慮切換到較輕量模型（haiku / gpt-4o-mini）
- 每次 Issue 回答通常消耗 2,000 ~ 8,000 tokens

## 自訂 System Prompt

可以修改 `config/prompts/answer_prompt.txt` 來調整 AI 的回答風格：

- 加入組織特有的術語說明
- 指定回答的語言偏好
- 調整回答的詳細程度
