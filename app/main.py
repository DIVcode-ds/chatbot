import base64
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from .db import init_db, create_user, get_user, save_message, get_messages
from .ai import generate_answer, transcribe_audio, text_to_speech

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Nova AI Chatbot", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

init_db()


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    message: str
    language: str = "English"
    conversation_id: str = "default"
    image_data_url: Optional[str] = None


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/register")
def register(data: RegisterRequest):
    name = data.name.strip()
    email = data.email.strip().lower()
    if len(name) < 2:
        raise HTTPException(400, "Name is too short.")
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    if get_user(email):
        raise HTTPException(409, "An account with this email already exists.")

    user_id = create_user(name, email, hash_password(data.password))
    token = create_access_token({"sub": str(user_id), "email": email, "name": name})
    return {"token": token, "user": {"id": user_id, "name": name, "email": email}}


@app.post("/api/login")
def login(data: LoginRequest):
    email = data.email.strip().lower()
    user = get_user(email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password.")

    token = create_access_token(
        {"sub": str(user["id"]), "email": user["email"], "name": user["name"]}
    )
    return {
        "token": token,
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
    }


@app.get("/api/me")
def me(user=Depends(get_current_user)):
    return {"user": user}


@app.get("/api/history")
def history(conversation_id: str = "default", user=Depends(get_current_user)):
    return {"messages": get_messages(user["id"], conversation_id)}


@app.post("/api/chat")
def chat(data: ChatRequest, user=Depends(get_current_user)):
    if not data.message.strip():
        raise HTTPException(400, "Message cannot be empty.")

    save_message(user["id"], data.conversation_id, "user", data.message)

    answer = generate_answer(
        message=data.message,
        language=data.language,
        history=get_messages(user["id"], data.conversation_id)[-20:],
        image_data_url=data.image_data_url,
    )

    save_message(user["id"], data.conversation_id, "assistant", answer)
    return {"answer": answer}


@app.post("/api/upload")
async def upload(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    allowed = {
        "image/png", "image/jpeg", "image/webp", "image/gif",
        "application/pdf", "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if file.content_type not in allowed:
        raise HTTPException(400, "Supported files: PNG, JPG, WEBP, GIF, PDF, TXT, DOCX.")

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "Maximum upload size is 15 MB.")

    safe_name = f"{uuid.uuid4().hex}_{Path(file.filename or 'file').name}"
    path = UPLOAD_DIR / safe_name
    path.write_bytes(content)

    # Images are returned as data URLs so the browser can preview them and
    # the AI can receive the image in the chat request.
    if file.content_type.startswith("image/"):
        encoded = base64.b64encode(content).decode("utf-8")
        return {
            "type": "image",
            "name": file.filename,
            "data_url": f"data:{file.content_type};base64,{encoded}",
        }

    extracted = ""
    if file.content_type == "text/plain":
        extracted = content.decode("utf-8", errors="ignore")
    elif file.content_type == "application/pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            extracted = "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception:
            extracted = ""
    elif file.content_type.endswith("wordprocessingml.document"):
        try:
            from docx import Document
            doc = Document(str(path))
            extracted = "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            extracted = ""

    return {
        "type": "document",
        "name": file.filename,
        "text": extracted[:120000],
        "message": "File uploaded. The extracted text can be attached to your next question."
    }


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), user=Depends(get_current_user)):
    content = await audio.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(413, "Audio file is too large.")
    result = transcribe_audio(content, audio.filename or "recording.webm")
    return {"text": result}


@app.post("/api/speak")
def speak(text: str = Form(...), user=Depends(get_current_user)):
    if not text.strip():
        raise HTTPException(400, "Text is empty.")
    audio = text_to_speech(text[:4000])
    filename = UPLOAD_DIR / f"tts_{uuid.uuid4().hex}.mp3"
    filename.write_bytes(audio)
    return FileResponse(filename, media_type="audio/mpeg", filename="answer.mp3")
