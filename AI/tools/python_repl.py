"""Python REPL tool for the agent.

WARNING: This tool executes arbitrary Python code with full system access.
There is no sandboxing, resource limiting, or network isolation.
Only enable (GENERAL_AGENT_PYTHON_REPL_TOOL=true) in trusted environments.
"""

from langchain_core.tools import tool
from langchain_experimental.tools import PythonREPLTool
from langgraph.config import get_stream_writer

from BE.logger import setup_logger

logger = setup_logger(__name__)

_repl: PythonREPLTool | None = None


def _get_repl() -> PythonREPLTool:
    global _repl
    if _repl is None:
        _repl = PythonREPLTool()
    return _repl


@tool
def python_repl_tool(code: str) -> str:
    """Execute Python code in a REPL. Use this to run Python snippets and return their output."""
    logger.info("python_repl_tool invoked (code=%s)", code[:100])
    writer = get_stream_writer()
    writer("Executing Python code")
    try:
        result = _get_repl().run(code)
        logger.info("python_repl_tool complete (result_length=%d)", len(result))
        writer("Execution complete")
        return result
    except Exception:
        logger.error("python_repl_tool failed", exc_info=True)
        raise
