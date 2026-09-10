import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
STT_MODEL = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")

SYSTEM = """
You are Nova, a helpful general-purpose AI assistant.
Answer clearly, accurately, and safely.
Respect the user's selected language. If the selected language is Hindi,
answer in natural Hindi; if Hinglish is selected, use natural Roman Hindi
mixed with English where appropriate.
Use Markdown for structured answers.
If you are uncertain, say so rather than inventing facts.
Do not claim to have browsed the internet unless a web-search tool is actually enabled.
"""

def generate_answer(message, language, history, image_data_url=None):
    input_items = [{"role": "system", "content": SYSTEM + f"\nSelected language: {language}"}]

    for item in history:
        role = item["role"]
        content = item["content"]
        input_items.append({"role": role, "content": content})

    content = [{"type": "input_text", "text": message}]
    if image_data_url:
        content.append({"type": "input_image", "image_url": image_data_url})

    input_items.append({"role": "user", "content": content})

    response = client.responses.create(
        model=MODEL,
        input=input_items,
    )
    return response.output_text


def transcribe_audio(content: bytes, filename: str):
    import io
    audio_file = io.BytesIO(content)
    audio_file.name = filename
    result = client.audio.transcriptions.create(
        model=STT_MODEL,
        file=audio_file,
    )
    return result.text


def text_to_speech(text: str):
    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="mp3",
    )
    return response.read()
