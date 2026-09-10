# Nova AI — Python ChatGPT-style chatbot

A complete starter AI chatbot built with Python/FastAPI.

## Included

- Login and account creation
- SQLite database
- JWT authentication
- AI text chat
- Conversation history
- Language selection
- Image uploads / vision
- PDF/TXT/DOCX uploads with text extraction
- Browser microphone recording
- Speech-to-text
- Text-to-speech API endpoint
- Responsive ChatGPT-style UI

## 1. Install Python

Use Python 3.11+.

## 2. Create a virtual environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install packages

```bash
pip install -r requirements.txt
```

## 4. Configure the API key

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

On Windows, simply duplicate the file in VS Code and rename it to `.env`.

Put your API key in:

```env
OPENAI_API_KEY=your_real_key
JWT_SECRET=use_a_long_random_secret
```

Never put the API key in `static/app.js` or any frontend file.

## 5. Start the server

```bash
uvicorn app.main:app --reload
```

Open:

http://127.0.0.1:8000

Create an account and start chatting.

## Deployment

This project is designed so FastAPI serves the frontend too, which makes initial deployment simple.

For production:

1. Use PostgreSQL instead of SQLite.
2. Store uploads in S3-compatible object storage.
3. Put the app behind HTTPS.
4. Set a strong JWT_SECRET.
5. Add rate limiting.
6. Restrict upload MIME types and scan files.
7. Add account email verification/password reset.
8. Do not commit `.env`.
9. Run with multiple workers where appropriate.

A typical production command is:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Important

The AI model and speech services require a valid API key and incur API usage charges.

The browser microphone normally requires HTTPS when deployed, although localhost works for development.

## Next upgrades

For a larger production system, add:

- Streaming responses
- Real-time voice conversation
- Web search
- Rate limiting
- Admin dashboard
- User billing/subscriptions
- PostgreSQL
- Redis
- S3 storage
- RAG/vector database
- Image generation
- Conversation rename/delete
- Dark mode
- Mobile app
