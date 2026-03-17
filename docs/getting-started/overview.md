---
title: 系統概覽
tags: 入門, 概覽, 架構
updated: 2026-01-01
---

# 系統概覽

本組織的知識庫管理系統基於 GitHub 建置，透過 Git 版本控制管理所有知識內容。

## 系統組成

### 1. 知識庫儲存

- 所有知識文件以 Markdown 格式儲存於 `docs/` 目錄
- 每次 `git push` 即自動更新搜尋索引
- 支援 Git 版本歷史，可追蹤每次修改

### 2. 搜尋介面

- 透過 GitHub Pages 提供靜態網頁搜尋
- 使用 GitHub Search API 進行全文搜尋
- 支援繁體中文與英文混合搜尋

### 3. AI 自動回答

- 找不到答案時可建立 GitHub Issue
- GitHub Actions 自動觸發 AI 讀取知識庫並回答
- 支援 Claude (Anthropic) 與 OpenAI GPT 切換

### 4. 人工審核機制

- AI 回答會加上 `answered` 標籤
- 維運者確認後可加上 `human-verified` 標籤
- 若答案有誤，可在 Issue 中補充或修正

## 快速開始

1. **搜尋問題**：前往知識庫網站，在搜尋框輸入問題
2. **瀏覽文件**：點擊搜尋結果查看完整文件
3. **提問**：若找不到答案，點擊「找不到答案」建立 Issue
4. **等待回答**：AI 通常在 5 分鐘內自動回答

## 常用連結

- [知識庫網站](../../web/index.html)
- [GitHub Issues](../../issues) - 查看所有問答記錄
- [貢獻指南](../README.md)
