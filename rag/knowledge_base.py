
import re
from pathlib import Path

import chromadb


# --------------------------------------------------
# Paths and configuration
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

FAQ_FILE = PROJECT_ROOT / "data" / "company_faqs.txt"
DB_DIRECTORY = PROJECT_ROOT / "data" / "chroma_db"

COLLECTION_NAME = "shopease_support"


# --------------------------------------------------
# Initialize persistent ChromaDB
# --------------------------------------------------
def get_collection():
    """Create or retrieve the persistent ChromaDB collection."""

    DB_DIRECTORY.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(DB_DIRECTORY)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "ShopEase customer support knowledge base"},
    )

    return collection


# --------------------------------------------------
# Load and split the FAQ document
# --------------------------------------------------
def load_documents():
    """Read the FAQ file and split it into policy sections."""

    if not FAQ_FILE.exists():
        raise FileNotFoundError(
            f"Knowledge base file not found: {FAQ_FILE}"
        )

    content = FAQ_FILE.read_text(encoding="utf-8").strip()

    if not content:
        raise ValueError("The knowledge base file is empty.")

    # Split on second-level Markdown headings, such as ## Returns.
    sections = re.split(r"(?m)(?=^##\s+)", content)

    documents = []
    ids = []
    metadatas = []

    for index, section in enumerate(sections):
        section = section.strip()

        if not section:
            continue

        # Skip the introductory text before the first policy section.
        if not section.startswith("## "):
            continue

        heading = section.splitlines()[0].replace("## ", "", 1).strip()

        documents.append(section)
        ids.append(f"policy_{index}")
        metadatas.append(
            {
                "category": heading,
                "source": FAQ_FILE.name,
            }
        )

    if not documents:
        raise ValueError(
            "No policy sections found. Check that the FAQ uses ## headings."
        )

    return documents, ids, metadatas


# --------------------------------------------------
# Build or refresh the knowledge base
# --------------------------------------------------
def build_knowledge_base():
    """Load policy sections and save their embeddings in ChromaDB."""

    documents, ids, metadatas = load_documents()
    collection = get_collection()

    # Replace old records so edits to the FAQ file are reflected.
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    return len(documents)


# --------------------------------------------------
# Retrieve relevant policy sections
# --------------------------------------------------
def retrieve_context(question: str, top_k: int = 3) -> str:
    """Find policy sections relevant to a customer question."""

    if not question or not question.strip():
        return ""

    collection = get_collection()

    if collection.count() == 0:
        build_knowledge_base()

    results = collection.query(
        query_texts=[question.strip()],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not documents:
        return ""

    context_parts = []

    for document, metadata, distance in zip(
        documents, metadatas, distances
    ):
        category = metadata.get("category", "General policy")

        context_parts.append(
            f"Category: {category}\n"
            f"Relevance distance: {distance:.4f}\n"
            f"{document}"
        )

    return "\n\n---\n\n".join(context_parts)


# --------------------------------------------------
# Run this file directly to build the knowledge base
# --------------------------------------------------
if __name__ == "__main__":
    try:
        count = build_knowledge_base()

        print("Knowledge base built successfully!")
        print(f"Policy sections indexed: {count}")
        print(f"Database location: {DB_DIRECTORY}")

    except Exception as error:
        print(f"Failed to build knowledge base: {error}")
        raise
