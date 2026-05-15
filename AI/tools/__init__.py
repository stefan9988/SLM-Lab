from AI.tools.get_current_date_and_time import get_current_date_and_time
from AI.tools.brave_search import brave_search_tool
from AI.tools.python_repl import python_repl_tool
from AI.tools.ollama_web import ollama_web_search_tool, ollama_web_fetch_tool
from AI.tools.read_file_content import read_file_content_tool
from AI.tools.search_chunks import search_chunks_tool
from AI.tools.delegate_to_agent import delegate_to_agent_tool
from AI.tools.web_page_content import web_page_content_tool
from AI.tools.send_telegram_message import send_telegram_message_tool

__all__ = [
    "get_current_date_and_time",
    "brave_search_tool",
    "python_repl_tool",
    "ollama_web_search_tool",
    "ollama_web_fetch_tool",
    "read_file_content_tool",
    "search_chunks_tool",
    "delegate_to_agent_tool",
    "web_page_content_tool",
    "send_telegram_message_tool",
    "get_enabled_tools",
    "get_document_agent_enabled_tools",
    "get_validation_agent_enabled_tools",
]

GENERAL_AGENT_TOOLS = [
    ("GENERAL_AGENT_DATE_TIME_TOOL", get_current_date_and_time),
    ("GENERAL_AGENT_BRAVE_SEARCH_TOOL", brave_search_tool),
    ("GENERAL_AGENT_PYTHON_REPL_TOOL", python_repl_tool),
    ("GENERAL_AGENT_OLLAMA_WEB_SEARCH_TOOL", ollama_web_search_tool),
    ("GENERAL_AGENT_OLLAMA_WEB_FETCH_TOOL", ollama_web_fetch_tool),
    ("GENERAL_AGENT_READ_FILE_CONTENT_TOOL", read_file_content_tool),
    ("GENERAL_AGENT_SEARCH_CHUNKS_TOOL", search_chunks_tool),
    ("GENERAL_AGENT_DELEGATE_TOOL", delegate_to_agent_tool),
    ("GENERAL_AGENT_WEB_PAGE_CONTENT_TOOL", web_page_content_tool),
    ("GENERAL_AGENT_SEND_TELEGRAM_MESSAGE_TOOL", send_telegram_message_tool),
]

DOCUMENT_AGENT_TOOLS = [
    ("DOCUMENT_AGENT_DATE_TIME_TOOL", get_current_date_and_time),
    ("DOCUMENT_AGENT_BRAVE_SEARCH_TOOL", brave_search_tool),
    ("DOCUMENT_AGENT_PYTHON_REPL_TOOL", python_repl_tool),
    ("DOCUMENT_AGENT_OLLAMA_WEB_SEARCH_TOOL", ollama_web_search_tool),
    ("DOCUMENT_AGENT_OLLAMA_WEB_FETCH_TOOL", ollama_web_fetch_tool),
    ("DOCUMENT_AGENT_READ_FILE_CONTENT_TOOL", read_file_content_tool),
    ("DOCUMENT_AGENT_SEARCH_CHUNKS_TOOL", search_chunks_tool),
    ("DOCUMENT_AGENT_DELEGATE_TOOL", delegate_to_agent_tool),
    ("DOCUMENT_AGENT_WEB_PAGE_CONTENT_TOOL", web_page_content_tool),
]


def get_enabled_tools(settings) -> list:
    """Return tools enabled for the general agent based on settings."""
    tools = []
    for setting_name, tool in GENERAL_AGENT_TOOLS:
        if getattr(settings, setting_name, False):
            tools.append(tool)
    return tools


def get_document_agent_enabled_tools(settings) -> list:
    """Return tools enabled for the document agent based on settings."""
    tools = []
    for setting_name, tool in DOCUMENT_AGENT_TOOLS:
        if getattr(settings, setting_name, False):
            tools.append(tool)
    return tools


VALIDATION_AGENT_TOOLS = [
    ("VALIDATION_AGENT_DATE_TIME_TOOL", get_current_date_and_time),
    ("VALIDATION_AGENT_BRAVE_SEARCH_TOOL", brave_search_tool),
    ("VALIDATION_AGENT_OLLAMA_WEB_SEARCH_TOOL", ollama_web_search_tool),
    ("VALIDATION_AGENT_OLLAMA_WEB_FETCH_TOOL", ollama_web_fetch_tool),
    ("VALIDATION_AGENT_WEB_PAGE_CONTENT_TOOL", web_page_content_tool),
]


def get_validation_agent_enabled_tools(settings) -> list:
    """Return tools enabled for the validation agent based on settings."""
    tools = []
    for setting_name, tool in VALIDATION_AGENT_TOOLS:
        if getattr(settings, setting_name, False):
            tools.append(tool)
    return tools
