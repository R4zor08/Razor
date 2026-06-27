"""Razor AI — entry point."""

import config
from system.executor import Executor
from utils.logger import get_logger

logger = get_logger(__name__)


def run_cli() -> None:
    """Interactive CLI for deterministic command execution."""
    executor = Executor()
    print(f"{config.APP_NAME} v{config.APP_VERSION} — CLI mode")
    print("Type a command or 'help' for available commands. Type 'exit' to quit.\n")

    while True:
        try:
            command = input("razor> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not command:
            continue

        result = executor.execute(command)
        if result == "__EXIT__":
            print("Goodbye.")
            break

        print(result)
        print()


def main() -> None:
    """Bootstrap and run the assistant."""
    logger.info("Starting %s v%s", config.APP_NAME, config.APP_VERSION)
    run_cli()


if __name__ == "__main__":
    main()
