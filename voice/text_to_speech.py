import io
import wave
from pathlib import Path

import streamlit as st
from piper import PiperVoice


# Voice model downloaded by Piper
VOICE_MODEL = (
    Path(__file__).resolve().parent.parent
    / "en_US-lessac-medium.onnx"
)


@st.cache_resource
def load_voice():
    """Load and cache the local Piper voice model."""
    if not VOICE_MODEL.exists():
        raise FileNotFoundError(
            f"Voice model not found: {VOICE_MODEL}\n"
            "Please check where Piper downloaded the model."
        )

    return PiperVoice.load(str(VOICE_MODEL))


def generate_speech(text: str) -> bytes:
    """Convert text into WAV audio and return its bytes."""
    if not text or not text.strip():
        return b""

    voice = load_voice()
    audio_buffer = io.BytesIO()

    with wave.open(audio_buffer, "wb") as wav_file:
        voice.synthesize_wav(text.strip(), wav_file)

    return audio_buffer.getvalue()