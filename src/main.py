from agents import OllamaAgent
from prompts.main_prompt import SYSTEM_PROMPT
from tools.get_current_date_and_time import get_current_date_and_time

agent = OllamaAgent(system_prompt=SYSTEM_PROMPT, tools=[get_current_date_and_time])

def main():
    for chunk in agent.stream("What is the current date and time?"):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
