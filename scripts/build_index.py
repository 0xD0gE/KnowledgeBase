#!/usr/bin/env python3
"""
build_index.py

掃描 docs/ 目錄，建立搜尋索引 (data/search-index.json)
與文件清單 (data/docs-manifest.json)。

由 GitHub Actions build-index.yml 在每次 Push 時自動執行。
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone

DOCS_DIR = Path(os.environ.get("DOCS_DIR", "docs"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "data"))


def extract_frontmatter(content: str) -> dict:
    """解析 YAML frontmatter，回傳 dict。不依賴 PyYAML 的簡易解析。"""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    frontmatter_text = content[3:end].strip()
    result = {}
    for line in frontmatter_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def strip_frontmatter(content: str) -> str:
    """移除 frontmatter，回傳純 Markdown 內文。"""
    if not content.startswith("---"):
        return content
    end = content.find("---", 3)
    if end == -1:
        return content
    return content[end + 3:].strip()


def extract_headings(content: str) -> list:
    """提取 H1 ~ H3 標題文字。"""
    return re.findall(r"^#{1,3}\s+(.+)$", content, re.MULTILINE)


def make_summary(body: str, max_chars: int = 300) -> str:
    """移除 Markdown 語法，取前 max_chars 字元作為摘要。"""
    # 移除代碼塊
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    # 移除行內代碼
    body = re.sub(r"`[^`]+`", "", body)
    # 移除連結
    body = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", body)
    # 移除 HTML 標籤
    body = re.sub(r"<[^>]+>", "", body)
    # 移除多餘空白與換行
    body = re.sub(r"\s+", " ", body).strip()
    return body[:max_chars]


def parse_tags(tags_str: str) -> list:
    """將 tags 字串解析成陣列，支援逗號或空格分隔。"""
    if not tags_str:
        return []
    # 先用逗號分割，再去除空白
    parts = re.split(r"[,，]", tags_str)
    return [t.strip() for t in parts if t.strip()]


def build_index():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index = []
    manifest = {
        "files": [],
        "total": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    md_files = sorted(DOCS_DIR.rglob("*.md"))

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  Warning: Cannot read {md_file}: {e}")
            continue

        frontmatter = extract_frontmatter(content)
        body = strip_frontmatter(content)
        headings = extract_headings(body)
        summary = make_summary(body)

        # 計算相對路徑（以 repo 根目錄為基準）
        try:
            relative_path = str(md_file.relative_to(Path("."))).replace("\\", "/")
        except ValueError:
            relative_path = str(md_file).replace("\\", "/")

        # 文件標題：優先用 frontmatter title，其次用第一個 H1，最後用檔名
        title = (
            frontmatter.get("title")
            or (headings[0] if headings else None)
            or md_file.stem.replace("-", " ").replace("_", " ").title()
        )

        tags = parse_tags(frontmatter.get("tags", ""))
        updated = frontmatter.get("updated", "")

        entry = {
            "path": relative_path,
            "title": title,
            "tags": tags,
            "headings": headings,
            "summary": summary,
            "updated": updated,
        }
        index.append(entry)
        manifest["files"].append(relative_path)

        print(f"  Indexed: {relative_path} ({len(body)} chars, {len(headings)} headings)")

    manifest["total"] = len(index)

    # 寫出 search-index.json
    search_index_path = OUTPUT_DIR / "search-index.json"
    search_index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 寫出 docs-manifest.json
    manifest_path = OUTPUT_DIR / "docs-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nBuild complete: {len(index)} documents indexed")
    print(f"  -> {search_index_path}")
    print(f"  -> {manifest_path}")


if __name__ == "__main__":
    build_index()
