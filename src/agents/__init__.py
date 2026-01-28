"""Agents package providing abstract base class and implementations."""

from .base import BaseAgent
from .ollama_agent import OllamaAgent

__all__ = ["BaseAgent", "OllamaAgent"]
