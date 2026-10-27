
import time

import streamlit as st

from agent.llm import get_llm_response
from voice.speech_to_text import transcribe_audio
from voice.text_to_speech import generate_speech
from analytics.logger import log_interaction, detect_escalation


# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="VoxAssist AI",
    page_icon="🎧",
    layout="centered",
)


# --------------------------------------------------
# Header
# --------------------------------------------------
st.title("🎧 VoxAssist AI")
st.caption("Your AI-powered customer support assistant")

st.markdown(
    """
    Welcome to VoxAssist! 👋

    Ask questions by typing or recording your voice.
    VoxAssist will respond with text and speech.
    """
)


# --------------------------------------------------
# Session state
# --------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! I'm VoxAssist. How can I help you today?",
            "audio": None,
        }
    ]

if "voice_transcript" not in st.session_state:
    st.session_state.voice_transcript = ""


# --------------------------------------------------
# Conversation memory helper
# --------------------------------------------------
def get_conversation_history():
    """Return the 10 most recent text messages."""

    history = []

    for message in st.session_state.messages:
        role = message.get("role")
        content = message.get("content", "")

        if role not in ("user", "assistant"):
            continue

        if not isinstance(content, str) or not content.strip():
            continue

        if (
            role == "assistant"
            and content == "Hi! I'm VoxAssist. How can I help you today?"
        ):
            continue

        history.append(
            {
                "role": role,
                "content": content,
            }
        )

    return history[-10:]


# --------------------------------------------------
# Analytics helper
# --------------------------------------------------
def record_analytics(question, answer, channel, response_time):
    """Log an interaction without interrupting customer support."""

    try:
        log_interaction(
            question=question,
            channel=channel,
            response_time_seconds=response_time,
            escalated=detect_escalation(question, answer),
        )
    except Exception as error:
        # Analytics failures should not stop the chatbot.
        print(f"Analytics logging failed: {error}")


# --------------------------------------------------
# Text-to-speech helper
# --------------------------------------------------
def display_answer_audio(answer: str):
    """Generate and display speech for an AI response."""

    try:
        with st.spinner("Generating voice response..."):
            audio_bytes = generate_speech(answer)

        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
            return audio_bytes

        st.warning("Voice playback is unavailable for this response.")
        return None

    except Exception as error:
        st.warning(
            "Your text response is available, but voice playback failed. "
            f"Details: {error}"
        )
        return None


# --------------------------------------------------
# Voice input
# --------------------------------------------------
st.subheader("🎙️ Ask by voice")

audio_file = st.audio_input("Record your question")

if audio_file is not None:
    if st.button("Transcribe recording", key="transcribe_button"):
        with st.spinner("Converting your speech to text..."):
            try:
                transcript = transcribe_audio(audio_file)

                if transcript:
                    st.session_state.voice_transcript = transcript
                    st.success("Transcription complete!")
                else:
                    st.session_state.voice_transcript = ""
                    st.warning("No speech detected. Please record again.")

            except Exception as error:
                st.error(f"Transcription failed: {error}")


# --------------------------------------------------
# Submit voice question
# --------------------------------------------------
if st.session_state.voice_transcript:
    st.write("**Recognized speech:**")
    st.info(st.session_state.voice_transcript)

    if st.button("Send voice question to VoxAssist", key="send_voice"):
        question = st.session_state.voice_transcript.strip()

        if question:
            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": question,
                    "audio": None,
                }
            )

            st.session_state.voice_transcript = ""
            st.session_state.pending_question = question
            st.rerun()


st.divider()


# --------------------------------------------------
# Display chat history
# --------------------------------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant" and message.get("audio"):
            st.audio(message["audio"], format="audio/wav")


# --------------------------------------------------
# Process voice questions
# --------------------------------------------------
if "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")

    # The voice question is already stored in session state.
    # Exclude it from history to avoid sending it twice.
    history = get_conversation_history()

    if history and history[-1]["role"] == "user":
        history = history[:-1]

    with st.chat_message("assistant"):
        with st.spinner("VoxAssist is thinking..."):
            start_time = time.perf_counter()

            try:
                answer = get_llm_response(
                    question,
                    conversation_history=history,
                )
            except Exception:
                answer = (
                    "I'm sorry, I'm having trouble connecting right now. "
                    "Please try again in a moment."
                )

            response_time = time.perf_counter() - start_time

        # Record the AI response generation time, excluding TTS.
        record_analytics(
            question=question,
            answer=answer,
            channel="voice",
            response_time=response_time,
        )

        st.markdown(answer)
        audio_bytes = display_answer_audio(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "audio": audio_bytes,
        }
    )


# --------------------------------------------------
# Text chat
# --------------------------------------------------
if prompt := st.chat_input("Type your question here..."):

    # Capture previous messages before appending the new question.
    history = get_conversation_history()

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
            "audio": None,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("VoxAssist is thinking..."):
            start_time = time.perf_counter()

            try:
                answer = get_llm_response(
                    prompt,
                    conversation_history=history,
                )
            except Exception:
                answer = (
                    "I'm sorry, I'm having trouble connecting right now. "
                    "Please try again in a moment."
                )

            response_time = time.perf_counter() - start_time

        # Record the AI response generation time, excluding TTS.
        record_analytics(
            question=prompt,
            answer=answer,
            channel="text",
            response_time=response_time,
        )

        st.markdown(answer)
        audio_bytes = display_answer_audio(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "audio": audio_bytes,
        }
    )


# --------------------------------------------------
# Sidebar
# --------------------------------------------------
with st.sidebar:
    st.header("About VoxAssist")

    st.write(
        "An AI customer support assistant with text chat, voice input, "
        "speech transcription, conversational memory, RAG-based policy "
        "retrieval, spoken AI responses, and interaction analytics."
    )

    st.divider()

    if st.button("Clear conversation"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi! I'm VoxAssist. How can I help you today?",
                "audio": None,
            }
        ]

        st.session_state.voice_transcript = ""
        st.session_state.pop("pending_question", None)

        st.rerun()

    st.caption(
        "Built with Python, Streamlit, Groq, Whisper, ChromaDB and Piper TTS"
    )
