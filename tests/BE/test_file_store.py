"""Tests for BE.file_store — async file persistence service."""

import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from BE.file_store import _decode_data_url, get_file_content, save_file


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def run(event_loop):
    return event_loop.run_until_complete


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
        data_url = f"data:application/octet-stream;base64,{base64.b64encode(raw).decode()}"
        assert _decode_data_url(data_url) == raw


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

        result = run(save_file(
            original_name="data.csv",
            mime_type="text/csv",
            data_url_content=data_url,
            size_bytes=len(raw),
            user_id="user-1",
            session_id="sess-1",
        ))

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_save_file_stores_decoded_bytes(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        raw = b"file content here"
        data_url = f"data:text/plain;base64,{base64.b64encode(raw).decode()}"

        run(save_file(
            original_name="test.txt",
            mime_type="text/plain",
            data_url_content=data_url,
            size_bytes=len(raw),
            user_id="user-1",
        ))

        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.content == raw
        assert added_obj.original_name == "test.txt"
        assert added_obj.mime_type == "text/plain"

    @patch("BE.config.settings")
    def test_save_file_empty_content_returns_none(self, mock_settings, run):
        mock_settings.POSTGRES_ENABLED = True

        result = run(save_file(
            original_name="empty.txt",
            mime_type="text/plain",
            data_url_content="",
            size_bytes=0,
            user_id="user-1",
        ))
        assert result is None

    @patch("BE.config.settings")
    def test_save_file_invalid_data_url_returns_none(self, mock_settings, run):
        mock_settings.POSTGRES_ENABLED = True

        result = run(save_file(
            original_name="bad.txt",
            mime_type="text/plain",
            data_url_content="data:text/plain;base64,!!!not-valid-b64!!!",
            size_bytes=10,
            user_id="user-1",
        ))
        assert result is None

    @patch("BE.config.settings")
    def test_save_file_postgres_disabled_returns_none(self, mock_settings, run):
        mock_settings.POSTGRES_ENABLED = False

        raw = b"content"
        data_url = f"data:text/plain;base64,{base64.b64encode(raw).decode()}"

        result = run(save_file(
            original_name="test.txt",
            mime_type="text/plain",
            data_url_content=data_url,
            size_bytes=len(raw),
            user_id="user-1",
        ))
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

        result = run(save_file(
            original_name="test.txt",
            mime_type="text/plain",
            data_url_content=data_url,
            size_bytes=len(raw),
            user_id="user-1",
        ))
        assert result is None


class TestGetFileContent:
    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_returns_text_content(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True

        upload = MagicMock()
        upload.content = b"hello world"
        upload.mime_type = "text/plain"
        upload.original_name = "readme.txt"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = upload

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        result = run(get_file_content("file-123"))
        assert result == "hello world"

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_file_not_found_raises(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with pytest.raises(FileNotFoundError, match="No file found"):
            run(get_file_content("nonexistent"))

    @patch("BE.config.settings")
    def test_postgres_disabled_raises(self, mock_settings, run):
        mock_settings.POSTGRES_ENABLED = False

        with pytest.raises(RuntimeError, match="PostgreSQL is disabled"):
            run(get_file_content("any-id"))

    @patch("BE.database.get_session_factory")
    @patch("BE.config.settings")
    def test_binary_file_raises_value_error(self, mock_settings, mock_factory, run):
        mock_settings.POSTGRES_ENABLED = True

        upload = MagicMock()
        upload.content = bytes(range(256))  # non-UTF-8 binary
        upload.mime_type = "application/octet-stream"
        upload.original_name = "data.bin"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = upload

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value = MagicMock(return_value=mock_session)

        with pytest.raises(ValueError, match="binary"):
            run(get_file_content("bin-file"))
