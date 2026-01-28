from agent import Agent
from prompts.main_prompt import SYSTEM_PROMPT

agent = Agent(system_prompt=SYSTEM_PROMPT)

def main():
    for chunk in agent.stream("What is the current date and time?"):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
