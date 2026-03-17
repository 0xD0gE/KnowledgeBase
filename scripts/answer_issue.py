#!/usr/bin/env python3
"""
answer_issue.py

GitHub Actions 執行此腳本，自動回答新建立的 Issue。

環境變數（由 answer-issue.yml 傳入）：
  GITHUB_TOKEN     - Actions 自動提供，用於 GitHub API 操作
  ANTHROPIC_API_KEY / OPENAI_API_KEY - 擇一設定在 GitHub Secrets
  LLM_PROVIDER     - "anthropic" 或 "openai"（Repository Variable）
  ISSUE_NUMBER     - Issue 編號
  ISSUE_TITLE      - Issue 標題
  ISSUE_BODY       - Issue 內文
  REPO_OWNER       - Repo 擁有者
  REPO_NAME        - Repo 名稱
"""

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

from knowledge_retriever import KnowledgeRetriever
from llm_client import create_llm_client


# ── 環境變數 ────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
ISSUE_NUMBER = int(os.environ.get("ISSUE_NUMBER", "0"))
ISSUE_TITLE  = os.environ.get("ISSUE_TITLE", "")
ISSUE_BODY   = os.environ.get("ISSUE_BODY", "")
REPO_OWNER   = os.environ.get("REPO_OWNER", "")
REPO_NAME    = os.environ.get("REPO_NAME", "")

# ── 設定 ──────────────────────────────────────────────────
DOCS_DIR     = "docs"
TOP_K_DOCS   = 5
MAX_DOC_CHARS = 3000

# System Prompt 路徑（優先讀取外部文件，fallback 使用內建）
PROMPT_FILE = Path("config/prompts/answer_prompt.txt")


def _load_system_prompt() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8").strip()
    # 內建 fallback prompt
    return """你是一個專業的知識庫助手，負責根據提供的知識庫文件內容來回答使用者的問題。

你的任務：
1. 仔細閱讀提供的知識庫文件
2. 判斷文件內容是否能夠回答使用者的問題
3. 如果能回答，提供準確、清晰的答案，並標明來源文件路徑
4. 如果無法從現有文件找到答案，誠實說明

輸出格式要求：
- 必須以 JSON 格式輸出（包在 ```json 代碼塊中）
- 欄位說明：
  - found_answer (boolean): true 表示找到答案
  - confidence (float 0.0~1.0): 信心分數
  - answer (string): 回答內容，使用 Markdown 格式，支援中英文混合
  - source_docs (string[]): 參考的文件路徑陣列

注意事項：
- 不要編造知識庫中沒有的資訊
- 如果資訊不完整，在答案中說明缺少哪些資訊
- 保持回答的準確性優先於完整性
- 回答語言以使用者提問語言為主（繁體中文或英文）"""


# ── GitHub API 操作 ────────────────────────────────────────

def _github_request(method: str, path: str, body: dict | None = None) -> dict:
    """通用 GitHub REST API 呼叫（不依賴第三方套件）。"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}{path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "KnowledgeBase-Bot/1.0",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {method} {path} -> {e.code}: {err_body}") from e


def add_label(label: str):
    _github_request("POST", f"/issues/{ISSUE_NUMBER}/labels", {"labels": [label]})


def remove_label(label: str):
    try:
        _github_request("DELETE", f"/issues/{ISSUE_NUMBER}/labels/{urllib.parse.quote(label)}")
    except Exception:
        pass  # label 不存在時忽略


def post_comment(body: str):
    _github_request("POST", f"/issues/{ISSUE_NUMBER}/comments", {"body": body})


# ── 回覆格式建構 ───────────────────────────────────────────

def _build_answer_comment(response, question_title: str) -> str:
    """根據 LLMResponse 建構 Issue Comment 的 Markdown 文字。"""
    provider_display = {
        "anthropic": "Claude (Anthropic)",
        "openai": "GPT (OpenAI)",
    }.get(response.provider, response.provider.title())

    confidence_bar = "🟢" if response.confidence >= 0.8 else ("🟡" if response.confidence >= 0.5 else "🔴")
    confidence_pct = f"{response.confidence:.0%}"

    if response.found_answer:
        sources_lines = "\n".join(
            f"- [`{doc}`](../../blob/main/{doc})" for doc in response.source_docs
        ) if response.source_docs else "（無具體來源文件）"

        return f"""## 🤖 AI 自動回答

{response.content}

---

### 參考來源

{sources_lines}

---

<details>
<summary>回答資訊</summary>

- **AI 引擎**：{provider_display} (`{response.model}`)
- **信心指數**：{confidence_bar} {confidence_pct}
- **Token 消耗**：{response.tokens_used:,}

</details>

> 如果答案不正確或不完整，歡迎：
> 1. 在此 Issue 補充說明或修正
> 2. 更新知識庫文件（`docs/`）並 Push
> 3. 維運者確認後會加上 `human-verified` 標籤"""

    else:
        return f"""## 🤖 AI 回應

感謝你的提問：**{question_title}**

很遺憾，目前知識庫中沒有足夠的資訊來完整回答這個問題。

{response.content}

---

**建議行動**：
- 如果你知道答案，歡迎直接在此 Issue 分享
- 或建立 Pull Request，在 `docs/` 目錄新增相關知識文件
- 維運者將會關注此 Issue 並補充知識庫

<details>
<summary>回答資訊</summary>

- **AI 引擎**：{provider_display} (`{response.model}`)
- **信心指數**：🔴 {confidence_pct}（知識庫資訊不足）

</details>"""


# ── 主流程 ────────────────────────────────────────────────

def main():
    if not all([GITHUB_TOKEN, ISSUE_NUMBER, REPO_OWNER, REPO_NAME]):
        print("Error: Missing required environment variables.", file=sys.stderr)
        sys.exit(1)

    print(f"[answer_issue] Processing Issue #{ISSUE_NUMBER}: {ISSUE_TITLE}")

    # Step 1：加上「處理中」label，讓使用者知道 Bot 已收到
    try:
        add_label("bot-processing")
    except Exception as e:
        print(f"  Warning: Cannot add bot-processing label: {e}")

    try:
        # Step 2：讀取相關知識庫文件
        retriever = KnowledgeRetriever(docs_dir=DOCS_DIR, max_doc_chars=MAX_DOC_CHARS)
        question = f"{ISSUE_TITLE}\n\n{ISSUE_BODY}".strip()
        relevant_docs = retriever.get_relevant_docs(question, top_k=TOP_K_DOCS)
        print(f"  Found {len(relevant_docs)} relevant documents")

        # Step 3：建構 LLM user message
        docs_context = retriever.format_docs_for_context(relevant_docs)
        system_prompt = _load_system_prompt()
        user_message = f"""## 使用者問題

{question}

---

## 知識庫相關文件

{docs_context}

---

## 輸出格式

請根據以上知識庫文件內容回答問題，並以 JSON 格式輸出（包在 ```json 代碼塊中）：

```json
{{
  "found_answer": true 或 false,
  "confidence": 0.0 到 1.0,
  "answer": "回答內容（Markdown 格式）",
  "source_docs": ["docs/path/to/file.md"]
}}
```"""

        # Step 4：呼叫 LLM
        llm = create_llm_client()
        print(f"  Calling {llm.provider_name}...")
        response = llm.chat(system_prompt, user_message)
        print(f"  Response: found_answer={response.found_answer}, "
              f"confidence={response.confidence:.0%}, tokens={response.tokens_used}")

        # Step 5：回覆 Issue Comment
        comment = _build_answer_comment(response, ISSUE_TITLE)
        post_comment(comment)

        # Step 6：更新 Labels
        result_label = "answered" if response.found_answer else "knowledge-gap"
        add_label(result_label)
        print(f"  Posted comment, added label: {result_label}")

    except Exception as e:
        # 即使出錯也要留言，讓使用者知道發生了什麼
        error_comment = f"""## ⚠️ AI 處理時發生錯誤

很抱歉，自動回答系統在處理此 Issue 時發生了錯誤。

**錯誤詳情**（給維運者參考）：
```
{str(e)}
```

請維運者手動查看並回答此問題。"""
        try:
            post_comment(error_comment)
            add_label("knowledge-gap")
        except Exception:
            pass
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        # 無論如何都移除 bot-processing label
        try:
            remove_label("bot-processing")
        except Exception:
            pass


if __name__ == "__main__":
    main()
