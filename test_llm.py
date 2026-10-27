from agent.llm import get_llm_response


def main():
    question = (
        "A customer says their order has not arrived. "
        "How would you respond professionally?"
    )

    print("\nConnecting to VoxAssist AI...\n")

    try:
        answer = get_llm_response(question)

        print("Customer:", question)
        print("\nVoxAssist AI:", answer)

    except Exception as error:
        print("\nSomething went wrong.")
        print("Error:", error)


if __name__ == "__main__":
    main()