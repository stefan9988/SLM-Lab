"""Tests for BE.logger module."""

import logging

from BE.logger import ColoredFormatter, setup_logger


class TestColoredFormatter:
    def test_warning_contains_yellow_ansi(self):
        fmt = ColoredFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord("test", logging.WARNING, "", 0, "msg", (), None)
        output = fmt.format(record)
        assert "\033[33m" in output

    def test_info_contains_green_ansi(self):
        fmt = ColoredFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        output = fmt.format(record)
        assert "\033[32m" in output


class TestSetupLogger:
    def test_returns_logger_with_stream_handler_and_colored_formatter(self):
        logger = setup_logger("test_logger_unique_1")
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        assert isinstance(logger.handlers[0].formatter, ColoredFormatter)

    def test_no_duplicate_handlers(self):
        name = "test_logger_unique_2"
        logger1 = setup_logger(name)
        logger2 = setup_logger(name)
        assert logger1 is logger2
        assert len(logger1.handlers) == 1

    def test_explicit_level_respected(self):
        logger = setup_logger("test_logger_unique_3", level="DEBUG")
        assert logger.level == logging.DEBUG
