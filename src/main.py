from langchain_ollama import ChatOllama

from config import settings


def main():
    llm = ChatOllama(model=settings.MODEL_NAME, base_url=settings.OLLAMA_BASE_URL)
    response = llm.invoke("Hello, how are you?")
    print(response.content)

if __name__ == "__main__":
    main()
