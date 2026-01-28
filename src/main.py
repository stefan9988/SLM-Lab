from langchain_ollama import ChatOllama

def main():
    llm = ChatOllama(model="llama3.1:8b")
    response = llm.invoke("Hello, how are you?")
    print(response.content)

if __name__ == "__main__":
    main()
