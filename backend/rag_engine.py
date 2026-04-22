import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
from database import execute_query

load_dotenv()

# ─── Groq Client ─────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.1-8b-instant"  # model aktif Groq (cepat & gratis)

# ─── Kolom aman untuk ORDER BY (whitelist anti SQL injection) ─────────────────
SAFE_COLUMNS = {"magnitude", "depth", "year", "month", "count", "avg_magnitude"}
SAFE_DIRECTIONS = {"ASC", "DESC"}

NUMERIC_TOLERANCE = 0.15  # Sedikit lebih longgar untuk mengakomodasi pembulatan LLM


# ─── Helper: call Groq ────────────────────────────────────────────────────────

def call_groq(system_prompt: str, user_message: str, max_tokens: int = 512) -> str:
    """Wrapper sederhana untuk Groq Chat Completions."""
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[GROQ ERROR] {e}")
        raise


# ─── 1. Parse Intent via Groq ────────────────────────────────────────────────

INTENT_SYSTEM = """Kamu adalah parser intent untuk chatbot data gempa bumi Indonesia.
Tugasmu: konversi pertanyaan user ke JSON yang mendeskripsikan query database.

Schema database:
- Tabel: earthquakes
- Kolom:
  * place        : TEXT (nama provinsi)
  * year         : INTEGER
  * month        : INTEGER
  * magnitude    : FLOAT
  * depth        : FLOAT
  * depth_category: TEXT ('dangkal', 'menengah', 'dalam')

Format JSON yang HARUS dikembalikan:
{
  "intent": "count|average|max|min|list|trend|general|knowledge",
  "metric": "magnitude|depth|count|null",
  "filters": {
    "place": null,
    "year": null,
    "month": null,
    "depth_category": null,
    "min_magnitude": null,
    "max_magnitude": null
  },
  "group_by": "year|month|place|null",
  "order_by": "magnitude|depth|year|count|null",
  "order_dir": "DESC|ASC",
  "limit": 10
}

Panduan Intent:
- "gempa terbesar/terkuat" -> intent "max", metric "magnitude", order_by "magnitude", order_dir "DESC"
- "gempa terdalam" -> intent "max", metric "depth", order_by "depth", order_dir "DESC"
- "daftar gempa" -> intent "list"
- "apa itu gempa", "edukasi", "penjelasan umum" -> intent "knowledge"
- Singkatan wilayah WAJIB dieja penuh untuk kolom place (misal: "jatim" -> "Jawa Timur", "jabar" -> "Jawa Barat", "jateng" -> "Jawa Tengah", "jogja/diy" -> "Yogyakarta", "dki" -> "DKI Jakarta").
- Jika user bertanya tentang "Indonesia" secara umum, kosongkan filter place (null).

Kembalikan HANYA JSON."""


def parse_intent(question: str, history: list = []) -> dict:
    history_str = "\n".join([f"{m['role']}: {m['content'][:100]}" for m in history[-6:]])
    user_msg = f"Riwayat percakapan:\n{history_str or '(tidak ada)'}\n\nPertanyaan: {question}"
    try:
        text = call_groq(INTENT_SYSTEM, user_msg, max_tokens=300)
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()
        return json.loads(text)
    except Exception:
        return {"intent": "general", "filters": {}, "limit": 10}


# ─── 2. Build SQL dari Intent ─────────────────────────────────────────────────

def build_sql(intent: dict) -> tuple[str, list]:
    filters = intent.get("filters") or {}
    intent_type = intent.get("intent", "general")
    metric = intent.get("metric") or "count"
    group_by = intent.get("group_by")
    order_by = intent.get("order_by")
    order_dir = intent.get("order_dir", "DESC")
    limit = intent.get("limit", 10)

    if order_by not in SAFE_COLUMNS: order_by = None
    if order_dir not in SAFE_DIRECTIONS: order_dir = "DESC"

    where_parts, params = [], []
    place_filter = filters.get("place")
    if place_filter and place_filter.lower() != "indonesia":
        where_parts.append("LOWER(place) LIKE %s")
        params.append(f"%{place_filter.lower()}%")
    if filters.get("year"):
        where_parts.append("year = %s")
        params.append(int(filters["year"]))
    if filters.get("month"):
        where_parts.append("month = %s")
        params.append(int(filters["month"]))
    if filters.get("depth_category"):
        where_parts.append("depth_category = %s")
        params.append(filters["depth_category"])
    if filters.get("min_magnitude"):
        where_parts.append("magnitude >= %s")
        params.append(float(filters["min_magnitude"]))
    if filters.get("max_magnitude"):
        where_parts.append("magnitude <= %s")
        params.append(float(filters["max_magnitude"]))

    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    # Logic SQL sesuai dengan struktur data
    if group_by == "year":
        select = "SELECT year, COUNT(*) AS count, ROUND(AVG(magnitude)::numeric, 2) AS avg_magnitude, MAX(magnitude) AS max_magnitude, MIN(magnitude) AS min_magnitude"
        group = "GROUP BY year ORDER BY year ASC"
        limit_clause = ""
    elif group_by == "month":
        select = "SELECT month, month_name, COUNT(*) AS count, ROUND(AVG(magnitude)::numeric, 2) AS avg_magnitude"
        group = "GROUP BY month, month_name ORDER BY month ASC"
        limit_clause = ""
    elif group_by == "place":
        select = "SELECT place, COUNT(*) AS count, ROUND(AVG(magnitude)::numeric, 2) AS avg_magnitude"
        group = f"GROUP BY place ORDER BY count {order_dir}"
        limit_clause = f"LIMIT {int(limit or 15)}"
    elif intent_type == "average":
        col = metric if metric in ("magnitude", "depth") else "magnitude"
        select = f"SELECT ROUND(AVG({col})::numeric, 3) AS avg_{col}, COUNT(*) AS total_earthquakes"
        group, limit_clause = "", ""
    elif intent_type in ("max", "min"):
        select = "SELECT place, date, magnitude, depth, depth_category, time"
        order_col = order_by or (metric if metric in ("magnitude", "depth") else "magnitude")
        forced_dir = "DESC" if intent_type == "max" else "ASC"
        group = f"ORDER BY {order_col} {forced_dir}"
        limit_clause = f"LIMIT {int(limit or 5)}"
    elif intent_type == "count":
        select = "SELECT COUNT(*) AS total_earthquakes"
        group, limit_clause = "", ""
    elif intent_type == "list":
        select = "SELECT date, place, magnitude, depth, depth_category, time"
        group = f"ORDER BY magnitude {order_dir}"
        limit_clause = f"LIMIT {int(limit or 10)}"
    else:  # general
        select = "SELECT COUNT(*) AS total, ROUND(AVG(magnitude)::numeric, 2) AS avg_magnitude, MAX(magnitude) AS max_magnitude, MIN(magnitude) AS min_magnitude"
        group, limit_clause = "", ""

    sql = f"{select} FROM earthquakes {where} {group} {limit_clause}".strip()
    return sql, params


# ─── 3. Format Data sebagai Context ──────────────────────────────────────────

def format_data(data: list, intent: dict) -> str:
    if not data: return "Tidak ada data yang ditemukan."
    
    intent_type = intent.get("intent", "general")
    group_by = intent.get("group_by")
    filters = intent.get("filters") or {}
    
    filter_strs = []
    if filters.get("place"): filter_strs.append(f"Lokasi: {filters['place']}")
    if filters.get("year"): filter_strs.append(f"Tahun: {filters['year']}")
    if filters.get("month"): filter_strs.append(f"Bulan: {filters['month']}")
    if filters.get("depth_category"): filter_strs.append(f"Kedalaman: {filters['depth_category']}")
    
    lines = []
    if filter_strs:
        lines.append(f"📌 Filter Data: {', '.join(filter_strs)}")
        lines.append("-" * 30)

    if group_by == "year":
        lines.append("📊 Tren gempa per tahun:")
        for row in data:
            lines.append(f"  • {row.get('year')}: {row.get('count')} kejadian | Rata-rata: {row.get('avg_magnitude')} | Max: {row.get('max_magnitude')}")
    elif group_by == "place":
        lines.append("🗺️ Distribusi gempa per provinsi:")
        for i, row in enumerate(data, 1):
            lines.append(f"  {i}. {row.get('place')}: {row.get('count')} kejadian | Rata-rata: {row.get('avg_magnitude')}")
    elif intent_type in ("max", "min", "list"):
        lines.append(f"📋 Data Gempa {intent_type.upper()}:")
        for i, row in enumerate(data, 1):
            lines.append(f"  {i}. {row.get('date')} | {row.get('place')} | M{row.get('magnitude')} | {row.get('depth')} km")
    else:
        for i, row in enumerate(data, 1):
            row_str = " | ".join([f"{k}: {v}" for k, v in row.items()])
            lines.append(f"{i}. {row_str}")
            
    return "\n".join(lines)


# ─── 4. Generate Response via Groq ───────────────────────────────────────────

ANSWER_SYSTEM = """Kamu adalah asisten ahli seismologi Indonesia yang ramah.
TUGAS UTAMA: Jawablah pertanyaan user dengan panduan berikut:
1. Jika pertanyaan berkaitan dengan DATA (angka, statistik, lokasi, tanggal), gunakan HANYA "Data Database" yang diberikan. Jangan berhalusinasi angka.
2. Jika pertanyaan bersifat UMUM/EDUKASI (misal: "Apa itu gempa?", "Tips keselamatan"), gunakan pengetahuanmu sebagai ahli seismologi untuk menjawab secara jelas dan ramah.
3. JIKA data database mencakup tanggal dan lokasi, sebutkan informasi tersebut. Jika tidak ada, cukup jelaskan angka yang tersedia.
4. Jika database kosong padahal user meminta data statistik, katakan dengan sopan bahwa data tersebut belum tersedia."""

CORRECTION_SYSTEM = """Kamu adalah asisten ahli seismologi yang sangat teliti.
PERINGATAN: Jawaban sebelumnya mungkin salah atau kurang tepat.
TUGAS: Gunakan "Data Database" yang benar di bawah ini untuk memberikan jawaban yang akurat kepada user.
- Jangan mengulangi kesalahan sebelumnya.
- Berikan informasi yang BENAR dari database secara naratif (chat biasa).
- Gunakan HANYA informasi yang secara eksplisit ada di Data Database untuk bagian angka/statistik."""


def generate_response(question: str, context: str, history: list, system_prompt: str = ANSWER_SYSTEM) -> str:
    history_str = "\n".join([f"{m['role'].title()}: {m['content'][:200]}" for m in history[-6:]])
    # Prompt grounding diperkuat untuk Groq agar tidak halusinasi
    user_msg = f"PENTING: Gunakan HANYA 'Data Database' di bawah ini sebagai sumber jawaban. Abaikan jika riwayat percakapan sebelumnya gagal menemukan data.\n\nRiwayat percakapan:\n{history_str or '(percakapan baru)'}\n\nData Database:\n{context}\n\nPertanyaan User: {question}\n\nJawaban:"
    try:
        return call_groq(system_prompt, user_msg, max_tokens=600)
    except Exception as e:
        return f"Error: {e}"


# ─── 5. Numeric Extraction ───────────────────────────────────────────────────

def extract_numbers_from_text(text: str) -> list[float]:
    """
    Ekstrak angka secara cerdas, menangkap format Indonesia (9,0 atau 1.000) 
    dan Internasional (9.0 atau 1,000). Mendukung prefix seperti M9.0.
    """
    # Regex untuk menangkap angka dengan pemisah (titik atau koma)
    pattern = r"(?<!\d)\d+(?:[.,]\d+)*(?!\d)"
    matches = re.findall(pattern, text)
    
    results = []
    for m in matches:
        # Jika tidak ada pemisah, langsung masukkan
        if "." not in m and "," not in m:
            try:
                results.append(float(m))
            except ValueError: pass
            continue
            
        # Hitung kemunculan titik dan koma
        dots = m.count(".")
        commas = m.count(",")
        
        # Kasus 1: Ada titik dan koma (misal 1.234,56 atau 1,234.56)
        if dots > 0 and commas > 0:
            last_dot = m.rfind(".")
            last_comma = m.rfind(",")
            if last_dot > last_comma:
                # Titik terakhir adalah desimal (gaya US: 1,234.56)
                clean = m.replace(",", "")
            else:
                # Koma terakhir adalah desimal (gaya ID: 1.234,56)
                clean = m.replace(".", "").replace(",", ".")
            try:
                results.append(float(clean))
            except ValueError: pass
            continue

        # Kasus 2: Hanya ada satu jenis pemisah (misal 1.000 atau 9.0)
        sep = "." if dots > 0 else ","
        parts = m.split(sep)
        
        # Jika pemisah muncul lebih dari sekali, itu pasti ribuan (misal 1.000.000)
        if len(parts) > 2:
            results.append(float(m.replace(sep, "")))
            continue
            
        # Jika hanya ada satu pemisah (misal "1.000" atau "9.0")
        if len(parts) > 1:
            if len(parts[1]) == 3:
                # Ambigu: bisa ribuan (1.000) atau desimal (1.234)
                results.append(float(m.replace(sep, ""))) # Asumsi ribuan
                results.append(float(m.replace(",", "."))) # Asumsi desimal
            else:
                # Bukan 3 digit, hampir pasti desimal (misal 9.0 atau 9.85)
                results.append(float(m.replace(",", ".")))
            
    return list(set(results))


def extract_key_numbers_from_db(data: list, intent: dict) -> list[float]:
    if not data: return []
    metric = intent.get("metric") or "magnitude"
    # Hanya validasi metric utama yang dicari user
    critical_keywords = {metric.lower(), "count", "total", "avg", "max"}
    numbers = []
    for row in data:
        for key, val in row.items():
            if val is not None and any(crit in key.lower() for crit in critical_keywords):
                try:
                    num = float(val)
                    if 1900 < num < 2100: continue # Skip tahun
                    numbers.append(num)
                except (ValueError, TypeError): continue
    return list(set(numbers))


# ─── 6. Validation Layer ─────────────────────────────────────────────────────

def validate_response(
    question: str, llm_answer: str, db_data: list, intent: dict, history: list
) -> tuple[bool, str]:
    intent_type = intent.get("intent", "general")
    if intent_type == "general" or not db_data:
        return True, llm_answer

    llm_numbers = extract_numbers_from_text(llm_answer)
    db_numbers = extract_key_numbers_from_db(db_data, intent)

    # Hanya validasi baris pertama untuk query daftar/max agar tidak terlalu ketat
    if intent_type in ("max", "min", "list") and len(db_data) > 1:
        db_numbers = extract_key_numbers_from_db(db_data[:1], intent)

    if not db_numbers:
        return True, llm_answer

    # Cek apakah setiap angka penting ada dalam jawaban LLM
    mismatched = [n for n in db_numbers if not any(abs(ln - n) <= NUMERIC_TOLERANCE for ln in llm_numbers)]

    if mismatched:
        print(f"[VALIDATION] Mismatch detected (DB expected {db_numbers}, but LLM said {llm_numbers}). Correcting...")
        db_context = format_data(db_data, intent)
        # Panggil Groq lagi dengan prompt koreksi
        corrected_answer = generate_response(question, db_context, history, system_prompt=CORRECTION_SYSTEM)
        return False, corrected_answer

    return True, llm_answer


# ─── 7. Main Entry Point ─────────────────────────────────────────────────────

def process_query(question: str, history: list = []) -> dict:
    intent = parse_intent(question, history)
    intent_type = intent.get("intent", "general")
    print(f"[INTENT] {json.dumps(intent)}")

    # Knowledge mode: bypass database
    if intent_type == "knowledge":
        print("[MODE] Knowledge/Educational")
        answer = generate_response(question, "(Pertanyaan edukasi umum, gunakan pengetahuan internal)", history)
        return {
            "answer": answer,
            "validated": True,
            "source": "llm-knowledge",
            "method": "direct-answer",
            "sql_query": None,
            "data_count": 0,
            "fetched_data": [],
        }

    try:
        sql, params = build_sql(intent)
        print(f"[SQL] {sql} | PARAMS: {params}")
    except Exception as e:
        print(f"[SQL BUILD ERROR] {e}")
        sql, params = "SELECT COUNT(*) FROM earthquakes", []

    db_data = execute_query(sql, params)
    print(f"[DATA] Returned {len(db_data)} rows")

    context = format_data(db_data, intent)
    raw_answer = generate_response(question, context, history)

    # Validation & Potential Correction
    validated, final_answer = validate_response(question, raw_answer, db_data, intent, history)
    print(f"[VALIDATION] validated={validated}")

    return {
        "answer": final_answer,
        "validated": validated,
        "source": "supabase",
        "method": "sql-comparison",
        "sql_query": sql,
        "data_count": len(db_data),
        "fetched_data": db_data,
    }
