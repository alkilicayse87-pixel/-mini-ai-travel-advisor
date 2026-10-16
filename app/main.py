from app import advisor


def run() -> None:
    print("AI Travel Advisor (type 'exit' or 'quit' to leave)")
    previous_id = None
    first = "Hi!"
    while True:
        text = first or input("\nYou: ").strip()
        first = None
        if text.lower() in {"exit", "quit"}:
            break
        if not text:
            continue
        answer, previous_id = advisor.chat(text, previous_id)
        print(f"\nAdvisor: {answer}")


if __name__ == "__main__":
    run()
