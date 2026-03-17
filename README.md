# 組織知識庫

基於 GitHub 的知識庫管理系統。知識庫內容即 Git Repo 中的 Markdown 文件，每次 Push 自動更新搜尋索引。

## 系統特色

- **零後端**：完全靜態，部署在 GitHub Pages
- **AI 自動回答**：找不到答案時建立 Issue，GitHub Actions 自動呼叫 LLM 回答
- **雙 LLM 支援**：Claude (Anthropic) 與 OpenAI，可隨時切換
- **版本控制**：知識庫修改歷史完整保存於 Git

## 快速使用

1. **搜尋**：前往 [知識庫網站](https://your-org.github.io/KnowledgeBase)
2. **提問**：找不到答案時點擊「建立 Issue，讓 AI 來回答」
3. **貢獻**：在 `docs/` 目錄下新增或修改 Markdown 文件後 Push

## 部署步驟

### 1. Fork / Clone 此 Repo

### 2. 啟用 GitHub Pages

- Repo Settings → Pages → Source 選擇 **GitHub Actions**

### 3. 設定 GitHub Secrets

在 Repo Settings → Secrets and variables → Actions → Secrets 中新增：

| Secret 名稱 | 說明 |
|------------|------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key（擇一） |
| `OPENAI_API_KEY` | OpenAI API Key（擇一） |

### 4. 設定 Repository Variables（可選）

在 Repo Settings → Secrets and variables → Actions → Variables 中新增：

| Variable 名稱 | 值 | 說明 |
|--------------|-----|------|
| `LLM_PROVIDER` | `anthropic` 或 `openai` | 預設使用的 LLM |

### 5. 新增初始知識庫文件

在 `docs/` 目錄下新增 Markdown 文件並 Push，等待 Actions 自動部署。

### 6. 建立 Issue Labels

前往 GitHub Issues → Labels，手動建立以下 Labels（或使用 [github-label-sync](https://github.com/Financial-Times/github-label-sync)）：

| Label | 顏色 | 說明 |
|-------|------|------|
| `auto-question` | #0075ca | 系統自動建立的問題 |
| `needs-answer` | #e4e669 | 等待回答 |
| `bot-processing` | #cccccc | AI 正在處理 |
| `answered` | #0e8a16 | AI 已回答 |
| `human-verified` | #006b75 | 人工確認正確 |
| `knowledge-gap` | #d93f0b | 知識庫需要補充 |
| `knowledge-updated` | #1d76db | 已更新知識庫 |
| `manual-question` | #7057ff | 使用者手動提問 |

## 專案結構

```
KnowledgeBase/
├── .github/
│   ├── workflows/
│   │   ├── answer-issue.yml    # Issue 觸發 LLM 自動回答
│   │   ├── build-index.yml     # Push 時更新搜尋索引
│   │   └── deploy-pages.yml    # 部署 GitHub Pages
│   └── ISSUE_TEMPLATE/         # Issue 建立模板
│
├── docs/                       # 知識庫文件（在此新增 .md 文件）
│   ├── getting-started/
│   ├── faq/
│   └── technical/
│
├── web/                        # 前端（GitHub Pages）
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── config.js           # Repo 設定
│       ├── github-api.js       # GitHub API 封裝
│       └── app.js              # 主應用邏輯
│
├── scripts/                    # GitHub Actions 使用的 Python 腳本
│   ├── build_index.py          # 搜尋索引生成
│   ├── answer_issue.py         # Issue 自動回答
│   ├── llm_client.py           # Claude/OpenAI 統一介面
│   ├── knowledge_retriever.py  # 知識庫文件讀取
│   └── requirements.txt
│
├── config/
│   ├── settings.yml            # 系統設定
│   └── prompts/
│       └── answer_prompt.txt   # LLM System Prompt
│
└── data/                       # 自動生成（Actions commit）
    └── search-index.json
```

## 新增知識庫文件

```bash
# 在對應分類目錄下建立文件
cat > docs/faq/my-topic.md << 'EOF'
---
title: 文件標題
tags: tag1, tag2
updated: 2026-01-01
---

# 文件標題

## 章節一

內容...
EOF

git add docs/faq/my-topic.md
git commit -m "docs: 新增 XXX 相關文件"
git push
```

Push 後約 2-3 分鐘即可在知識庫網站搜尋到新文件。

## 本地測試搜尋索引

```bash
cd KnowledgeBase
python scripts/build_index.py
# 生成 data/search-index.json
```

## 授權

MIT License
