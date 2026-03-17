/**
 * app.js
 *
 * 知識庫前端主邏輯。
 * 依賴：config.js, github-api.js
 */

// ── 狀態 ─────────────────────────────────────────────────────
let _searchIndex = null;   // 本地搜尋索引（data/search-index.json）
let _searchTimer = null;   // 防抖 timer
let _currentQuery = "";    // 目前搜尋字串

// ── DOM 節點快取 ──────────────────────────────────────────────
const el = {};

// ── 初始化 ────────────────────────────────────────────────────
async function init() {
  // 快取 DOM 節點
  el.searchInput    = document.getElementById("search-input");
  el.searchSpinner  = document.getElementById("search-spinner");
  el.resultsSection = document.getElementById("results-section");
  el.resultsList    = document.getElementById("results-list");
  el.resultsCount   = document.getElementById("results-count");
  el.noResultBox    = document.getElementById("no-result-box");
  el.createIssueBtn = document.getElementById("create-issue-btn");
  el.recentSection  = document.getElementById("recent-section");
  el.recentList     = document.getElementById("recent-list");
  el.rateLimitWarn  = document.getElementById("rate-limit-warn");
  el.patModal       = document.getElementById("pat-modal");
  el.patInput       = document.getElementById("pat-input");
  el.patSubmitBtn   = document.getElementById("pat-submit-btn");
  el.patCancelBtn   = document.getElementById("pat-cancel-btn");
  el.patError       = document.getElementById("pat-error");
  el.issueCreatedBox = document.getElementById("issue-created-box");
  el.issueLink      = document.getElementById("issue-link");

  // 設定 GitHub 連結
  const issuesUrl = `https://github.com/${KB_CONFIG.owner}/${KB_CONFIG.repo}/issues`;
  const docsUrl   = `https://github.com/${KB_CONFIG.owner}/${KB_CONFIG.repo}/tree/main/docs`;
  document.getElementById("github-issues-link").href = issuesUrl;
  document.getElementById("github-docs-link").href   = docsUrl;
  document.getElementById("github-repo-link").href   =
    `https://github.com/${KB_CONFIG.owner}/${KB_CONFIG.repo}`;

  // 載入本地搜尋索引
  await loadSearchIndex();

  // 載入最近已回答問題
  loadRecentAnswered();

  // 綁定搜尋框事件（防抖）
  el.searchInput.addEventListener("input", (e) => {
    clearTimeout(_searchTimer);
    const q = e.target.value.trim();
    if (q.length < KB_CONFIG.search.minQueryLength) {
      showState("idle");
      return;
    }
    showSpinner(true);
    _searchTimer = setTimeout(() => handleSearch(q), KB_CONFIG.search.debounceMs);
  });

  // 按 Enter 立即搜尋
  el.searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      clearTimeout(_searchTimer);
      const q = el.searchInput.value.trim();
      if (q.length >= KB_CONFIG.search.minQueryLength) {
        showSpinner(true);
        handleSearch(q);
      }
    }
  });

  // 「建立 Issue」按鈕
  el.createIssueBtn.addEventListener("click", () => openPatModal());

  // PAT Modal 送出
  el.patSubmitBtn.addEventListener("click", submitCreateIssue);
  el.patCancelBtn.addEventListener("click", closePatModal);
  el.patInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitCreateIssue();
  });

  // 按 Esc 關閉 Modal
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePatModal();
  });

  // Modal 背景點擊關閉
  el.patModal.addEventListener("click", (e) => {
    if (e.target === el.patModal) closePatModal();
  });

  // 若 sessionStorage 有 PAT，填入輸入框
  const savedPat = sessionStorage.getItem(KB_CONFIG.issue.patStorageKey);
  if (savedPat) el.patInput.value = savedPat;
}

// ── 搜尋索引 ──────────────────────────────────────────────────

async function loadSearchIndex() {
  try {
    const res = await fetch(KB_CONFIG.paths.searchIndex + "?t=" + Date.now());
    if (res.ok) {
      _searchIndex = await res.json();
      console.log(`[KB] Loaded search index: ${_searchIndex.length} docs`);
    }
  } catch (e) {
    console.warn("[KB] Cannot load local search index:", e.message);
  }
}

/**
 * 本地全文搜尋（在 search-index.json 中）。
 * 回傳有分數的結果陣列，按分數降冪排序。
 */
function localSearch(query) {
  if (!_searchIndex) return [];
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);

  return _searchIndex
    .map((doc) => {
      let score = 0;
      const haystack = [
        doc.title,
        ...(doc.headings || []),
        ...(doc.tags || []),
        doc.summary,
      ]
        .join(" ")
        .toLowerCase();

      terms.forEach((term) => {
        if (doc.title.toLowerCase().includes(term)) score += 4;
        if ((doc.tags || []).some((t) => t.toLowerCase().includes(term))) score += 3;
        if ((doc.headings || []).some((h) => h.toLowerCase().includes(term))) score += 2;
        if (doc.summary.toLowerCase().includes(term)) score += 1;
      });

      return { ...doc, score, snippets: score > 0 ? [doc.summary] : [] };
    })
    .filter((d) => d.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, KB_CONFIG.search.maxLocalResults);
}

// ── 搜尋主流程 ────────────────────────────────────────────────

async function handleSearch(query) {
  _currentQuery = query;
  showSpinner(true);
  hideElement(el.noResultBox);
  hideElement(el.issueCreatedBox);

  try {
    // Step 1：本地索引搜尋（快速）
    let results = localSearch(query);
    const localTopScore = results.length > 0 ? results[0].score : 0;

    // Step 2：若本地結果不足，呼叫 GitHub Search API
    if (localTopScore < KB_CONFIG.search.localScoreThreshold) {
      try {
        const apiResults = await GitHubAPI.searchCode(
          query,
          KB_CONFIG.owner,
          KB_CONFIG.repo,
          KB_CONFIG.paths.docsDir,
          KB_CONFIG.search.maxApiResults
        );

        // 合併：API 結果優先，去除重複路徑
        const localPaths = new Set(results.map((r) => r.path));
        const merged = [
          ...apiResults.map((r) => ({ ...r, fromApi: true })),
          ...results.filter((r) => !localPaths.has(r.path)),
        ].slice(0, KB_CONFIG.search.maxLocalResults);

        results = merged;
      } catch (e) {
        if (e instanceof GitHubAPI.RateLimitError) {
          showElement(el.rateLimitWarn);
        } else {
          console.warn("[KB] GitHub Search API error:", e.message);
        }
        // 繼續使用本地結果
      }
    }

    // 顯示結果
    if (results.length > 0) {
      renderResults(results, query);
      showState("results");
    } else {
      showState("no-results");
    }
  } catch (e) {
    console.error("[KB] Search error:", e);
    showState("no-results");
  } finally {
    showSpinner(false);
  }
}

// ── 結果渲染 ──────────────────────────────────────────────────

function renderResults(results, query) {
  el.resultsCount.textContent = `找到 ${results.length} 篇相關文件`;
  el.resultsList.innerHTML = "";

  results.forEach((result) => {
    const blobUrl = `https://github.com/${KB_CONFIG.owner}/${KB_CONFIG.repo}/blob/main/${result.path}`;
    const snippet = pickBestSnippet(result.snippets || [], query);
    const highlightedSnippet = highlight(escapeHtml(snippet), query);
    const highlightedTitle = highlight(escapeHtml(result.title || result.name || result.path), query);

    const li = document.createElement("li");
    li.className = "result-item";
    li.innerHTML = `
      <a class="result-title" href="${blobUrl}" target="_blank" rel="noopener">
        ${highlightedTitle}
        <span class="result-ext-icon">↗</span>
      </a>
      <div class="result-path">${escapeHtml(result.path)}</div>
      ${snippet ? `<div class="result-snippet">${highlightedSnippet}</div>` : ""}
    `;
    el.resultsList.appendChild(li);
  });
}

/** 從多個摘要片段中挑出包含最多搜尋詞的那段 */
function pickBestSnippet(snippets, query) {
  if (!snippets || snippets.length === 0) return "";
  const terms = query.toLowerCase().split(/\s+/);
  let best = snippets[0];
  let bestCount = 0;
  snippets.forEach((s) => {
    const count = terms.filter((t) => s.toLowerCase().includes(t)).length;
    if (count > bestCount) { best = s; bestCount = count; }
  });
  return best.length > 200 ? best.slice(0, 200) + "…" : best;
}

/** 高亮搜尋關鍵字 */
function highlight(html, query) {
  const terms = query.split(/\s+/).filter(Boolean).map(escapeRegex);
  if (terms.length === 0) return html;
  const pattern = new RegExp(`(${terms.join("|")})`, "gi");
  return html.replace(pattern, "<mark>$1</mark>");
}

// ── 最近已回答問題 ────────────────────────────────────────────

async function loadRecentAnswered() {
  try {
    const issues = await GitHubAPI.getAnsweredIssues(
      KB_CONFIG.owner,
      KB_CONFIG.repo,
      KB_CONFIG.ui.maxRecentAnswered
    );

    if (issues.length === 0) {
      hideElement(el.recentSection);
      return;
    }

    el.recentList.innerHTML = "";
    issues.forEach((issue) => {
      const li = document.createElement("li");
      li.className = "recent-item";
      li.innerHTML = `
        <a href="${issue.url}" target="_blank" rel="noopener">
          #${issue.number} ${escapeHtml(issue.title)}
        </a>
        <span class="recent-date">${formatDate(issue.updatedAt)}</span>
      `;
      el.recentList.appendChild(li);
    });

    showElement(el.recentSection);
  } catch (e) {
    hideElement(el.recentSection);
  }
}

// ── PAT Modal ────────────────────────────────────────────────

function openPatModal() {
  el.patError.textContent = "";
  showElement(el.patModal);
  el.patInput.focus();
}

function closePatModal() {
  hideElement(el.patModal);
}

async function submitCreateIssue() {
  const pat = el.patInput.value.trim();
  if (!pat) {
    el.patError.textContent = "請輸入 GitHub Personal Access Token。";
    return;
  }

  // 儲存 PAT 到 sessionStorage（分頁關閉即清除）
  sessionStorage.setItem(KB_CONFIG.issue.patStorageKey, pat);

  el.patSubmitBtn.disabled = true;
  el.patSubmitBtn.textContent = "建立中…";
  el.patError.textContent = "";

  try {
    const issue = await createIssueFromQuery(_currentQuery, pat);
    closePatModal();
    showIssueCreated(issue);
  } catch (e) {
    el.patError.textContent = e.message;
  } finally {
    el.patSubmitBtn.disabled = false;
    el.patSubmitBtn.textContent = "建立 Issue";
  }
}

async function createIssueFromQuery(query, token) {
  const title = `[Question] ${query.slice(0, 80)}`;
  const body = buildIssueBody(query);

  return GitHubAPI.createIssue({
    owner: KB_CONFIG.owner,
    repo: KB_CONFIG.repo,
    title,
    body,
    labels: KB_CONFIG.issue.labels,
    token,
  });
}

function buildIssueBody(query) {
  const now = new Date().toISOString().replace("T", " ").slice(0, 19) + " UTC";
  return `## 使用者提問

${query}

---

> 此 Issue 由知識庫查詢系統自動建立
> 建立時間：${now}
> 系統版本：knowledge-base-web-v1

## 搜尋狀況

知識庫搜尋後未找到足夠的相關答案。

## 期望
AI Agent 將自動讀取知識庫並嘗試回答此問題。
如果 AI 回答不夠準確，請在此 Issue 中補充或修正。`;
}

function showIssueCreated(issue) {
  el.issueLink.href = issue.html_url;
  el.issueLink.textContent = `#${issue.number} ${issue.title}`;
  showElement(el.issueCreatedBox);
  hideElement(el.noResultBox);
}

// ── UI 輔助函式 ───────────────────────────────────────────────

function showState(state) {
  hideElement(el.resultsSection);
  hideElement(el.noResultBox);
  hideElement(el.rateLimitWarn);

  if (state === "results") showElement(el.resultsSection);
  if (state === "no-results") showElement(el.noResultBox);
}

function showSpinner(on) {
  el.searchSpinner.style.display = on ? "inline-block" : "none";
}

function showElement(el) { el.style.display = ""; }
function hideElement(el) { el.style.display = "none"; }

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("zh-TW", { year: "numeric", month: "2-digit", day: "2-digit" });
}

// ── 啟動 ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", init);
