from agents import init_ollama_agent
from tools import get_current_date_and_time, brave_search_tool

agent = init_ollama_agent(tools=[get_current_date_and_time, brave_search_tool])

def main():
    for event in agent.stream("Write paragraphs about the future of AI."):
        if event["type"] == "token":
            print(event["content"], end="", flush=True)
        elif event["type"] == "status":
            print(f"\n[{event['content']}]", flush=True)
    print()


if __name__ == "__main__":
    main()
