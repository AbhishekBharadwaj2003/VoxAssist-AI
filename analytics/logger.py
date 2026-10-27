
import csv
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ANALYTICS_FILE = PROJECT_ROOT / "data" / "analytics.csv"

FIELDNAMES = [
    "timestamp",
    "question",
    "channel",
    "response_time_seconds",
    "topic",
    "escalated",
]


def classify_topic(question: str) -> str:
    """Classify a customer question using simple keyword matching."""
    text = question.lower()

    topics = {
        "Shipping": [
            "shipping", "delivery", "deliver", "dispatch", "express",
            "tracking", "track my order",
        ],
        "Returns": [
            "return", "exchange", "send back",
        ],
        "Refunds": [
            "refund", "money back", "reimbursement",
        ],
        "Payments": [
            "payment", "paid", "upi", "transaction", "billing",
        ],
        "Cancellation": [
            "cancel", "cancellation",
        ],
        "Damaged or Incorrect Items": [
            "damaged", "broken", "defective", "wrong item", "incorrect item",
        ],
    }

    for topic, keywords in topics.items():
        if any(keyword in text for keyword in keywords):
            return topic

    return "General"


def detect_escalation(question: str, answer: str) -> bool:
    """
    Flag interactions that may need human support.
    This is a heuristic, not a confirmed escalation.
    """
    text = f"{question} {answer}".lower()

    escalation_keywords = [
        "speak to a human",
        "human support",
        "human agent",
        "contact our support team",
        "escalate this",
        "disputed payment",
    ]

    return any(keyword in text for keyword in escalation_keywords)


def log_interaction(
    question: str,
    channel: str,
    response_time_seconds: float,
    topic: str | None = None,
    escalated: bool | None = None,
) -> None:
    """Append one customer interaction to the analytics CSV."""
    ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if topic is None:
        topic = classify_topic(question)

    if escalated is None:
        # The caller should provide the actual detection result when available.
        escalated = False

    file_exists = (
        ANALYTICS_FILE.exists()
        and ANALYTICS_FILE.stat().st_size > 0
    )

    with ANALYTICS_FILE.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "question": question.strip(),
                "channel": channel,
                "response_time_seconds": round(
                    max(0.0, response_time_seconds), 3
                ),
                "topic": topic,
                "escalated": bool(escalated),
            }
        )
