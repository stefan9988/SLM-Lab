from typing import Iterator

from langchain_ollama import ChatOllama

from config import settings


class Agent:
    """Agent class that wraps an LLM with streaming support."""

    def __init__(
        self,
        model_name: str = settings.MODEL_NAME,
        base_url: str = settings.OLLAMA_BASE_URL,
    ):
        self.model_name = model_name
        self.base_url = base_url
        self._llm = ChatOllama(model=model_name, base_url=base_url)

    def stream(self, prompt: str) -> Iterator[str]:
        """Stream response chunks for the given prompt."""
        for chunk in self._llm.stream(prompt):
            yield chunk.content

    def invoke(self, prompt: str) -> str:
        """Get a complete response for the given prompt."""
        response = self._llm.invoke(prompt)
        return response.content
