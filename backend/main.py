import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import ChatRequest
from rag_engine import process_query
from database import (
    create_session,
    get_sessions,
    get_messages,
    save_message,
    delete_session,
)

app = FastAPI(title="GempaBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "message": "GempaBot API is running"}


@app.post("/chat")
async def chat(request: ChatRequest):
    """Kirim pertanyaan, dapatkan jawaban berbasis data gempa."""
    session_id = request.session_id or str(uuid.uuid4())
    is_new_session = not request.session_id

    # Buat session baru jika belum ada
    if is_new_session:
        # Gunakan 60 karakter pertama query sebagai nama sesi
        session_name = request.query[:60] + ("..." if len(request.query) > 60 else "")
        create_session(session_id, session_name)

    # Ambil history percakapan untuk konteks
    history = get_messages(session_id)

    # Simpan pesan user
    save_message(session_id, "user", request.query)

    # Proses RAG pipeline
    result = process_query(request.query, history)

    # Simpan jawaban assistant
    save_message(session_id, "assistant", result["answer"])

    return {
        "session_id": session_id,
        "answer": result["answer"],
        "sql_query": result.get("sql_query"),
        "data_count": result.get("data_count", 0),
    }


@app.get("/sessions")
async def list_sessions():
    """Ambil semua sesi percakapan."""
    return get_sessions()


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Ambil semua pesan dalam satu sesi."""
    messages = get_messages(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    return messages


@app.delete("/history/{session_id}")
async def delete_chat(session_id: str):
    """Hapus sesi percakapan."""
    delete_session(session_id)
    return {"message": "Sesi berhasil dihapus"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
