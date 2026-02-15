"""Tests for BE.file_store — async file persistence service."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from BE.file_store import (
    MAX_UPLOAD_SIZE,
    PageText,
    _decode_data_url,
    _extract_pdf_pages,
    _fetch_upload,
    get_file_content,
    get_file_pages,
    sanitize_filename,
    save_file,
)


@pytest.fixture
def run():
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop.run_until_complete
    loop.close()


def _make_db_session(upload_obj=None):
    """Create a mock async DB session that returns *upload_obj* from execute()."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = upload_obj

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.execute = AsyncMock(return_value=mock_result)
    return mock_session


def _make_upload(content, mime_type="text/plain", original_name="test.txt"):
    upload = MagicMock()
    upload.content = content
    upload.mime_type = mime_type
    upload.original_name = original_name
    return upload


class TestDecodeDataUrl:
    def test_strips_prefix_and_decodes(self):
        raw = b"hello world"
        data_url = f"data:text/plain;base64,{base64.b64encode(raw).decode()}"
        assert _decode_data_url(data_url) == raw

    def test_plain_base64_without_prefix(self):
        raw = b"no prefix"
        b64 = base64.b64encode(raw).decode()
        assert _decode_data_url(b64) == raw

    def test_binary_content(self):
        raw = bytes(range(256))
        data_url = (
            f"data:application/octet-stream;base64,{base64.b64encode(raw).decode()}"
        )
        assert _decode_data_url(data_url) == raw


class TestSanitizeFilename:
    def test_strips_control_characters(self):
        assert sanitize_filename("file\x00name\x1f.txt") == "filename.txt"

    def test_strips_brackets(self):
        assert sanitize_filename("[malicious].txt") == "malicious.txt"

    def test_limits_length_to_255(self):
        long_name = "a" * 500
        assert len(sanitize_filename(long_name)) == 255

    def test_normal_filename_unchanged(self):
        assert sanitize_filename("report.pdf") == "report.pdf"

    def test_empty_string(self):
        assert sanitize_filename("") == ""


class TestSaveFile:
    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_save_file_returns_uuid(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        raw = b"a,b,c\n1,2,3"
        data_url = f"data:text/csv;base64,{base64.b64encode(raw).decode()}"

        result = run(
            save_file(
                original_name="data.csv",
                mime_type="text/csv",
                data_url_content=data_url,
                size_bytes=len(raw),
                user_id="user-1",
                session_id="sess-1",
            )
        )

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_save_file_stores_actual_size_not_declared(
        self, mock_settings, mock_factory, run
    ):
        """Issue 2: size_bytes stored should be len(raw_bytes), not client-declared."""
        mock_settings.POSTGRES_ENABLED = True

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        raw = b"file content here"
        data_url = f"data:text/plain;base64,{base64.b64encode(raw).decode()}"

        run(
            save_file(
                original_name="test.txt",
                mime_type="text/plain",
                data_url_content=data_url,
                size_bytes=1,  # client lies about size
                user_id="user-1",
            )
        )

        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.content == raw
        assert added_obj.size_bytes == len(raw)  # actual decoded size
        assert added_obj.original_name == "test.txt"
        assert added_obj.mime_type == "text/plain"

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_save_file_rejects_oversized_file(self, mock_settings, mock_factory, run):
        """Issue 2: Files exceeding MAX_UPLOAD_SIZE are rejected."""
        mock_settings.POSTGRES_ENABLED = True

        # Create content just over the limit
        raw = b"x" * (MAX_UPLOAD_SIZE + 1)
        data_url = (
            f"data:application/octet-stream;base64,{base64.b64encode(raw).decode()}"
        )

        result = run(
            save_file(
                original_name="huge.bin",
                mime_type="application/octet-stream",
                data_url_content=data_url,
                size_bytes=1,  # client declares small
                user_id="user-1",
            )
        )
        assert result is None

    @patch("BE.config.settings")
    def test_save_file_empty_content_returns_none(self, mock_settings, run):
        mock_settings.POSTGRES_ENABLED = True

        result = run(
            save_file(
                original_name="empty.txt",
                mime_type="text/plain",
                data_url_content="",
                size_bytes=0,
                user_id="user-1",
            )
        )
        assert result is None

    @patch("BE.config.settings")
    def test_save_file_invalid_data_url_returns_none(self, mock_settings, run):
        mock_settings.POSTGRES_ENABLED = True

        result = run(
            save_file(
                original_name="bad.txt",
                mime_type="text/plain",
                data_url_content="data:text/plain;base64,!!!not-valid-b64!!!",
                size_bytes=10,
                user_id="user-1",
            )
        )
        assert result is None

    @patch("BE.config.settings")
    def test_save_file_postgres_disabled_returns_none(self, mock_settings, run):
        mock_settings.POSTGRES_ENABLED = False

        raw = b"content"
        data_url = f"data:text/plain;base64,{base64.b64encode(raw).decode()}"

        result = run(
            save_file(
                original_name="test.txt",
                mime_type="text/plain",
                data_url_content=data_url,
                size_bytes=len(raw),
                user_id="user-1",
            )
        )
        assert result is None

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_save_file_db_error_returns_none(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit.side_effect = RuntimeError("DB down")
        mock_factory.return_value = MagicMock(return_value=mock_session)

        raw = b"content"
        data_url = f"data:text/plain;base64,{base64.b64encode(raw).decode()}"

        result = run(
            save_file(
                original_name="test.txt",
                mime_type="text/plain",
                data_url_content=data_url,
                size_bytes=len(raw),
                user_id="user-1",
            )
        )
        assert result is None

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_save_file_sanitizes_filename(self, mock_settings, mock_factory, run):
        """Issue 9: Filenames with brackets/control chars are sanitized."""
        mock_settings.POSTGRES_ENABLED = True

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        raw = b"content"
        data_url = f"data:text/plain;base64,{base64.b64encode(raw).decode()}"

        run(
            save_file(
                original_name="[malicious\x00].txt",
                mime_type="text/plain",
                data_url_content=data_url,
                size_bytes=len(raw),
                user_id="user-1",
            )
        )

        added_obj = mock_session.add.call_args[0][0]
        assert "[" not in added_obj.original_name
        assert "]" not in added_obj.original_name
        assert "\x00" not in added_obj.original_name


class TestGetFileContent:
    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_returns_text_content(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True

        mock_session = _make_db_session(
            _make_upload(b"hello world", "text/plain", "readme.txt")
        )
        mock_factory.return_value = MagicMock(return_value=mock_session)

        result = run(get_file_content("file-123", user_id="user-1"))
        assert result == "hello world"

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_file_not_found_raises(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True

        mock_session = _make_db_session(None)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with pytest.raises(FileNotFoundError, match="No file found"):
            run(get_file_content("nonexistent", user_id="user-1"))

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_wrong_user_returns_not_found(self, mock_settings, mock_factory, run):
        """Issue 1: A different user_id should produce the same not-found error."""
        mock_settings.POSTGRES_ENABLED = True

        # DB returns None because user_id doesn't match (the WHERE clause filters it)
        mock_session = _make_db_session(None)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with pytest.raises(FileNotFoundError, match="No file found"):
            run(get_file_content("file-123", user_id="other-user"))

    @patch("BE.config.settings")
    def test_postgres_disabled_raises(self, mock_settings, run):
        mock_settings.POSTGRES_ENABLED = False

        with pytest.raises(RuntimeError, match="PostgreSQL is disabled"):
            run(get_file_content("any-id", user_id="user-1"))

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_binary_file_raises_value_error(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True

        mock_session = _make_db_session(
            _make_upload(bytes(range(256)), "application/octet-stream", "data.bin")
        )
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with pytest.raises(ValueError, match="binary"):
            run(get_file_content("bin-file", user_id="user-1"))

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_non_utf8_text_mime_raises_value_error(
        self, mock_settings, mock_factory, run
    ):
        """Issue 5: Non-UTF-8 content with a text MIME type raises ValueError."""
        mock_settings.POSTGRES_ENABLED = True

        # Latin-1 encoded content that's not valid UTF-8
        latin1_bytes = "caf\xe9".encode("latin-1")

        mock_session = _make_db_session(
            _make_upload(latin1_bytes, "text/plain", "cafe.txt")
        )
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with pytest.raises(ValueError, match="not valid UTF-8"):
            run(get_file_content("latin-file", user_id="user-1"))

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_non_utf8_text_extension_raises_value_error(
        self, mock_settings, mock_factory, run
    ):
        """Issue 5: Non-UTF-8 content with a text extension raises ValueError."""
        mock_settings.POSTGRES_ENABLED = True

        latin1_bytes = "caf\xe9".encode("latin-1")

        mock_session = _make_db_session(
            _make_upload(latin1_bytes, "application/octet-stream", "script.py")
        )
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with pytest.raises(ValueError, match="not valid UTF-8"):
            run(get_file_content("py-file", user_id="user-1"))

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_text_extension_detection(self, mock_settings, mock_factory, run):
        """Text extension files with application/octet-stream MIME are decoded."""
        mock_settings.POSTGRES_ENABLED = True

        mock_session = _make_db_session(
            _make_upload(b"print('hello')", "application/octet-stream", "script.py")
        )
        mock_factory.return_value = MagicMock(return_value=mock_session)

        result = run(get_file_content("py-file", user_id="user-1"))
        assert result == "print('hello')"

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_pdf_extraction_success(self, mock_settings, mock_factory, run):
        """Issue 6: PDF extraction returns text."""
        mock_settings.POSTGRES_ENABLED = True

        mock_session = _make_db_session(
            _make_upload(b"dummy-pdf", "application/pdf", "report.pdf")
        )
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with patch("BE.file_store._extract_pdf_text", return_value="PDF page text"):
            result = run(get_file_content("pdf-file", user_id="user-1"))
            assert result == "PDF page text"

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_pdf_extraction_failure_raises_value_error(
        self, mock_settings, mock_factory, run
    ):
        """Issue 6: Malformed PDF raises ValueError instead of crashing."""
        mock_settings.POSTGRES_ENABLED = True

        mock_session = _make_db_session(
            _make_upload(b"not-a-pdf", "application/pdf", "bad.pdf")
        )
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with patch(
            "BE.file_store._extract_pdf_text",
            side_effect=RuntimeError("cannot open broken PDF"),
        ):
            with pytest.raises(ValueError, match="Failed to extract text from PDF"):
                run(get_file_content("bad-pdf", user_id="user-1"))

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_oversized_file_raises_value_error(self, mock_settings, mock_factory, run):
        """File exceeding MAX_READABLE_SIZE raises ValueError."""
        mock_settings.POSTGRES_ENABLED = True

        from BE.file_store import MAX_READABLE_SIZE

        oversized = b"x" * (MAX_READABLE_SIZE + 1)
        mock_session = _make_db_session(
            _make_upload(oversized, "text/plain", "huge.txt")
        )
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with pytest.raises(ValueError, match="too large"):
            run(get_file_content("huge-file", user_id="user-1"))


class TestExtractPdfPages:
    def test_returns_page_text_with_1based_numbers(self):
        """Each page gets a 1-based page number."""
        import fitz

        doc = fitz.open()
        page1 = doc.new_page()
        page1.insert_text((72, 72), "Page one content")
        page2 = doc.new_page()
        page2.insert_text((72, 72), "Page two content")
        raw = doc.tobytes()
        doc.close()

        pages = _extract_pdf_pages(raw)
        assert len(pages) == 2
        assert pages[0].page_number == 1
        assert "Page one content" in pages[0].text
        assert pages[1].page_number == 2
        assert "Page two content" in pages[1].text

    def test_skips_blank_pages(self):
        """Blank pages are not included in the output."""
        import fitz

        doc = fitz.open()
        doc.new_page()  # blank page
        page2 = doc.new_page()
        page2.insert_text((72, 72), "Non-blank page")
        doc.new_page()  # another blank page
        raw = doc.tobytes()
        doc.close()

        pages = _extract_pdf_pages(raw)
        assert len(pages) == 1
        assert pages[0].page_number == 2
        assert "Non-blank page" in pages[0].text

    def test_returns_page_text_instances(self):
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Hello")
        raw = doc.tobytes()
        doc.close()

        pages = _extract_pdf_pages(raw)
        assert len(pages) == 1
        assert isinstance(pages[0], PageText)


class TestFetchUpload:
    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_returns_upload_row(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True
        upload_obj = _make_upload(b"content", "text/plain", "test.txt")
        mock_session = _make_db_session(upload_obj)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        result = run(_fetch_upload("file-1", "user-1"))
        assert result is upload_obj

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_not_found_raises(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True
        mock_session = _make_db_session(None)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with pytest.raises(FileNotFoundError, match="No file found"):
            run(_fetch_upload("nonexistent", "user-1"))

    @patch("BE.config.settings")
    def test_postgres_disabled_raises(self, mock_settings, run):
        mock_settings.POSTGRES_ENABLED = False

        with pytest.raises(RuntimeError, match="PostgreSQL is disabled"):
            run(_fetch_upload("any-id", "user-1"))


class TestGetFilePages:
    @patch("BE.file_store._fetch_upload")
    def test_returns_pages_for_pdf(self, mock_fetch, run):
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "PDF content here")
        raw = doc.tobytes()
        doc.close()

        mock_fetch.return_value = _make_upload(raw, "application/pdf", "report.pdf")

        pages = run(get_file_pages("file-1", "user-1"))
        assert pages is not None
        assert len(pages) >= 1
        assert isinstance(pages[0], PageText)
        assert pages[0].page_number == 1
        assert "PDF content here" in pages[0].text

    @patch("BE.file_store._fetch_upload")
    def test_returns_none_for_text_file(self, mock_fetch, run):
        mock_fetch.return_value = _make_upload(b"text", "text/plain", "readme.txt")

        result = run(get_file_pages("file-1", "user-1"))
        assert result is None

    @patch("BE.file_store._fetch_upload")
    def test_returns_none_for_non_pdf_mime(self, mock_fetch, run):
        mock_fetch.return_value = _make_upload(b"data", "application/json", "data.json")

        result = run(get_file_pages("file-1", "user-1"))
        assert result is None

    @patch("BE.file_store._fetch_upload")
    def test_pdf_by_extension(self, mock_fetch, run):
        """Files with .pdf extension but generic MIME type are treated as PDFs."""
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Extension-detected PDF")
        raw = doc.tobytes()
        doc.close()

        mock_fetch.return_value = _make_upload(
            raw, "application/octet-stream", "doc.pdf"
        )

        pages = run(get_file_pages("file-1", "user-1"))
        assert pages is not None
        assert len(pages) >= 1

    @patch("BE.file_store._fetch_upload")
    def test_malformed_pdf_raises_value_error(self, mock_fetch, run):
        mock_fetch.return_value = _make_upload(
            b"not-a-pdf", "application/pdf", "bad.pdf"
        )

        with pytest.raises(ValueError, match="Failed to extract text from PDF"):
            run(get_file_pages("file-1", "user-1"))
