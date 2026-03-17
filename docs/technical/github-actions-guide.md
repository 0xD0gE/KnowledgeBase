---
title: GitHub Actions 使用指南
tags: GitHub Actions, CI/CD, 自動化, workflow
updated: 2026-01-01
---

# GitHub Actions 使用指南

本文說明本知識庫系統使用的 GitHub Actions Workflows。

## Workflows 總覽

| Workflow 文件 | 觸發條件 | 功能 |
|--------------|---------|------|
| `build-index.yml` | Push `docs/**/*.md` | 更新搜尋索引 |
| `deploy-pages.yml` | Push `web/**` 或索引更新後 | 部署 GitHub Pages |
| `answer-issue.yml` | Issue 建立或加上 `auto-question` label | LLM 自動回答 |

## 必要的 Secrets 設定

在 GitHub Repo 的 **Settings > Secrets and variables > Actions** 中設定：

| Secret 名稱 | 說明 | 必填 |
|------------|------|------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key | 擇一 |
| `OPENAI_API_KEY` | OpenAI API Key | 擇一 |

## 必要的 Variables 設定

在 **Settings > Secrets and variables > Actions > Variables** 中設定：

| Variable 名稱 | 說明 | 預設值 |
|--------------|------|--------|
| `LLM_PROVIDER` | LLM 提供商：`anthropic` 或 `openai` | `anthropic` |

## 如何切換 LLM 提供商

1. 前往 GitHub Repo > Settings > Secrets and variables > Actions > Variables
2. 修改 `LLM_PROVIDER` 的值（`anthropic` 或 `openai`）
3. 下次 Issue 建立時即會使用新的提供商

## 手動觸發 Workflow

若需要手動更新索引：
1. 前往 GitHub Repo > Actions
2. 選擇 "Build Knowledge Index"
3. 點擊 "Run workflow"

## 查看 Workflow 執行記錄

1. 前往 GitHub Repo > Actions
2. 選擇對應的 Workflow
3. 點擊執行記錄查看詳細日誌

## 常見問題

### Workflow 執行失敗

**原因 1: API Key 未設定**
- 確認 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY` 已設定在 Secrets 中

**原因 2: API 費用不足**
- 確認 API 帳戶有足夠的額度

**原因 3: Python 套件安裝失敗**
- 檢查 `scripts/requirements.txt` 中的套件版本是否相容

### AI 回答品質不佳

- 確認知識庫文件內容完整
- 調整 `config/prompts/answer_prompt.txt` 中的 System Prompt
- 嘗試切換不同的 LLM 提供商
