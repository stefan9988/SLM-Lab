from agent import Agent


def main():
    agent = Agent()
    for chunk in agent.stream("Write paragraph about France."):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
