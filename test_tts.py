
from voice.text_to_speech import generate_speech

print("Loading Piper voice model...")

try:
    audio_bytes = generate_speech(
        "Hello! Welcome to VoxAssist AI. "
        "I am your AI-powered customer support assistant."
    )

    with open("test_voice.wav", "wb") as audio_file:
        audio_file.write(audio_bytes)

    print("Success! Speech generated.")
    print("Audio saved as test_voice.wav")

except Exception as error:
    print(f"Speech generation failed: {error}")
