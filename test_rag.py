
from rag.knowledge_base import retrieve_context

questions = [
    "How many days do I have to return a product?",
    "How long does a refund take?",
    "What should I do if my tracking information is unavailable?",
]

for question in questions:
    print("\n" + "=" * 60)
    print(f"QUESTION: {question}")
    print("=" * 60)

    context = retrieve_context(question)

    if context:
        print(context)
    else:
        print("No relevant policy information was retrieved.")
