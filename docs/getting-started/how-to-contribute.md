---
title: 如何貢獻知識庫
tags: 入門, 貢獻, Git
updated: 2026-01-01
---

# 如何貢獻知識庫

本文說明如何新增或修改知識庫文件。

## 基本流程

```bash
# 1. 複製儲存庫
git clone https://github.com/your-org/KnowledgeBase.git
cd KnowledgeBase

# 2. 建立新文件（在對應分類目錄下）
# 例如：新增 FAQ 文件
touch docs/faq/my-new-faq.md

# 3. 編輯文件內容
# 使用下方的文件模板格式

# 4. 提交並推送
git add docs/faq/my-new-faq.md
git commit -m "docs: 新增 XXX 相關 FAQ"
git push origin main
```

推送後，GitHub Actions 會自動：
1. 更新搜尋索引（`data/search-index.json`）
2. 重新部署 GitHub Pages 網站

## 文件格式規範

每個 Markdown 文件應包含 YAML frontmatter：

```markdown
---
title: 文件標題（必填）
tags: tag1, tag2, tag3（建議填寫，有助於搜尋）
updated: 2026-01-15（最後更新日期）
---

# 文件標題

## 章節一

內容...

## 章節二

內容...
```

## 文件命名規則

- 使用小寫英文字母和連字號（kebab-case）
- 例如：`how-to-setup-database.md`
- 避免空格和特殊符號

## 目錄分類建議

| 目錄 | 適合的內容 |
|------|-----------|
| `getting-started/` | 入門教學、快速開始 |
| `faq/` | 常見問題與解答 |
| `technical/` | 技術參考、API 文件、架構說明 |

如果現有分類不符合，可以新增目錄，但請在 `docs/README.md` 中更新目錄說明。

## 修正現有文件

直接編輯對應 `.md` 文件並 push 即可。建議在 commit message 中說明修正原因：

```bash
git commit -m "fix(docs): 更正 OAuth 設定說明中的錯誤步驟"
```

## 關閉相關 Issue

如果此次更新是為了解答某個 Issue 中的問題，可以在 commit message 或 PR 中引用：

```bash
git commit -m "docs: 新增 JWT Token 過期處理說明 (closes #42)"
```
