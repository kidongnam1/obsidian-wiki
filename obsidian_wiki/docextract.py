"""Extract text from binary document formats (HWP, HWPX, PDF) with caching and PII redaction.

Adapted from patterns in the Ruby Obsidian HTML Studio project.  Optional
dependencies: ``olefile`` (HWP), ``pypdf`` (PDF).  HWPX uses only stdlib
(``zipfile`` + ``xml.etree``).

Usage from skills or CLI::

    from obsidian_wiki.docextract import extract_text, redact_pii

    text = extract_text(Path("document.hwp"))
    safe = redact_pii(text)
"""

from __future__ import annotations

import re
import sqlite3
import threading
import zlib
import zipfile
from pathlib import Path
from xml.etree import ElementTree
from typing import Optional

MAX_EXTRACTED_CHARS = 250_000

TEXT_EXTENSIONS = {".md", ".txt", ".csv", ".json", ".tsv", ".html"}
DOCUMENT_EXTENSIONS = {".pdf", ".hwp", ".hwpx"}
SEARCHABLE_EXTENSIONS = TEXT_EXTENSIONS | DOCUMENT_EXTENSIONS

SENSITIVE_FOLDER_HINTS = (
    "개인",
    "금융",
    "중요서류",
    "계좌",
    "비밀번호",
    "주민",
    "여권",
    "대출",
    "credentials",
    "secrets",
    "private",
)

# ---------------------------------------------------------------------------
# PII redaction
# ---------------------------------------------------------------------------

def redact_pii(text: str) -> str:
    """Mask personally identifiable information in *text*.

    Covers: email addresses, Korean resident registration numbers,
    phone numbers (Korean mobile), credit/account card-like digit
    sequences, bank account numbers, and API keys / tokens / passwords
    in ``key = value`` lines.
    """
    text = re.sub(
        r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[EMAIL_REDACTED]",
        text,
    )
    text = re.sub(r"\b\d{6}\s*-\s*\d{7}\b", "[RRN_REDACTED]", text)
    text = re.sub(r"\b(?:\d[ -]*?){13,19}\b", "[CARD_REDACTED]", text)
    text = re.sub(
        r"(?<!\d)(?:01[016789])[-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)",
        "[PHONE_REDACTED]",
        text,
    )
    text = re.sub(
        r"(?i)((?:계좌(?:번호)?|account)\s*[:=]?\s*)[\d -]{8,}",
        r"\1[ACCOUNT_REDACTED]",
        text,
    )
    text = re.sub(
        r"(?im)^(\s*(?:api[_ -]?key|token|password|passwd|secret)\s*[:=]\s*).+$",
        r"\1[SECRET_REDACTED]",
        text,
    )
    return text


# ---------------------------------------------------------------------------
# Sensitive folder detection
# ---------------------------------------------------------------------------

def is_sensitive_folder(path: Path) -> bool:
    """Return True if any component of *path* contains a sensitive hint."""
    parts_lower = [p.lower() for p in path.parts]
    return any(
        hint in part for part in parts_lower for hint in SENSITIVE_FOLDER_HINTS
    )


# ---------------------------------------------------------------------------
# Document extraction
# ---------------------------------------------------------------------------

def _parse_hwp_section(data: bytes, compressed: bool) -> str:
    if compressed:
        data = zlib.decompress(data, -15)
    position = 0
    paragraphs: list[str] = []
    while position + 4 <= len(data):
        header = int.from_bytes(data[position:position + 4], "little")
        position += 4
        tag_id = header & 0x3FF
        size = (header >> 20) & 0xFFF
        if size == 0xFFF:
            if position + 4 > len(data):
                break
            size = int.from_bytes(data[position:position + 4], "little")
            position += 4
        if size < 0 or position + size > len(data):
            break
        payload = data[position:position + size]
        position += size
        if tag_id != 67:
            continue
        text = payload.decode("utf-16le", errors="ignore")
        text = re.sub(r"[\x00-\x08\x0b-\x1f]", " ", text)
        text = re.sub(r"[ \t]+", " ", text).strip()
        if text:
            paragraphs.append(text)
        if sum(map(len, paragraphs)) >= MAX_EXTRACTED_CHARS:
            break
    return "\n".join(paragraphs)[:MAX_EXTRACTED_CHARS]


def extract_hwp_text(path: Path) -> str:
    """Extract text from a HWP (Hangul Word Processor) file.

    Requires the ``olefile`` package.
    """
    import olefile  # type: ignore[import-untyped]

    with olefile.OleFileIO(str(path)) as document:
        if not document.exists("FileHeader"):
            return ""
        header = document.openstream("FileHeader").read()
        flags = int.from_bytes(header[36:40], "little") if len(header) >= 40 else 0
        if flags & 0x02:
            return "[Password-protected HWP — cannot extract text]"
        compressed = bool(flags & 0x01)
        sections = [
            parts
            for parts in document.listdir(streams=True, storages=False)
            if len(parts) == 2
            and parts[0].casefold() == "bodytext"
            and parts[1].casefold().startswith("section")
        ]
        sections.sort(key=lambda parts: int(re.sub(r"\D", "", parts[1]) or "0"))
        contents: list[str] = []
        used = 0
        for parts in sections:
            text = _parse_hwp_section(document.openstream(parts).read(), compressed)
            remaining = MAX_EXTRACTED_CHARS - used
            if remaining <= 0:
                break
            contents.append(text[:remaining])
            used += len(contents[-1])
        return "\n".join(filter(None, contents))


def extract_hwpx_text(path: Path) -> str:
    """Extract text from a HWPX file (ZIP-based HWP format)."""
    chunks: list[str] = []
    used = 0
    with zipfile.ZipFile(path) as document:
        section_infos = sorted(
            info
            for info in document.infolist()
            if info.filename.casefold().startswith("contents/section")
            and info.filename.casefold().endswith(".xml")
            and info.file_size <= 8 * 1024 * 1024
        )
        for info in section_infos:
            root = ElementTree.fromstring(document.read(info))
            text = " ".join(
                node.text.strip()
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1] == "t"
                and node.text
                and node.text.strip()
            )
            remaining = MAX_EXTRACTED_CHARS - used
            if remaining <= 0:
                break
            chunks.append(text[:remaining])
            used += len(chunks[-1])
    return "\n".join(chunks)


def extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file.

    Requires the ``pypdf`` package.
    """
    from pypdf import PdfReader  # type: ignore[import-untyped]

    reader = PdfReader(str(path), strict=False)
    pages: list[str] = []
    used = 0
    for page in reader.pages[:200]:
        text = page.extract_text() or ""
        if not text.strip():
            continue
        remaining = MAX_EXTRACTED_CHARS - used
        if remaining <= 0:
            break
        pages.append(text[:remaining])
        used += len(pages[-1])
    return "\n\n".join(pages)


# ---------------------------------------------------------------------------
# Unified extraction entry point
# ---------------------------------------------------------------------------

def extract_text(path: Path) -> str:
    """Extract text from a file based on its extension.

    Returns the extracted text (capped at ``MAX_EXTRACTED_CHARS``), or an
    empty string for unsupported formats.
    """
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="replace")[:MAX_EXTRACTED_CHARS]
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix == ".hwp":
        return extract_hwp_text(path)
    if suffix == ".hwpx":
        return extract_hwpx_text(path)
    return ""


# ---------------------------------------------------------------------------
# SQLite extraction cache
# ---------------------------------------------------------------------------

_cache_lock = threading.Lock()
_memory_cache: dict[str, tuple[int, int, str]] = {}
_db_connections: dict[int, sqlite3.Connection] = {}


def _get_connection(db_path: Path) -> sqlite3.Connection:
    """Return a thread-local SQLite connection, creating the DB if needed."""
    tid = threading.get_ident()
    key_str = str(db_path)
    cache_key = hash((tid, key_str))
    conn = _db_connections.get(cache_key)
    if conn is not None:
        return conn
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS document_text (
            cache_key TEXT PRIMARY KEY,
            mtime_ns  INTEGER NOT NULL,
            size      INTEGER NOT NULL,
            content   TEXT    NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    _db_connections[cache_key] = conn
    return conn


def cached_extract(path: Path, cache_db: Optional[Path] = None) -> str:
    """Extract text with a two-tier cache (in-memory LRU + SQLite on disk).

    *cache_db* defaults to ``<path-parent>/.cache/docextract.sqlite3``.
    """
    from datetime import datetime

    if cache_db is None:
        cache_db = path.parent / ".cache" / "docextract.sqlite3"

    stat = path.stat()
    cache_key = str(path.resolve())

    with _cache_lock:
        cached = _memory_cache.get(cache_key)
        if cached and cached[:2] == (stat.st_mtime_ns, stat.st_size):
            return cached[2]

    conn = _get_connection(cache_db)
    row = conn.execute(
        "SELECT content FROM document_text WHERE cache_key = ? AND mtime_ns = ? AND size = ?",
        (cache_key, stat.st_mtime_ns, stat.st_size),
    ).fetchone()
    if row:
        content = str(row[0])
        with _cache_lock:
            _memory_cache[cache_key] = (stat.st_mtime_ns, stat.st_size, content)
        return content

    content = extract_text(path)

    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO document_text(cache_key, mtime_ns, size, content, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            mtime_ns = excluded.mtime_ns,
            size = excluded.size,
            content = excluded.content,
            updated_at = excluded.updated_at
        """,
        (cache_key, stat.st_mtime_ns, stat.st_size, content, now),
    )
    conn.commit()

    with _cache_lock:
        if len(_memory_cache) >= 500:
            _memory_cache.pop(next(iter(_memory_cache)))
        _memory_cache[cache_key] = (stat.st_mtime_ns, stat.st_size, content)

    return content
