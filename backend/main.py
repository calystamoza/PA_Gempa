import uuid
import io
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from models import (
    ChatRequest,
    LoginRequest,
    UserSession,
    CreateUserRequest,
    EarthquakeInput,
)
from auth import hash_password, verify_password
from rag_engine import process_query
from database import (
    create_session,
    get_sessions,
    get_messages,
    save_message,
    delete_session,
    get_user_by_username,
    create_user,
    insert_earthquake,
    insert_earthquakes_batch,
    get_next_earthquake_id,
)

app = FastAPI(title="GempaBot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helper: cek role admin ───────────────────────────────────────────────────

def require_admin(x_user_role: str | None):
    """Raise 403 jika bukan admin. Digunakan di endpoint admin."""
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Akses ditolak — hanya admin")


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "message": "GempaBot API v2 is running"}


# ─── Auth Endpoints ───────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=UserSession)
def login(request: LoginRequest):
    """Login dengan username dan password. Kembalikan user_id, username, role."""
    user = get_user_by_username(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Username atau password salah")
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    return UserSession(
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
    )


@app.post("/auth/register", response_model=UserSession)
def register(request: CreateUserRequest, x_user_role: str | None = Header(default=None)):
    """
    Registrasi user baru.
    - Role 'admin' hanya bisa dibuat oleh admin yang sudah login.
    - Role 'user' bisa dibuat siapa saja (untuk setup awal).
    """
    if request.role == "admin":
        require_admin(x_user_role)

    if request.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role harus 'admin' atau 'user'")

    existing = get_user_by_username(request.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username sudah digunakan")

    hashed = hash_password(request.password)
    user = create_user(request.username, hashed, request.role)
    if not user:
        raise HTTPException(status_code=500, detail="Gagal membuat user")

    return UserSession(
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
    )


# ─── Chat Endpoints ───────────────────────────────────────────────────────────

@app.post("/chat")
def chat(request: ChatRequest):
    """Kirim pertanyaan, dapatkan jawaban berbasis data gempa."""
    session_id = request.session_id or str(uuid.uuid4())
    is_new_session = not request.session_id

    # Buat session baru jika belum ada
    if is_new_session:
        session_name = request.query[:60] + ("..." if len(request.query) > 60 else "")
        create_session(session_id, session_name, request.user_id)

    # Ambil history percakapan untuk konteks (maks 6 pesan terakhir)
    history = get_messages(session_id)

    # Simpan pesan user
    save_message(session_id, "user", request.query)

    # Proses RAG pipeline
    result = process_query(request.query, history, session_id=session_id)

    # Simpan jawaban assistant
    save_message(session_id, "assistant", result["answer"])

    return {
        "session_id": session_id,
        "answer": result["answer"],
        "validated": result.get("validated", False),
        "source": result.get("source", "supabase"),
        "method": result.get("method", "sql-comparison"),
        "sql_query": result.get("sql_query"),
        "data_count": result.get("data_count", 0),
        "fetched_data": result.get("fetched_data", []),
    }


@app.get("/sessions")
def list_sessions(user_id: str | None = None):
    """Ambil semua sesi percakapan, opsional filter by user_id."""
    return get_sessions(user_id)


@app.get("/history/{session_id}")
def get_history(session_id: str):
    """Ambil semua pesan dalam satu sesi."""
    messages = get_messages(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    return messages


@app.delete("/history/{session_id}")
def delete_chat(session_id: str):
    """Hapus sesi percakapan."""
    delete_session(session_id)
    return {"message": "Sesi berhasil dihapus"}


# ─── Admin: Data Gempa ────────────────────────────────────────────────────────

@app.get("/admin/earthquakes/next-id")
def next_earthquake_id(x_user_role: str | None = Header(default=None)):
    """Ambil ID berikutnya untuk data gempa baru. Hanya admin."""
    require_admin(x_user_role)
    next_id = get_next_earthquake_id()
    return {"next_id": str(next_id)}


@app.post("/admin/earthquakes")
def add_earthquake(
    data: EarthquakeInput,
    x_user_role: str | None = Header(default=None),
):
    """Insert satu data gempa secara manual. Hanya admin."""
    require_admin(x_user_role)
    ok = insert_earthquake(data.model_dump())
    if not ok:
        raise HTTPException(status_code=500, detail="Gagal menyimpan data gempa")
    return {"message": "Data gempa berhasil ditambahkan", "id": data.id}


@app.post("/admin/earthquakes/upload")
async def upload_earthquakes_csv(
    file: UploadFile = File(...),
    x_user_role: str | None = Header(default=None),
):
    """Upload CSV data gempa (batch insert). Hanya admin."""
    require_admin(x_user_role)

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File harus berformat CSV")

    content = await file.read()
    # Coba UTF-8 dulu, fallback ke latin-1 untuk file lama
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Gagal membaca encoding CSV: {e}")

    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca CSV: {e}")

    # Rename kolom province → place (sesuai format data_gempa_processed.csv)
    df.rename(columns={"province": "place"}, inplace=True)

    # Normalisasi depth_category ke lowercase agar konsisten dengan RAG engine
    if "depth_category" in df.columns:
        df["depth_category"] = df["depth_category"].str.lower().str.strip()

    # Kolom yang diharapkan (sesuai skema DB)
    required_cols = {"id"}
    missing = required_cols - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Kolom wajib tidak ditemukan: {missing}",
        )

    # Isi kolom opsional yang tidak ada dengan None
    all_cols = [
        "id", "place", "date", "month", "month_name",
        "year", "latitude", "longitude", "magnitude", "depth",
        "depth_category", "time",
    ]
    for col in all_cols:
        if col not in df.columns:
            df[col] = None

    # Konversi ke list of dict, ganti NaN → None
    rows = df[all_cols].where(df[all_cols].notna(), other=None).to_dict(orient="records")

    result = insert_earthquakes_batch(rows)
    skipped = result.get("skipped", 0)
    skipped_msg = f", {skipped} dilewati (ID duplikat)" if skipped > 0 else ""
    return {
        "message": f"Proses selesai: {result['success']} berhasil{skipped_msg}, {result['failed']} gagal",
        **result,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
