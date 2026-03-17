/**
 * github-api.js
 *
 * GitHub REST API 封裝。
 * - 搜尋程式碼（不需要 Auth，公開 Repo）
 * - 建立 Issue（需要 GitHub PAT）
 * - 讀取 Issues 列表（不需要 Auth，公開 Repo）
 */

const GitHubAPI = (() => {
  const BASE = "https://api.github.com";

  // Rate limit 狀態追蹤
  let _rateLimitRemaining = 10;
  let _rateLimitReset = 0;

  /**
   * 通用 fetch，自動加 Accept header，並追蹤 Rate Limit。
   */
  async function _fetch(url, options = {}) {
    const headers = {
      Accept: "application/vnd.github.v3+json",
      ...options.headers,
    };
    const res = await fetch(url, { ...options, headers });

    // 更新 rate limit 狀態
    const remaining = res.headers.get("X-RateLimit-Remaining");
    const reset = res.headers.get("X-RateLimit-Reset");
    if (remaining !== null) _rateLimitRemaining = parseInt(remaining, 10);
    if (reset !== null) _rateLimitReset = parseInt(reset, 10);

    return res;
  }

  /**
   * 使用 GitHub Code Search API 搜尋知識庫文件。
   * 公開 Repo 不需要 Token。
   *
   * @param {string} query   - 搜尋關鍵字
   * @param {string} owner   - Repo 擁有者
   * @param {string} repo    - Repo 名稱
   * @param {string} docsDir - 限定搜尋的目錄（預設 docs）
   * @param {number} perPage - 最多回傳幾筆
   * @returns {Promise<Array>} - 搜尋結果陣列
   */
  async function searchCode(query, owner, repo, docsDir = "docs", perPage = 8) {
    if (_rateLimitRemaining <= 1) {
      const waitSec = Math.max(0, _rateLimitReset - Math.floor(Date.now() / 1000));
      throw new RateLimitError(`GitHub API rate limit exceeded. Resets in ${waitSec}s.`);
    }

    const q = encodeURIComponent(
      `${query} repo:${owner}/${repo} path:${docsDir} extension:md`
    );
    const url = `${BASE}/search/code?q=${q}&per_page=${perPage}`;

    const res = await _fetch(url, {
      headers: {
        // text-match 讓 API 回傳匹配片段，避免額外讀取文件
        Accept: "application/vnd.github.v3.text-match+json",
      },
    });

    if (res.status === 403) throw new RateLimitError("GitHub API rate limit hit.");
    if (res.status === 422) return []; // query 太短或格式有誤，回傳空
    if (!res.ok) throw new Error(`GitHub Search API error: ${res.status}`);

    const data = await res.json();
    return (data.items || []).map((item) => ({
      path: item.path,
      name: item.name,
      title: item.name.replace(/\.md$/i, "").replace(/[-_]/g, " "),
      url: item.html_url,
      rawUrl: `https://raw.githubusercontent.com/${owner}/${repo}/main/${item.path}`,
      snippets: (item.text_matches || []).map((m) => m.fragment).filter(Boolean),
      score: item.score || 0,
    }));
  }

  /**
   * 建立 GitHub Issue。需要 PAT（public_repo scope）。
   *
   * @param {object} params
   * @param {string} params.owner
   * @param {string} params.repo
   * @param {string} params.title
   * @param {string} params.body
   * @param {string[]} params.labels
   * @param {string} params.token - GitHub PAT
   * @returns {Promise<object>} - 建立後的 Issue 物件
   */
  async function createIssue({ owner, repo, title, body, labels, token }) {
    const url = `${BASE}/repos/${owner}/${repo}/issues`;
    const res = await _fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title, body, labels }),
    });

    if (res.status === 401) throw new AuthError("GitHub PAT 無效或已過期。");
    if (res.status === 403) throw new AuthError("GitHub PAT 權限不足，需要 public_repo scope。");
    if (res.status === 404) throw new Error("找不到 Repo，請確認 owner/repo 設定是否正確。");
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || `GitHub API error: ${res.status}`);
    }

    return res.json();
  }

  /**
   * 讀取最近已回答的 Issues（label: answered）。
   * 公開 Repo 不需要 Token。
   */
  async function getAnsweredIssues(owner, repo, perPage = 5) {
    const url =
      `${BASE}/repos/${owner}/${repo}/issues` +
      `?labels=answered&state=open&per_page=${perPage}&sort=updated`;
    const res = await _fetch(url);
    if (!res.ok) return [];
    const data = await res.json();
    return data.map((issue) => ({
      number: issue.number,
      title: issue.title,
      url: issue.html_url,
      updatedAt: issue.updated_at,
    }));
  }

  /**
   * 讀取 Raw 文件內容（Markdown 原始文字）。
   */
  async function getRawFile(rawUrl) {
    const res = await fetch(rawUrl);
    if (!res.ok) throw new Error(`Cannot fetch file: ${res.status}`);
    return res.text();
  }

  /** 取得目前 rate limit 狀態 */
  function getRateLimit() {
    return { remaining: _rateLimitRemaining, reset: _rateLimitReset };
  }

  // ── 自訂 Error 類型 ──────────────────────────────────────
  class RateLimitError extends Error {
    constructor(msg) { super(msg); this.name = "RateLimitError"; }
  }
  class AuthError extends Error {
    constructor(msg) { super(msg); this.name = "AuthError"; }
  }

  return { searchCode, createIssue, getAnsweredIssues, getRawFile, getRateLimit, RateLimitError, AuthError };
})();
