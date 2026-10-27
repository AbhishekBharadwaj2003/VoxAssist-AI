
import os

import streamlit as st
from groq import Groq

from rag.knowledge_base import retrieve_context

MODEL_NAME = "openai/gpt-oss-20b"


@st.cache_resource
def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. Please check your .env file."
        )

    return Groq(api_key=api_key)


def get_llm_response(
    question: str,
    conversation_history: list | None = None,
) -> str:
    if not question or not question.strip():
        return "Please enter a question so I can help you."

    context = retrieve_context(question)

    system_prompt = f"""
You are VoxAssist AI, a professional customer support agent
for the fictional e-commerce company ShopEase.

Rules:
1. Use retrieved policies as the source of truth for company policies.
2. Use conversation history to understand follow-up questions.
3. Never invent order details, tracking information, refund statuses,
   or company policies.
4. If the available policies do not answer a question, explain that
   you cannot confirm the information and offer human support.
5. Never claim an action was completed unless a verified tool confirms it.
6. Be concise, friendly, and professional.

Retrieved ShopEase policies:
{context if context else "No relevant policies were retrieved."}

If the retrieved policies do not contain the requested information,
do not present guesses as company policy.
"""

    messages = [{"role": "system", "content": system_prompt}]

    # Include recent conversation messages for context.
    if conversation_history:
        for message in conversation_history[-10:]:
            role = message.get("role")
            content = message.get("content")

            if role in ("user", "assistant") and isinstance(content, str):
                messages.append({
                    "role": role,
                    "content": content,
                })

    messages.append({
        "role": "user",
        "content": question.strip(),
    })

    client = get_groq_client()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
    )

    return response.choices[0].message.content or (
        "I'm sorry, but I couldn't generate a response. Please try again."
    )
