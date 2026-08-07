"""Tests for obsidian_wiki.docextract — PII redaction, sensitive folder detection,
document extraction (HWPX, DOCX, XLSX, PPTX, DOC, XLS, PPT), and the extraction cache."""

from __future__ import annotations

import sqlite3
import struct
import zipfile
from pathlib import Path

import pytest

from obsidian_wiki.docextract import (
    SENSITIVE_FOLDER_HINTS,
    cached_extract,
    extract_docx_text,
    extract_hwpx_text,
    extract_pptx_text,
    extract_text,
    extract_xlsx_text,
    is_sensitive_folder,
    redact_pii,
)


# ---------------------------------------------------------------------------
# PII redaction
# ---------------------------------------------------------------------------

class TestRedactPii:
    def test_email(self):
        assert redact_pii("contact user@example.com now") == "contact [EMAIL_REDACTED] now"

    def test_rrn(self):
        assert "[RRN_REDACTED]" in redact_pii("주민번호: 900101-1234567")

    def test_phone(self):
        assert "[PHONE_REDACTED]" in redact_pii("전화번호 010-1234-5678")

    def test_card(self):
        assert "[CARD_REDACTED]" in redact_pii("카드 1234-5678-9012-3456")

    def test_account(self):
        assert "[ACCOUNT_REDACTED]" in redact_pii("계좌번호: 110-123-456789")

    def test_secret(self):
        assert "[SECRET_REDACTED]" in redact_pii("api_key = sk-abc123xyz")

    def test_no_false_positives(self):
        safe = "Hello world, this is normal text."
        assert redact_pii(safe) == safe


# ---------------------------------------------------------------------------
# Sensitive folder detection
# ---------------------------------------------------------------------------

class TestSensitiveFolder:
    @pytest.mark.parametrize("name", list(SENSITIVE_FOLDER_HINTS))
    def test_sensitive_names(self, name):
        assert is_sensitive_folder(Path(f"/vault/{name}/file.md"))

    def test_normal_folder(self):
        assert not is_sensitive_folder(Path("/vault/projects/readme.md"))

    def test_nested(self):
        assert is_sensitive_folder(Path("/vault/docs/개인/notes.md"))


# ---------------------------------------------------------------------------
# HWPX extraction
# ---------------------------------------------------------------------------

def _make_hwpx(tmp_path: Path, text_content: str) -> Path:
    """Create a minimal HWPX file with one section containing *text_content*."""
    hwpx_path = tmp_path / "test.hwpx"
    xml_body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sec xmlns="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        f"<p><run><t>{text_content}</t></run></p>"
        "</sec>"
    )
    with zipfile.ZipFile(hwpx_path, "w") as zf:
        zf.writestr("Contents/section0.xml", xml_body)
    return hwpx_path


class TestHwpxExtraction:
    def test_basic(self, tmp_path):
        path = _make_hwpx(tmp_path, "한글 테스트 문장입니다")
        result = extract_hwpx_text(path)
        assert "한글 테스트 문장입니다" in result

    def test_empty(self, tmp_path):
        path = tmp_path / "empty.hwpx"
        xml_body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sec xmlns="http://www.hancom.co.kr/hwpml/2011/paragraph">'
            "<p><run><t> </t></run></p>"
            "</sec>"
        )
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("Contents/section0.xml", xml_body)
        result = extract_hwpx_text(path)
        assert result.strip() == ""


# ---------------------------------------------------------------------------
# Text extraction dispatch
# ---------------------------------------------------------------------------

class TestExtractText:
    def test_txt(self, tmp_path):
        p = tmp_path / "notes.txt"
        p.write_text("plain text content", encoding="utf-8")
        assert extract_text(p) == "plain text content"

    def test_md(self, tmp_path):
        p = tmp_path / "readme.md"
        p.write_text("# Title\n\nBody", encoding="utf-8")
        assert "# Title" in extract_text(p)

    def test_unsupported(self, tmp_path):
        p = tmp_path / "binary.bin"
        p.write_bytes(b"\x00\x01\x02")
        assert extract_text(p) == ""


# ---------------------------------------------------------------------------
# Cached extraction
# ---------------------------------------------------------------------------

class TestCachedExtract:
    def test_creates_cache_db(self, tmp_path):
        p = tmp_path / "doc.txt"
        p.write_text("cached content", encoding="utf-8")
        db_path = tmp_path / ".cache" / "test.sqlite3"

        result = cached_extract(p, cache_db=db_path)
        assert result == "cached content"
        assert db_path.exists()

        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT content FROM document_text").fetchone()
        conn.close()
        assert row[0] == "cached content"

    def test_cache_hit(self, tmp_path):
        p = tmp_path / "doc.txt"
        p.write_text("original", encoding="utf-8")
        db_path = tmp_path / ".cache" / "test.sqlite3"

        r1 = cached_extract(p, cache_db=db_path)
        r2 = cached_extract(p, cache_db=db_path)
        assert r1 == r2 == "original"

    def test_cache_invalidation(self, tmp_path):
        p = tmp_path / "doc.txt"
        p.write_text("version1", encoding="utf-8")
        db_path = tmp_path / ".cache" / "test.sqlite3"

        assert cached_extract(p, cache_db=db_path) == "version1"

        p.write_text("version2", encoding="utf-8")
        assert cached_extract(p, cache_db=db_path) == "version2"


# ---------------------------------------------------------------------------
# DOCX extraction
# ---------------------------------------------------------------------------

def _make_docx(tmp_path: Path, paragraphs: list[str]) -> Path:
    """Create a minimal DOCX file with the given paragraphs."""
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body_paras = "".join(
        f'<w:p><w:r><w:t>{text}</w:t></w:r></w:p>' for text in paragraphs
    )
    document_xml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{ns}"><w:body>{body_paras}</w:body></w:document>'
    )
    docx_path = tmp_path / "test.docx"
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr("word/document.xml", document_xml)
    return docx_path


class TestDocxExtraction:
    def test_basic(self, tmp_path):
        path = _make_docx(tmp_path, ["Hello World", "Second paragraph"])
        result = extract_docx_text(path)
        assert "Hello World" in result
        assert "Second paragraph" in result

    def test_korean(self, tmp_path):
        path = _make_docx(tmp_path, ["한글 문서 테스트입니다"])
        result = extract_docx_text(path)
        assert "한글 문서 테스트입니다" in result

    def test_empty(self, tmp_path):
        path = _make_docx(tmp_path, [])
        result = extract_docx_text(path)
        assert result == ""

    def test_extract_text_dispatch(self, tmp_path):
        path = _make_docx(tmp_path, ["Dispatched content"])
        result = extract_text(path)
        assert "Dispatched content" in result


# ---------------------------------------------------------------------------
# XLSX extraction
# ---------------------------------------------------------------------------

def _make_xlsx(tmp_path: Path, rows: list[list[str]]) -> Path:
    """Create a minimal XLSX file with the given rows using shared strings."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

    all_strings = []
    for row in rows:
        for cell in row:
            if cell not in all_strings:
                all_strings.append(cell)

    si_entries = "".join(f"<si><t>{s}</t></si>" for s in all_strings)
    shared_strings_xml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<sst xmlns="{ns}" count="{sum(len(r) for r in rows)}" '
        f'uniqueCount="{len(all_strings)}">{si_entries}</sst>'
    )

    sheet_rows = []
    for row_idx, row in enumerate(rows, 1):
        cells_xml = []
        for col_idx, cell_val in enumerate(row):
            col_letter = chr(65 + col_idx)
            ref = f"{col_letter}{row_idx}"
            str_idx = all_strings.index(cell_val)
            cells_xml.append(f'<c r="{ref}" t="s"><v>{str_idx}</v></c>')
        sheet_rows.append(f'<row r="{row_idx}">{"".join(cells_xml)}</row>')

    sheet_xml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<worksheet xmlns="{ns}"><sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    )

    xlsx_path = tmp_path / "test.xlsx"
    with zipfile.ZipFile(xlsx_path, "w") as zf:
        zf.writestr("xl/sharedStrings.xml", shared_strings_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return xlsx_path


class TestXlsxExtraction:
    def test_basic(self, tmp_path):
        path = _make_xlsx(tmp_path, [["Name", "Age"], ["Alice", "30"]])
        result = extract_xlsx_text(path)
        assert "Name" in result
        assert "Alice" in result

    def test_korean(self, tmp_path):
        path = _make_xlsx(tmp_path, [["이름", "나이"], ["홍길동", "25"]])
        result = extract_xlsx_text(path)
        assert "홍길동" in result

    def test_empty(self, tmp_path):
        ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        xlsx_path = tmp_path / "empty.xlsx"
        sheet_xml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<worksheet xmlns="{ns}"><sheetData></sheetData></worksheet>'
        )
        with zipfile.ZipFile(xlsx_path, "w") as zf:
            zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        result = extract_xlsx_text(xlsx_path)
        assert result == ""

    def test_extract_text_dispatch(self, tmp_path):
        path = _make_xlsx(tmp_path, [["dispatched", "cell"]])
        result = extract_text(path)
        assert "dispatched" in result


# ---------------------------------------------------------------------------
# PPTX extraction
# ---------------------------------------------------------------------------

def _make_pptx(tmp_path: Path, slides: list[list[str]]) -> Path:
    """Create a minimal PPTX file. Each inner list is one slide's text runs."""
    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    ns_p = "http://schemas.openxmlformats.org/presentationml/2006/main"

    pptx_path = tmp_path / "test.pptx"
    with zipfile.ZipFile(pptx_path, "w") as zf:
        for slide_idx, texts in enumerate(slides, 1):
            paras = "".join(
                f'<a:p xmlns:a="{ns_a}"><a:r><a:t>{t}</a:t></a:r></a:p>'
                for t in texts
            )
            slide_xml = (
                f'<?xml version="1.0" encoding="UTF-8"?>'
                f'<p:sld xmlns:p="{ns_p}" xmlns:a="{ns_a}">'
                f'<p:cSld><p:spTree><p:sp><p:txBody>{paras}</p:txBody></p:sp></p:spTree></p:cSld>'
                f'</p:sld>'
            )
            zf.writestr(f"ppt/slides/slide{slide_idx}.xml", slide_xml)
    return pptx_path


class TestPptxExtraction:
    def test_basic(self, tmp_path):
        path = _make_pptx(tmp_path, [["Slide One Title", "Subtitle"]])
        result = extract_pptx_text(path)
        assert "Slide One Title" in result
        assert "Subtitle" in result

    def test_multiple_slides(self, tmp_path):
        path = _make_pptx(tmp_path, [["First"], ["Second"], ["Third"]])
        result = extract_pptx_text(path)
        assert "First" in result
        assert "Third" in result

    def test_korean(self, tmp_path):
        path = _make_pptx(tmp_path, [["발표 제목", "내용입니다"]])
        result = extract_pptx_text(path)
        assert "발표 제목" in result

    def test_extract_text_dispatch(self, tmp_path):
        path = _make_pptx(tmp_path, [["dispatched slide"]])
        result = extract_text(path)
        assert "dispatched slide" in result


# ---------------------------------------------------------------------------
# Legacy format extraction (DOC, XLS, PPT) — dispatch only, requires olefile
# ---------------------------------------------------------------------------

class TestLegacyFormatDispatch:
    """Test that extract_text dispatches to legacy extractors for .doc/.xls/.ppt
    and handles invalid files gracefully."""

    def test_doc_invalid_returns_empty(self, tmp_path):
        p = tmp_path / "test.doc"
        p.write_bytes(b"\x00\x01\x02")
        assert extract_text(p) == ""

    def test_xls_invalid_returns_empty(self, tmp_path):
        p = tmp_path / "test.xls"
        p.write_bytes(b"\x00\x01\x02")
        assert extract_text(p) == ""

    def test_ppt_invalid_returns_empty(self, tmp_path):
        p = tmp_path / "test.ppt"
        p.write_bytes(b"\x00\x01\x02")
        assert extract_text(p) == ""
