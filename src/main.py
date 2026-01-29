from agents import init_ollama_agent
from logger import setup_logger
from tools import get_current_date_and_time, brave_search_tool, python_repl_tool

logger = setup_logger(__name__)

agent = init_ollama_agent(tools=[get_current_date_and_time, brave_search_tool, python_repl_tool])

def main():
    logger.info("Starting conversation")
    token_count = 0
    try:
        for event in agent.stream("Can you run a Python code to calculate the factorial of 5?"):
            if event["type"] == "token":
                print(event["content"], end="", flush=True)
                token_count += 1
            elif event["type"] == "status":
                print(f"\n[{event['content']}]", flush=True)
        print()
        logger.info("Conversation complete (tokens=%d)", token_count)
    except KeyboardInterrupt:
        print()
        logger.info("Conversation interrupted by user")
    except Exception:
        logger.error("Conversation failed", exc_info=True)


if __name__ == "__main__":
    main()
