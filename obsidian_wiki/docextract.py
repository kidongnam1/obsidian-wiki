"""Extract text from binary document formats with caching and PII redaction.

Supported formats:
- HWP / HWPX (Korean word processor) — ``olefile`` (HWP only) / stdlib
- PDF — ``pypdf``
- DOCX / XLSX / PPTX (Office Open XML) — stdlib (``zipfile`` + ``xml.etree``)
- DOC / XLS / PPT (legacy Office binary) — ``olefile``

Usage from skills or CLI::

    from obsidian_wiki.docextract import extract_text, redact_pii

    text = extract_text(Path("document.hwp"))
    safe = redact_pii(text)
"""

from __future__ import annotations

import re
import sqlite3
import struct
import threading
import zlib
import zipfile
from pathlib import Path
from xml.etree import ElementTree
from typing import Optional

MAX_EXTRACTED_CHARS = 250_000

TEXT_EXTENSIONS = {".md", ".txt", ".csv", ".json", ".tsv", ".html"}
DOCUMENT_EXTENSIONS = {
    ".pdf", ".hwp", ".hwpx",
    ".docx", ".xlsx", ".pptx",
    ".doc", ".xls", ".ppt",
}
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
# Office Open XML extraction (DOCX, XLSX, PPTX) — stdlib only
# ---------------------------------------------------------------------------

_OOXML_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}


def extract_docx_text(path: Path) -> str:
    """Extract text from a DOCX file (Office Open XML)."""
    paragraphs: list[str] = []
    used = 0
    with zipfile.ZipFile(path) as zf:
        try:
            xml_data = zf.read("word/document.xml")
        except KeyError:
            return ""
        root = ElementTree.fromstring(xml_data)
        for para in root.iter(f"{{{_OOXML_NS['w']}}}p"):
            texts: list[str] = []
            for t_elem in para.iter(f"{{{_OOXML_NS['w']}}}t"):
                if t_elem.text:
                    texts.append(t_elem.text)
            line = "".join(texts).strip()
            if not line:
                continue
            remaining = MAX_EXTRACTED_CHARS - used
            if remaining <= 0:
                break
            paragraphs.append(line[:remaining])
            used += len(paragraphs[-1])
    return "\n".join(paragraphs)


def extract_xlsx_text(path: Path) -> str:
    """Extract text from an XLSX file (Office Open XML)."""
    ns = _OOXML_NS["r"]
    shared_strings: list[str] = []
    with zipfile.ZipFile(path) as zf:
        if "xl/sharedStrings.xml" in zf.namelist():
            ss_root = ElementTree.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in ss_root.iter(f"{{{ns}}}si"):
                parts: list[str] = []
                for t_elem in si.iter(f"{{{ns}}}t"):
                    if t_elem.text:
                        parts.append(t_elem.text)
                shared_strings.append("".join(parts))

        rows_out: list[str] = []
        used = 0
        sheet_names = sorted(
            n for n in zf.namelist()
            if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
        )
        for sheet_name in sheet_names:
            sheet_root = ElementTree.fromstring(zf.read(sheet_name))
            for row in sheet_root.iter(f"{{{ns}}}row"):
                cells: list[str] = []
                for cell in row.iter(f"{{{ns}}}c"):
                    cell_type = cell.get("t", "")
                    v_elem = cell.find(f"{{{ns}}}v")
                    if v_elem is not None and v_elem.text:
                        if cell_type == "s":
                            idx = int(v_elem.text)
                            if idx < len(shared_strings):
                                cells.append(shared_strings[idx])
                        else:
                            cells.append(v_elem.text)
                    else:
                        is_elem = cell.find(f"{{{ns}}}is")
                        if is_elem is not None:
                            inline_parts = []
                            for t_el in is_elem.iter(f"{{{ns}}}t"):
                                if t_el.text:
                                    inline_parts.append(t_el.text)
                            if inline_parts:
                                cells.append("".join(inline_parts))
                if cells:
                    line = "\t".join(cells)
                    remaining = MAX_EXTRACTED_CHARS - used
                    if remaining <= 0:
                        break
                    rows_out.append(line[:remaining])
                    used += len(rows_out[-1])
            if used >= MAX_EXTRACTED_CHARS:
                break
    return "\n".join(rows_out)


def extract_pptx_text(path: Path) -> str:
    """Extract text from a PPTX file (Office Open XML)."""
    ns_a = _OOXML_NS["a"]
    slides_text: list[str] = []
    used = 0
    with zipfile.ZipFile(path) as zf:
        slide_names = sorted(
            n for n in zf.namelist()
            if n.startswith("ppt/slides/slide") and n.endswith(".xml")
        )
        for slide_name in slide_names:
            root = ElementTree.fromstring(zf.read(slide_name))
            paragraphs: list[str] = []
            for para in root.iter(f"{{{ns_a}}}p"):
                runs: list[str] = []
                for t_elem in para.iter(f"{{{ns_a}}}t"):
                    if t_elem.text:
                        runs.append(t_elem.text)
                line = "".join(runs).strip()
                if line:
                    paragraphs.append(line)
            if paragraphs:
                slide_block = "\n".join(paragraphs)
                remaining = MAX_EXTRACTED_CHARS - used
                if remaining <= 0:
                    break
                slides_text.append(slide_block[:remaining])
                used += len(slides_text[-1])
    return "\n\n".join(slides_text)


# ---------------------------------------------------------------------------
# Legacy Office binary extraction (DOC, XLS, PPT) — requires olefile
# ---------------------------------------------------------------------------

def extract_doc_text(path: Path) -> str:
    """Extract text from a legacy DOC file (Word Binary File Format).

    Requires the ``olefile`` package. Parses the piece table in the Table
    stream to reassemble document text from CP1252 and UTF-16LE pieces.
    Returns an empty string for corrupt or invalid files.
    """
    import olefile  # type: ignore[import-untyped]

    try:
        ole = olefile.OleFileIO(str(path))
    except Exception:
        return ""
    with ole:
        if not ole.exists("WordDocument"):
            return ""
        word_stream = ole.openstream("WordDocument").read()
        if len(word_stream) < 48:
            return ""

        flags = struct.unpack_from("<H", word_stream, 0x000A)[0]
        table_name = "1Table" if (flags & 0x0200) else "0Table"
        if not ole.exists(table_name):
            return ""
        table_stream = ole.openstream(table_name).read()

        fc_clx = struct.unpack_from("<I", word_stream, 0x01A2)[0]
        lcb_clx = struct.unpack_from("<I", word_stream, 0x01A6)[0]
        if fc_clx == 0 or lcb_clx == 0:
            return ""
        if fc_clx + lcb_clx > len(table_stream):
            return ""
        clx = table_stream[fc_clx:fc_clx + lcb_clx]

        pos = 0
        while pos < len(clx) and clx[pos] == 0x01:
            if pos + 1 >= len(clx):
                break
            grpprl_len = struct.unpack_from("<H", clx, pos + 1)[0]
            pos += 3 + grpprl_len

        if pos >= len(clx) or clx[pos] != 0x02:
            return ""
        pos += 1
        if pos + 4 > len(clx):
            return ""
        pcdt_size = struct.unpack_from("<I", clx, pos)[0]
        pos += 4
        if pos + pcdt_size > len(clx):
            return ""
        pcd_data = clx[pos:pos + pcdt_size]

        n_pieces = (pcdt_size - 4) // 12
        if n_pieces <= 0:
            return ""
        cp_offsets = []
        for i in range(n_pieces + 1):
            cp_offsets.append(struct.unpack_from("<I", pcd_data, i * 4)[0])

        pcd_start = (n_pieces + 1) * 4
        text_parts: list[str] = []
        used = 0
        for i in range(n_pieces):
            if pcd_start + i * 8 + 8 > len(pcd_data):
                break
            pcd_entry = pcd_data[pcd_start + i * 8:pcd_start + (i + 1) * 8]
            fc_value = struct.unpack_from("<I", pcd_entry, 2)[0]
            is_ansi = bool(fc_value & 0x40000000)
            fc_value &= 0x3FFFFFFF

            char_count = cp_offsets[i + 1] - cp_offsets[i]
            if is_ansi:
                offset = fc_value // 2
                end = offset + char_count
                if end <= len(word_stream):
                    chunk = word_stream[offset:end].decode("cp1252", errors="replace")
                else:
                    continue
            else:
                offset = fc_value
                byte_count = char_count * 2
                end = offset + byte_count
                if end <= len(word_stream):
                    chunk = word_stream[offset:end].decode("utf-16le", errors="replace")
                else:
                    continue

            remaining = MAX_EXTRACTED_CHARS - used
            if remaining <= 0:
                break
            text_parts.append(chunk[:remaining])
            used += len(text_parts[-1])

        result = "".join(text_parts)
        result = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", result)
        return result.strip()


def extract_xls_text(path: Path) -> str:
    """Extract text from a legacy XLS file (BIFF8 format).

    Requires the ``olefile`` package. Reads the Shared String Table (SST)
    to extract all unique cell text values.
    Returns an empty string for corrupt or invalid files.
    """
    import olefile  # type: ignore[import-untyped]

    try:
        ole = olefile.OleFileIO(str(path))
    except Exception:
        return ""
    with ole:
        stream_name = None
        for candidate in ("Workbook", "Book"):
            if ole.exists(candidate):
                stream_name = candidate
                break
        if stream_name is None:
            return ""
        data = ole.openstream(stream_name).read()

    strings: list[str] = []
    used = 0
    pos = 0
    while pos + 4 <= len(data):
        rec_type = struct.unpack_from("<H", data, pos)[0]
        rec_len = struct.unpack_from("<H", data, pos + 2)[0]
        pos += 4
        if pos + rec_len > len(data):
            break

        if rec_type == 0x00FC:
            sst_data = data[pos:pos + rec_len]
            if len(sst_data) < 8:
                pos += rec_len
                continue
            total_strings = struct.unpack_from("<I", sst_data, 4)[0]
            sst_pos = 8
            for _ in range(total_strings):
                if sst_pos + 3 > len(sst_data):
                    break
                char_count = struct.unpack_from("<H", sst_data, sst_pos)[0]
                flags = sst_data[sst_pos + 2]
                sst_pos += 3
                is_wide = bool(flags & 0x01)
                has_rich = bool(flags & 0x08)
                has_ext = bool(flags & 0x04)
                if has_rich:
                    if sst_pos + 2 > len(sst_data):
                        break
                    rich_runs = struct.unpack_from("<H", sst_data, sst_pos)[0]
                    sst_pos += 2
                else:
                    rich_runs = 0
                if has_ext:
                    if sst_pos + 4 > len(sst_data):
                        break
                    ext_size = struct.unpack_from("<I", sst_data, sst_pos)[0]
                    sst_pos += 4
                else:
                    ext_size = 0

                if is_wide:
                    byte_len = char_count * 2
                    if sst_pos + byte_len > len(sst_data):
                        break
                    text = sst_data[sst_pos:sst_pos + byte_len].decode(
                        "utf-16le", errors="replace"
                    )
                    sst_pos += byte_len
                else:
                    if sst_pos + char_count > len(sst_data):
                        break
                    text = sst_data[sst_pos:sst_pos + char_count].decode(
                        "cp1252", errors="replace"
                    )
                    sst_pos += char_count

                sst_pos += rich_runs * 4
                sst_pos += ext_size

                text = text.strip()
                if text:
                    remaining = MAX_EXTRACTED_CHARS - used
                    if remaining <= 0:
                        break
                    strings.append(text[:remaining])
                    used += len(strings[-1])
            break
        pos += rec_len

    return "\n".join(strings)


def extract_ppt_text(path: Path) -> str:
    """Extract text from a legacy PPT file (PowerPoint Binary format).

    Requires the ``olefile`` package. Scans for TextBytesAtom (0x0FA8)
    and TextCharsAtom (0x0FA0) records in the PowerPoint Document stream.
    Returns an empty string for corrupt or invalid files.
    """
    import olefile  # type: ignore[import-untyped]

    try:
        ole = olefile.OleFileIO(str(path))
    except Exception:
        return ""
    with ole:
        if not ole.exists("PowerPoint Document"):
            return ""
        data = ole.openstream("PowerPoint Document").read()

    text_parts: list[str] = []
    used = 0
    pos = 0
    while pos + 8 <= len(data):
        rec_ver_inst = struct.unpack_from("<H", data, pos)[0]
        rec_type = struct.unpack_from("<H", data, pos + 2)[0]
        rec_len = struct.unpack_from("<I", data, pos + 4)[0]
        pos += 8
        is_container = (rec_ver_inst & 0x0F) == 0x0F
        if is_container:
            continue

        if rec_type == 0x0FA0:
            end = pos + rec_len
            if end <= len(data):
                text = data[pos:end].decode("utf-16le", errors="replace").strip()
                if text:
                    remaining = MAX_EXTRACTED_CHARS - used
                    if remaining <= 0:
                        break
                    text_parts.append(text[:remaining])
                    used += len(text_parts[-1])
        elif rec_type == 0x0FA8:
            end = pos + rec_len
            if end <= len(data):
                text = data[pos:end].decode("cp1252", errors="replace").strip()
                if text:
                    remaining = MAX_EXTRACTED_CHARS - used
                    if remaining <= 0:
                        break
                    text_parts.append(text[:remaining])
                    used += len(text_parts[-1])

        pos += rec_len

    result = "\n".join(text_parts)
    result = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", result)
    return result.strip()


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
    extractors = {
        ".pdf": extract_pdf_text,
        ".hwp": extract_hwp_text,
        ".hwpx": extract_hwpx_text,
        ".docx": extract_docx_text,
        ".xlsx": extract_xlsx_text,
        ".pptx": extract_pptx_text,
        ".doc": extract_doc_text,
        ".xls": extract_xls_text,
        ".ppt": extract_ppt_text,
    }
    fn = extractors.get(suffix)
    if fn is not None:
        return fn(path)
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
