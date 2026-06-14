"""Structure-aware text chunking for RAG evidence."""

from __future__ import annotations

import re
from typing import List


SENTENCE_PATTERN = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?")


def semantic_chunk_text(
    text: str,
    *,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[str]:
    """Split text by structure first, then sentence, with fixed-window fallback."""
    normalized = _normalize_text(text)
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    units: List[str] = []
    for block in _split_blocks(normalized):
        units.extend(_split_long_block(block, chunk_size))

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for unit in units:
        separator_len = 1 if current else 0
        if current and current_len + separator_len + len(unit) > chunk_size:
            _flush(chunks, current)
            current = []
            current_len = 0

            tail = _tail_context(chunks[-1], overlap) if chunks and overlap > 0 else ""
            if tail and len(tail) + 1 + len(unit) <= chunk_size:
                current.append(tail)
                current_len = len(tail)

        current.append(unit)
        current_len += (1 if current_len else 0) + len(unit)

    _flush(chunks, current)
    return chunks


def _normalize_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _split_blocks(text: str) -> List[str]:
    blocks: List[str] = []
    current: List[str] = []

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            _flush(blocks, current)
            current = []
            continue

        if _starts_new_block(line, current):
            _flush(blocks, current)
            current = []

        current.append(line)

    _flush(blocks, current)
    return blocks


def _starts_new_block(line: str, current: List[str]) -> bool:
    if not current:
        return False
    if _is_heading(line):
        return True
    if _is_list_item(line) and not _is_list_item(current[-1]):
        return True
    return False


def _is_heading(line: str) -> bool:
    if len(line) > 40:
        return False
    return bool(
        re.match(r"^(#{1,6}\s+|[一二三四五六七八九十\d]+[、.)．]\s*)", line)
        or re.search(r"(岗位职责|任职要求|项目经历|工作经历|教育经历|技能|证书|总结|背景)$", line)
    )


def _is_list_item(line: str) -> bool:
    return bool(re.match(r"^([-*•]|\d+[.)、]|[（(][一二三四五六七八九十\d]+[）)])\s*", line))


def _split_long_block(block: str, chunk_size: int) -> List[str]:
    if len(block) <= chunk_size:
        return [block]

    sentences = [item.group(0).strip() for item in SENTENCE_PATTERN.finditer(block) if item.group(0).strip()]
    if not sentences:
        return _hard_split(block, chunk_size)

    parts: List[str] = []
    current: List[str] = []
    current_len = 0
    for sentence in sentences:
        if len(sentence) > chunk_size:
            _flush(parts, current)
            current = []
            current_len = 0
            parts.extend(_hard_split(sentence, chunk_size))
            continue

        separator_len = 1 if current else 0
        if current and current_len + separator_len + len(sentence) > chunk_size:
            _flush(parts, current)
            current = []
            current_len = 0

        current.append(sentence)
        current_len += (1 if current_len else 0) + len(sentence)

    _flush(parts, current)
    return parts


def _hard_split(text: str, chunk_size: int) -> List[str]:
    parts: List[str] = []
    start = 0
    while start < len(text):
        part = text[start:start + chunk_size].strip()
        if part:
            parts.append(part)
        start += chunk_size
    return parts


def _tail_context(text: str, overlap: int) -> str:
    if not text or overlap <= 0:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        tail = lines[-1]
        if len(tail) <= overlap:
            return tail
    sentences = [item.group(0).strip() for item in SENTENCE_PATTERN.finditer(text) if item.group(0).strip()]
    if sentences and len(sentences[-1]) <= overlap:
        return sentences[-1]
    return text[-overlap:].strip()


def _flush(target: List[str], items: List[str]) -> None:
    if not items:
        return
    value = "\n".join(item for item in items if item and item.strip()).strip()
    if value:
        target.append(value)
