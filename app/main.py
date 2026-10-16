from app import advisor


def run() -> None:
    print("AI Travel Advisor (type 'exit' or 'quit' to leave)")
    previous_id = None
    first = "Hi!"
    total = None
    while True:
        text = first or input("\nYou: ").strip()
        first = None
        if text.lower() in {"exit", "quit"}:
            break
        if not text:
            continue
        answer, previous_id, _, total = advisor.chat(text, previous_id)
        print(f"\nAdvisor: {answer}")
        print(
            f"\n[tokens in/out: {total.input_tokens}/{total.output_tokens}"
            f" | est. cost: ${total.cost_usd:.4f}]"
        )


if __name__ == "__main__":
    run()
