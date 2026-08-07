"""Tests for obsidian_wiki.docextract — PII redaction, sensitive folder detection,
HWPX extraction, and the extraction cache."""

from __future__ import annotations

import sqlite3
import struct
import zipfile
from pathlib import Path

import pytest

from obsidian_wiki.docextract import (
    SENSITIVE_FOLDER_HINTS,
    cached_extract,
    extract_hwpx_text,
    extract_text,
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
