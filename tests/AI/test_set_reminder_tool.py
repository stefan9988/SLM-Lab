"""Tests for AI.tools.set_reminder."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestSetReminderTool:
    def _invoke(self, task: str, remind_at: str):
        from AI.tools.set_reminder import set_reminder_tool

        return asyncio.run(set_reminder_tool.coroutine(task=task, remind_at=remind_at))

    @patch("AI.tools.set_reminder.get_stream_writer")
    @patch("BE.reminder_store.insert_reminder", new_callable=AsyncMock)
    def test_valid_future_datetime_returns_confirmation(self, mock_insert, mock_writer):
        mock_writer.return_value = MagicMock()
        mock_insert.return_value = "abc-123"
        future = datetime.now() + timedelta(hours=1)
        remind_at = future.strftime("%Y-%m-%d %H:%M:%S")

        result = self._invoke("Clean the kitchen", remind_at)

        assert "Clean the kitchen" in result
        assert remind_at in result
        mock_insert.assert_called_once()

    @patch("AI.tools.set_reminder.get_stream_writer")
    def test_past_datetime_returns_error(self, mock_writer):
        mock_writer.return_value = MagicMock()
        past = datetime.now() - timedelta(minutes=5)
        remind_at = past.strftime("%Y-%m-%d %H:%M:%S")

        result = self._invoke("Do something", remind_at)

        assert result.startswith("Error:")
        assert "future" in result

    @patch("AI.tools.set_reminder.get_stream_writer")
    def test_invalid_format_returns_error(self, mock_writer):
        mock_writer.return_value = MagicMock()

        result = self._invoke("Do something", "01/01/2099 14:00")

        assert result.startswith("Error:")
        assert "YYYY-MM-DD HH:MM:SS" in result

    @patch("AI.tools.set_reminder.get_stream_writer")
    @patch("BE.reminder_store.insert_reminder", new_callable=AsyncMock)
    def test_db_error_returns_error_string(self, mock_insert, mock_writer):
        mock_writer.return_value = MagicMock()
        mock_insert.side_effect = RuntimeError("DB connection lost")
        future = datetime.now() + timedelta(hours=1)
        remind_at = future.strftime("%Y-%m-%d %H:%M:%S")

        result = self._invoke("Take pills", remind_at)

        assert result.startswith("Error:")
        assert "DB connection lost" in result
