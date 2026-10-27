from faster_whisper import WhisperModel
import streamlit as st


@st.cache_resource
def load_model():
    """Load and cache the lightweight speech recognition model."""
    return WhisperModel(
        "tiny",
        device="cpu",
        compute_type="int8",
    )


def transcribe_audio(audio_file) -> str:
    """Convert an uploaded audio recording into text."""

    model = load_model()

    segments, _ = model.transcribe(
        audio_file,
        beam_size=1,
        vad_filter=True,
    )

    transcription = " ".join(
        segment.text.strip()
        for segment in segments
    )

    return transcription.strip()