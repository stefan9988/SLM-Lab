from agents import init_ollama_agent
from tools import get_current_date_and_time

agent = init_ollama_agent(tools=[get_current_date_and_time])

def main():
    for chunk in agent.stream("What is the capital of France?"):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
