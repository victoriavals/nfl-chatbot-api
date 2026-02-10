# 🤖 NFL Chatbot API

FastAPI backend untuk fal bot - RAG-based WhatsApp chatbot.

## 📋 Quick Start

### 1. Install Dependencies
```bash
cd nfl-chatbot-api
pip install -r requirements.txt
```

### 2. Setup Supabase (Optional - for persistent memory)
Jika ingin memory persist across server restarts:

1. Buat akun di [Supabase](https://supabase.com)
2. Buat project baru
3. Jalankan SQL ini di SQL Editor:
   ```sql
   CREATE TABLE chat_memory (
       id BIGSERIAL PRIMARY KEY,
       user_id TEXT NOT NULL,
       role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
       content TEXT NOT NULL,
       created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_chat_memory_user_id ON chat_memory(user_id);
   ```
4. Ambil credentials dari Settings → API

### 3. Set Environment Variables
Pastikan file `.env` di root project sudah berisi:
```env
# LLM API Keys (minimal 1)
MY_CEREBRAS_API_KEY=your_key
MY_GROQ_API_KEY=your_key
MY_OPENROUTER_API_KEY=your_key
MY_GEMINI_API_KEY=your_key

# API Authentication (optional)
NFL_CHATBOT_API_KEY=your_custom_key

# Supabase (optional - for persistent memory)
SUPABASE_PROJECT_URL=https://your-project.supabase.co
SUPABASE_ANON_PUBLIC_KEY=eyJhbGc...
```

### 4. Run Server
```bash
uvicorn main:app --reload --port 8000
```

### 5. Test API
```bash
# Health check
curl http://localhost:8000/api/health

# Chat
curl -X POST http://localhost:8000/api/chat \
  -H "X-API-Key: nfl-dev-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test123", "message": "Siapa kamu?"}'
```

---

## 🔌 API Endpoints

| Method | Endpoint | Auth | Deskripsi |
|--------|----------|------|-----------|
| GET | `/api/health` | ❌ | Health check |
| POST | `/api/chat` | ✅ | Chat dengan RAG |
| DELETE | `/api/memory/{user_id}` | ✅ | Clear memory |
| GET | `/api/memory/{user_id}/length` | ✅ | Get memory length |

### POST /api/chat

**Request:**
```json
{
  "user_id": "62812345678",
  "message": "Siapa kamu?",
  "include_memory": true
}
```

**Response:**
```json
{
  "status": "success",
  "response": "Aku fal bot, representasi digital dari Naufal...",
  "provider": "Ai4Chat",
  "model": "ai4chat",
  "memory_length": 2
}
```

---

## 🏗️ Architecture

```
nfl-chatbot-api/
├── main.py              # FastAPI entry
├── config.py            # Configuration
├── models/
│   └── schemas.py       # Pydantic models
├── services/
│   ├── llm_service.py   # LLM with fallback
│   ├── rag_service.py   # RAG pipeline
│   └── memory_service.py # Conversation memory
├── routes/
│   └── chat_routes.py   # API endpoints
├── requirements.txt
└── vercel.json          # Vercel deployment
```

## 🔄 LLM Fallback Order

1. **Ai4Chat** (Primary - Free)
2. **Cerebras** (Fallback 1)
3. **Groq** (Fallback 2)
4. **OpenRouter** (Fallback 3)
5. **Gemini** (Fallback 4)

---

## 🚀 Deploy to Vercel

```bash
cd nfl-chatbot-api
vercel
```

Set environment variables di Vercel dashboard.
