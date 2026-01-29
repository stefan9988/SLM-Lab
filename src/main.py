from agents import init_ollama_agent
from tools import get_current_date_and_time, brave_search_tool

agent = init_ollama_agent(tools=[get_current_date_and_time, brave_search_tool])

def main():
    for chunk in agent.stream("What is current bitcoin price?"):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
