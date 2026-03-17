#!/usr/bin/env python3
"""
knowledge_retriever.py

讀取 docs/ 目錄下的所有 Markdown 文件，
根據問題關鍵字篩選最相關的 top-k 篇，
並格式化成可傳給 LLM 的 context 文字。

由 answer_issue.py 引用，不直接執行。
"""

import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DocEntry:
    """代表一篇知識庫文件。"""
    path: str      # 相對路徑（如 docs/faq/general-faq.md）
    title: str     # 文件標題
    content: str   # 完整內文（已移除 frontmatter）
    tags: list     # 標籤列表
    score: int = 0 # 搜尋相關性分數（暫存用）


def _strip_frontmatter(text: str) -> str:
    """移除 YAML frontmatter，回傳純 Markdown 內文。"""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].strip()
    return text.strip()


def _parse_title(text: str, stem: str) -> str:
    """從 frontmatter title 或第一個 H1 擷取標題。"""
    # 嘗試 frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm = text[3:end]
            for line in fm.split("\n"):
                if line.lower().startswith("title:"):
                    return line.split(":", 1)[1].strip()
    # 嘗試第一個 H1
    h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()
    # Fallback：檔名
    return stem.replace("-", " ").replace("_", " ").title()


def _parse_tags(text: str) -> list:
    """從 frontmatter 擷取 tags。"""
    if not text.startswith("---"):
        return []
    end = text.find("---", 3)
    if end == -1:
        return []
    fm = text[3:end]
    for line in fm.split("\n"):
        if line.lower().startswith("tags:"):
            raw = line.split(":", 1)[1].strip()
            return [t.strip() for t in re.split(r"[,，]", raw) if t.strip()]
    return []


def _score_doc(doc: DocEntry, terms: list) -> int:
    """計算文件與搜尋詞的相關性分數。"""
    score = 0
    title_lower = doc.title.lower()
    content_lower = doc.content.lower()
    tags_lower = " ".join(doc.tags).lower()

    for term in terms:
        t = term.lower()
        if t in title_lower:
            score += 5
        if any(t in tag for tag in doc.tags):
            score += 3
        # 計算 content 中出現次數（每次 +1，上限 5）
        count = content_lower.count(t)
        score += min(count, 5)

    return score


class KnowledgeRetriever:
    """
    讀取並篩選知識庫文件。

    Usage:
        retriever = KnowledgeRetriever(docs_dir="docs")
        relevant = retriever.get_relevant_docs("JWT token 過期怎麼處理", top_k=5)
        context = retriever.format_docs_for_context(relevant)
    """

    def __init__(self, docs_dir: str = "docs", max_doc_chars: int = 3000):
        self.docs_dir = Path(docs_dir)
        self.max_doc_chars = max_doc_chars
        self._all_docs: list[DocEntry] | None = None

    def _load_all_docs(self) -> list[DocEntry]:
        """讀取 docs_dir 下所有 .md 文件。"""
        docs = []
        for md_file in sorted(self.docs_dir.rglob("*.md")):
            try:
                raw = md_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  Warning: Cannot read {md_file}: {e}")
                continue

            relative_path = str(md_file).replace("\\", "/")
            title = _parse_title(raw, md_file.stem)
            tags = _parse_tags(raw)
            content = _strip_frontmatter(raw)

            docs.append(DocEntry(
                path=relative_path,
                title=title,
                content=content,
                tags=tags,
            ))

        print(f"[Retriever] Loaded {len(docs)} documents from {self.docs_dir}")
        return docs

    @property
    def all_docs(self) -> list[DocEntry]:
        if self._all_docs is None:
            self._all_docs = self._load_all_docs()
        return self._all_docs

    def get_relevant_docs(self, question: str, top_k: int = 5) -> list[DocEntry]:
        """
        根據問題關鍵字，回傳最相關的 top_k 篇文件。
        若關鍵字搜尋分數全為 0（完全找不到），回傳前 top_k 篇（讓 LLM 自行判斷）。
        """
        # 斷詞：分割空白、逗號、中文全角逗號
        terms = [t for t in re.split(r"[\s,，。？?！!]+", question) if len(t) >= 2]
        if not terms:
            terms = [question]

        scored = []
        for doc in self.all_docs:
            score = _score_doc(doc, terms)
            scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)

        # 若最高分 > 0，只回傳有分數的；否則回傳全部前 top_k（fallback）
        if scored and scored[0][0] > 0:
            result = [doc for score, doc in scored if score > 0]
        else:
            result = [doc for _, doc in scored]

        return result[:top_k]

    def format_docs_for_context(self, docs: list[DocEntry]) -> str:
        """
        將文件列表格式化成可傳給 LLM 的 context 文字。
        每篇文件會被截斷到 max_doc_chars，避免 context 過長。
        """
        if not docs:
            return "（知識庫中沒有相關文件）"

        parts = []
        for i, doc in enumerate(docs, 1):
            content = doc.content
            if len(content) > self.max_doc_chars:
                content = content[: self.max_doc_chars] + "\n\n…（內容已截斷）"

            parts.append(
                f"### 文件 {i}：{doc.title}\n"
                f"路徑：`{doc.path}`\n"
                f"標籤：{', '.join(doc.tags) if doc.tags else '無'}\n\n"
                f"{content}"
            )

        return "\n\n---\n\n".join(parts)
