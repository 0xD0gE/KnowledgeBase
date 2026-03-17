/**
 * config.js
 *
 * 知識庫網站設定。
 * 部署時由 GitHub Actions deploy-pages.yml 自動注入 REPO_OWNER 與 REPO_NAME。
 * 若需要本地測試，可直接修改下方的值。
 */

const KB_CONFIG = {
  // ── Repo 設定（由 Actions 自動注入，格式：__PLACEHOLDER__）──
  owner: "__REPO_OWNER__",   // GitHub 用戶名或組織名稱
  repo:  "__REPO_NAME__",    // Repository 名稱

  // ── 搜尋設定 ────────────────────────────────────────────
  search: {
    minQueryLength: 2,       // 最少幾個字才觸發搜尋
    debounceMs: 400,         // 防抖延遲 (ms)
    maxLocalResults: 8,      // 本地索引最多顯示幾筆
    maxApiResults: 8,        // GitHub API 最多取幾筆
    // 本地搜尋分數門檻，低於此分數才額外呼叫 GitHub Search API
    localScoreThreshold: 2,
  },

  // ── 知識庫路徑 ───────────────────────────────────────────
  paths: {
    docsDir: "docs",
    searchIndex: "data/search-index.json",
  },

  // ── Issue 設定 ───────────────────────────────────────────
  issue: {
    labels: ["auto-question", "needs-answer"],
    // sessionStorage 存放 PAT 的 key
    patStorageKey: "kb_github_pat",
  },

  // ── UI 設定 ──────────────────────────────────────────────
  ui: {
    // GitHub raw content base URL，用來讓使用者直接看文件內容
    rawContentBase: "https://raw.githubusercontent.com",
    // GitHub 文件連結 base URL
    blobBase: "https://github.com",
    // Issues 頁面
    issuesUrl: "https://github.com/__REPO_OWNER__/__REPO_NAME__/issues",
    // 最近已回答問題：從 Issues API 讀取此 label
    answeredLabel: "answered",
    maxRecentAnswered: 5,
  },
};
