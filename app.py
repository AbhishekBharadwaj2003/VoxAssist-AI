import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from agent.llm import get_llm_response
from voice.speech_to_text import transcribe_audio
from voice.text_to_speech import generate_speech
from analytics.logger import ANALYTICS_FILE, log_interaction, detect_escalation

st.set_page_config(
    page_title="VoxAssist AI",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- Styling -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { color-scheme: dark; }
.stApp { background: #0b1020; color: #e8edf7; font-family: 'DM Sans', sans-serif; }
[data-testid="stHeader"] { background: rgba(11,16,32,.92); }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -0.03em; }
h1 { color: #f4f7ff; }
[data-testid="stSidebar"] { background: #10172a; border-right: 1px solid #202b43; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
[data-testid="stMetric"] { background: linear-gradient(135deg,#151f36,#111a2e); border: 1px solid #273550; padding: 18px 20px; border-radius: 16px; }
[data-testid="stMetricLabel"] { color: #9baac4; }
[data-testid="stMetricValue"] { color: #f3f7ff; }
.stButton > button, .stDownloadButton > button { border-radius: 10px; border: 1px solid #344563; background: #17243c; color: #edf4ff; min-height: 2.6rem; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color: #66d9c3; color: #66d9c3; }
.stTextInput input, [data-testid="stChatInput"] textarea { background: #121b2e; color: #f4f7ff; border-color: #2b3955; border-radius: 12px; }
[data-testid="stChatMessage"] { background: #111a2d; border: 1px solid #202d46; border-radius: 16px; padding: 14px 16px; }
[data-testid="stFileUploader"] { background: #111a2d; border: 1px dashed #344563; border-radius: 14px; padding: 10px; }
hr { border-color: #26334c; }
.va-brand { display:flex; align-items:center; gap:12px; margin: 0 0 1.4rem; }
.va-logo { width:44px; height:44px; display:flex; align-items:center; justify-content:center; border-radius:14px; background:linear-gradient(135deg,#66d9c3,#6e8bff); color:#091321; font-size:24px; font-weight:700; }
.va-brand-name { font-family:'Space Grotesk',sans-serif; font-size:21px; font-weight:700; color:#f4f7ff; }
.va-muted { color:#9baac4; font-size:13px; }
.va-eyebrow { color:#66d9c3; font-weight:700; font-size:12px; letter-spacing:.14em; text-transform:uppercase; }
.va-hero { background:radial-gradient(circle at 85% 10%,rgba(102,217,195,.14),transparent 30%),linear-gradient(135deg,#17243c,#11182b); border:1px solid #2b3a55; padding:30px 32px; border-radius:22px; margin-bottom:24px; }
.va-pill { display:inline-block; padding:5px 10px; border-radius:999px; background:#173b3a; color:#77e6cf; font-size:12px; font-weight:700; }
.va-card { background:#111a2d; border:1px solid #25334d; border-radius:16px; padding:18px 20px; min-height:125px; }
.va-card-title { color:#9baac4; font-size:13px; margin-bottom:10px; }
.va-card-value { font-family:'Space Grotesk',sans-serif; color:#f4f7ff; font-size:24px; font-weight:700; }
.va-card-desc { color:#8f9fba; font-size:12px; margin-top:6px; }
</style>
""", unsafe_allow_html=True)

# ----------------------------- Session state -----------------------------
GREETING = "Hi! I'm VoxAssist. How can I help you today?"
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": GREETING, "audio": None}]
if "voice_transcript" not in st.session_state:
    st.session_state.voice_transcript = ""
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# ----------------------------- Helpers -----------------------------
def get_conversation_history():
    history = []
    for message in st.session_state.messages:
        role, text = message.get("role"), message.get("content", "")
        if role in ("user", "assistant") and isinstance(text, str) and text.strip():
            if role == "assistant" and text == GREETING:
                continue
            history.append({"role": role, "content": text})
    return history[-10:]


def record_analytics(question, answer, channel, response_time):
    try:
        log_interaction(
            question=question,
            channel=channel,
            response_time_seconds=response_time,
            escalated=detect_escalation(question, answer),
        )
    except Exception as error:
        print(f"Analytics logging failed: {error}")


def display_answer_audio(answer: str):
    try:
        with st.spinner("Generating voice response..."):
            audio_bytes = generate_speech(answer)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
            return audio_bytes
        st.info("Voice playback is unavailable for this response.")
    except Exception as error:
        st.warning(f"Text response is ready, but voice playback failed: {error}")
    return None


def answer_question(question: str, channel: str):
    history = get_conversation_history()
    # For voice questions, the user message was already appended before this call.
    if history and history[-1]["role"] == "user" and history[-1]["content"] == question:
        history = history[:-1]
    with st.chat_message("assistant", avatar="🎧"):
        with st.spinner("VoxAssist is thinking..."):
            started = time.perf_counter()
            try:
                answer = get_llm_response(question, conversation_history=history)
            except Exception as error:
                print(f"LLM request failed: {error}")
                answer = "I'm sorry, I'm having trouble connecting right now. Please check the API configuration and try again."
            elapsed = time.perf_counter() - started
        record_analytics(question, answer, channel, elapsed)
        st.markdown(answer)
        audio_bytes = display_answer_audio(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer, "audio": audio_bytes})


def load_analytics():
    if not ANALYTICS_FILE.exists() or ANALYTICS_FILE.stat().st_size == 0:
        return pd.DataFrame()
    try:
        df = pd.read_csv(ANALYTICS_FILE)
        if df.empty:
            return df
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["response_time_seconds"] = pd.to_numeric(df["response_time_seconds"], errors="coerce")
        df["channel"] = df["channel"].fillna("unknown").astype(str).str.lower()
        df["topic"] = df["topic"].fillna("General")
        df["escalated"] = df["escalated"].astype(str).str.lower().isin(["true", "1", "yes"])
        return df
    except Exception as error:
        st.error(f"Could not read analytics data: {error}")
        return pd.DataFrame()


# ----------------------------- Sidebar navigation -----------------------------
with st.sidebar:
    st.markdown('<div class="va-brand"><div class="va-logo">V</div><div><div class="va-brand-name">VoxAssist AI</div><div class="va-muted">CUSTOMER EXPERIENCE PLATFORM</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="va-eyebrow">Workspace</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        ["Customer Support", "Analytics", "About"],
        label_visibility="collapsed",
        key="main_navigation",
    )
    st.divider()
    st.markdown("**System status**")
    st.markdown('<span class="va-pill">● Ready to assist</span>', unsafe_allow_html=True)
    st.caption("AI responses require a working Groq API connection.")
    st.divider()
    if st.button("↻ Clear conversation", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": GREETING, "audio": None}]
        st.session_state.voice_transcript = ""
        st.session_state.pending_question = None
        st.rerun()
    st.markdown('<div class="va-muted">Built with Python · Streamlit · Groq</div>', unsafe_allow_html=True)

# ----------------------------- Customer support -----------------------------
if page == "Customer Support":
    st.markdown('<div class="va-eyebrow">CUSTOMER EXPERIENCE / SUPPORT DESK</div>', unsafe_allow_html=True)
    st.title("Customer Support")
    st.markdown("A smarter support experience, powered by conversational AI.")
    st.markdown("""
    <div class="va-hero">
      <span class="va-pill">● AI ASSISTANT ONLINE</span>
      <h2 style="margin:16px 0 8px;">How can we help you today?</h2>
      <p style="color:#a9b8d0;max-width:720px;margin-bottom:0;">Ask about shipping, returns, refunds, payments, or store policies. Type a message or use your voice, and VoxAssist will respond with helpful guidance.</p>
    </div>
    """, unsafe_allow_html=True)
    total_messages = sum(1 for m in st.session_state.messages if m.get("role") == "user")
    m1, m2, m3 = st.columns(3)
    m1.metric("Conversation questions", total_messages)
    m2.metric("Input modes", "Text + Voice")
    m3.metric("Knowledge base", "ShopEase FAQs")
    st.divider()

    with st.expander("🎙️ Ask by voice", expanded=False):
        audio_file = st.audio_input("Record your question")
        c1, c2 = st.columns([1, 3])
        with c1:
            transcribe_clicked = st.button("Transcribe audio", disabled=audio_file is None, use_container_width=True)
        if transcribe_clicked and audio_file is not None:
            with st.spinner("Transcribing your recording..."):
                try:
                    transcript = transcribe_audio(audio_file)
                    st.session_state.voice_transcript = transcript
                    if transcript:
                        st.success("Transcription complete. Review it below before sending.")
                    else:
                        st.warning("No speech detected. Please try recording again.")
                except Exception as error:
                    st.error(f"Transcription failed: {error}")
        if st.session_state.voice_transcript:
            edited_transcript = st.text_area("Recognized speech (you can edit this)", value=st.session_state.voice_transcript, key="editable_transcript")
            if st.button("Send voice question", type="primary"):
                question = edited_transcript.strip()
                if question:
                    st.session_state.messages.append({"role": "user", "content": question, "audio": None})
                    st.session_state.voice_transcript = ""
                    st.session_state.pending_question = question
                    st.rerun()

    st.markdown("### Conversation")
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🎧" if message["role"] == "assistant" else "🙂"):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("audio"):
                st.audio(message["audio"], format="audio/wav")

    if st.session_state.pending_question:
        question = st.session_state.pending_question
        st.session_state.pending_question = None
        answer_question(question, "voice")

    if prompt := st.chat_input("Message VoxAssist about an order, refund, or policy..."):
        st.session_state.messages.append({"role": "user", "content": prompt, "audio": None})
        with st.chat_message("user", avatar="🙂"):
            st.markdown(prompt)
        answer_question(prompt, "text")

# ----------------------------- Analytics -----------------------------
elif page == "Analytics":
    st.markdown('<div class="va-eyebrow">INSIGHTS / PERFORMANCE</div>', unsafe_allow_html=True)
    st.title("Support Analytics")
    st.markdown("Monitor usage patterns and response performance from your locally logged interactions.")
    df = load_analytics()
    if df.empty:
        st.info("No interaction data yet. Open Customer Support, ask VoxAssist a few questions, then return here.")
    else:
        valid_dates = df["timestamp"].dropna()
        if not valid_dates.empty:
            min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
            selected = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
            if isinstance(selected, (tuple, list)) and len(selected) == 2:
                start_date, end_date = selected
                df = df[df["timestamp"].dt.date.between(start_date, end_date)]
        total = len(df)
        text_count = int((df["channel"] == "text").sum())
        voice_count = int((df["channel"] == "voice").sum())
        avg_time = df["response_time_seconds"].dropna().mean()
        escalation_rate = float(df["escalated"].mean() * 100) if total else 0
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total interactions", f"{total:,}")
        k2.metric("Text interactions", f"{text_count:,}")
        k3.metric("Voice interactions", f"{voice_count:,}")
        k4.metric("Avg. AI response", f"{avg_time:.2f}s" if pd.notna(avg_time) else "—")
        st.caption(f"Escalation flag rate: {escalation_rate:.1f}% · Keyword-based estimate, not a confirmed human handoff.")
        left, right = st.columns(2)
        with left:
            st.markdown("#### Channel distribution")
            channel_counts = df["channel"].value_counts().rename_axis("Channel").reset_index(name="Interactions")
            if not channel_counts.empty:
                st.plotly_chart(px.pie(channel_counts, names="Channel", values="Interactions", hole=.55), use_container_width=True)
        with right:
            st.markdown("#### Common support topics")
            topic_counts = df["topic"].value_counts().rename_axis("Topic").reset_index(name="Interactions")
            if not topic_counts.empty:
                st.plotly_chart(px.bar(topic_counts, x="Topic", y="Interactions", color="Topic"), use_container_width=True)
        trend = df.dropna(subset=["timestamp"]).copy()
        if not trend.empty:
            trend["Date"] = trend["timestamp"].dt.date
            daily = trend.groupby(["Date", "channel"]).size().reset_index(name="Interactions")
            st.markdown("#### Interaction trends")
            st.plotly_chart(px.line(daily, x="Date", y="Interactions", color="channel", markers=True), use_container_width=True)
        st.markdown("#### Recent interactions")
        display = df.sort_values("timestamp", ascending=False, na_position="last").copy()
        display["escalated"] = display["escalated"].map({True: "Flagged", False: "Not flagged"})
        st.dataframe(display[["timestamp", "question", "channel", "response_time_seconds", "topic", "escalated"]], use_container_width=True, hide_index=True)
        st.caption("Response time excludes speech synthesis. Questions are stored locally in data/analytics.csv; avoid logging sensitive customer data.")

# ----------------------------- About -----------------------------
else:
    st.markdown('<div class="va-eyebrow">PLATFORM / OVERVIEW</div>', unsafe_allow_html=True)
    st.title("About VoxAssist AI")
    st.markdown("A portfolio project exploring multimodal customer support with retrieval-augmented generation.")
    st.markdown("""
    <div class="va-hero">
      <span class="va-pill">PROJECT OVERVIEW</span>
      <h2 style="margin:16px 0 8px;">Support that can listen, understand, and respond.</h2>
      <p style="color:#a9b8d0;max-width:780px;">VoxAssist combines a conversational language model with a searchable FAQ knowledge base, voice transcription, speech generation, and lightweight analytics in one Streamlit application.</p>
    </div>
    """, unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        st.markdown("### Core capabilities")
        st.markdown("- Text-based customer support chat\n- Voice recording and transcription\n- Spoken AI responses\n- RAG-based FAQ retrieval\n- Conversation context for follow-up questions\n- Interaction analytics dashboard")
    with b:
        st.markdown("### Technology stack")
        st.markdown("- **Python & Streamlit** — application and interface\n- **Groq API** — language-model inference\n- **Faster-Whisper** — speech-to-text\n- **Piper TTS** — text-to-speech\n- **ChromaDB** — vector search for FAQ content\n- **Pandas & Plotly** — analytics and charts")
    st.markdown("### How a request flows")
    steps = st.columns(4)
    for col, number, title, detail in zip(steps, ["01", "02", "03", "04"], ["Capture", "Retrieve", "Respond", "Measure"], ["Text input or voice recording", "Search relevant FAQ context", "Generate text and optional speech", "Log interaction metrics locally"]):
        with col:
            st.markdown(f'<div class="va-card"><div class="va-eyebrow">{number}</div><h3 style="font-size:18px;margin:10px 0;">{title}</h3><div class="va-muted">{detail}</div></div>', unsafe_allow_html=True)
    st.info("ShopEase is a fictional demo business. Review the sample FAQ policies before adapting VoxAssist for real customer support.")
    st.markdown("**Repository:** [AbhishekBharadwaj2003/VoxAssist-AI](https://github.com/AbhishekBharadwaj2003/VoxAssist-AI)")
