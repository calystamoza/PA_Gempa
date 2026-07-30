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
SAFE_COLUMNS = {"magnitude", "depth", "year", "month", "count", "avg_magnitude", "date"}
SAFE_DIRECTIONS = {"ASC", "DESC"}

# ─── Data Context (di-query dari DB saat startup, bukan hardcode) ────────────
TAHUN_SEKARANG = 2026

def _query_year_bounds() -> tuple[int, int]:
    """Query MAX dan MIN year dari DB. Fallback ke nilai default jika DB belum siap."""
    try:
        result = execute_query("SELECT MAX(year) AS max_year, MIN(year) AS min_year FROM earthquakes", [])
        if result and result[0].get("max_year") and result[0].get("min_year"):
            return int(result[0]["max_year"]), int(result[0]["min_year"])
    except Exception as e:
        print(f"[WARN] Gagal query year bounds dari DB: {e}. Menggunakan nilai default.")
    return 2024, 1900  # fallback default

DATA_TAHUN_TERBARU, DATA_TAHUN_TERTUA = _query_year_bounds()
print(f"[CONFIG] Rentang data: {DATA_TAHUN_TERTUA} - {DATA_TAHUN_TERBARU}")

NUMERIC_TOLERANCE = 0.15  # Sedikit lebih longgar untuk mengakomodasi pembulatan LLM


# ─── Helper: call Groq ────────────────────────────────────────────────────────

def call_groq(system_prompt: str, user_message: str, max_tokens: int = 512, response_format: dict = None) -> str:
    """Wrapper sederhana untuk Groq Chat Completions."""
    api_key_preview = f"{groq_client.api_key[:8]}...{groq_client.api_key[-4:]}" if groq_client.api_key else "None"
    print(f"\n[GROQ API TRACE] Memanggil model: '{GROQ_MODEL}' menggunakan key: {api_key_preview}")
    try:
        kwargs = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        if response_format:
            kwargs["response_format"] = response_format
            
        response = groq_client.chat.completions.create(**kwargs)
        print(f"[GROQ API TRACE] SUCCESS! API hit berhasil.")
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[GROQ API TRACE] FAILED! Error saat memanggil Groq: {e}")
        raise


# ─── 1. Parse Intent via Groq ────────────────────────────────────────────────

INTENT_SYSTEM = f"""Kamu adalah parser intent untuk chatbot data gempa bumi Indonesia.
Tugasmu: konversi pertanyaan user ke JSON yang mendeskripsikan query database.

KONTEKS DATA (SANGAT PENTING — gunakan ini untuk menerjemahkan referensi waktu):
- Data tersedia dari tahun {DATA_TAHUN_TERTUA} hingga {DATA_TAHUN_TERBARU}.
- "Data terbaru" / "tahun terbaru" / "paling baru" = tahun {DATA_TAHUN_TERBARU}
- "Data terlama" / "tahun tertua" / "paling lama" = tahun {DATA_TAHUN_TERTUA}
- "Tahun ini" = {TAHUN_SEKARANG} (gunakan sebagai filter year, namun data mungkin tidak ada)
- "Tahun lalu" = {TAHUN_SEKARANG - 1}
- "5 tahun terakhir" = min_year {DATA_TAHUN_TERBARU - 4} (inklusif)
- "10 tahun terakhir" / "dekade terakhir" = min_year {DATA_TAHUN_TERBARU - 9}
- "Dekade ini" / "2020-an" = min_year 2020
- "2010-an" = min_year 2010, max_year 2019
- "Abad ini" / "era 2000-an" = min_year 2000
- "Era 1990-an" = min_year 1990, max_year 1999
- Jika user menyebut rentang seperti "antara X dan Y" atau "dari X sampai Y" → min_year=X, max_year=Y

Schema database:
- Tabel: earthquakes
- Kolom:
  * place        : TEXT (nama provinsi)
  * year         : INTEGER
  * month        : INTEGER
  * date         : DATE (tanggal kejadian, format YYYY-MM-DD — GUNAKAN INI untuk urutan terbaru/terakhir)
  * time         : TIME (waktu kejadian)
  * magnitude    : FLOAT
  * depth        : FLOAT
  * depth_category: TEXT ('dangkal', 'menengah', 'dalam')

Format JSON yang HARUS dikembalikan:
{{
  "intent": "count|average|max|min|list|trend|general|knowledge",
  "metric": "magnitude|depth|count|null",
  "filters": {{
    "place": null,
    "places": null,
    "year": null,
    "min_year": null,
    "max_year": null,
    "month": null,
    "depth_category": null,
    "min_magnitude": null,
    "max_magnitude": null
  }},
  "group_by": "year|month|place|day_of_week|null",
  "order_by": "magnitude|depth|year|month|count|date|null",
  "order_dir": "DESC|ASC",
  "limit": 10
}}

ATURAN PERBANDINGAN LOKASI:
- Jika pertanyaan mengandung kata "dibanding", "dibandingkan", "daripada", "lebih banyak dari", "lebih besar dari", "vs", "versus", "antara X dan Y", atau menyebut DUA ATAU LEBIH lokasi yang dibandingkan:
  * Set filters.place = null
  * Set filters.places = ["Lokasi A", "Lokasi B", ...] (array semua lokasi yang dibandingkan)
  * PERTAHANKAN intent asli (count/average/max/min/list/trend) — JANGAN ubah intent menjadi apapun yang lain
- Singkatan wilayah tetap dieja penuh dalam array places.
- Jika hanya satu lokasi disebutkan: gunakan filters.place seperti biasa, filters.places = null.

Panduan Intent:
- Jika user menyertakan tempat prvinsi wajib digunakan sebagai filter parameter, jika pertanyaan selanjutnya tidak dalam konteks tempat yang sama set ke filter dari pertanyaan baru atau set ke general
- JIKA pertanyaan user sangat singkat DAN tidak menyebut tahun/waktu spesifik (misal: "kalo di indo?", "hari apa?", "yang paling parah?"), kamu BOLEH mewarisi filter tahun dari riwayat percakapan.
- PENTING — ATURAN OVERRIDE WAKTU: Jika user SECARA EKSPLISIT menyebut tahun atau rentang waktu tertentu (misal: "2024", "tahun lalu", "5 tahun terakhir", "2020-2023"), WAJIB gunakan tahun/waktu yang disebutkan user dan ABAIKAN filter tahun dari riwayat sebelumnya. Tahun eksplisit dari user selalu menang.
- PENTING — RESET KONTEKS: Jika pertanyaan user jelas menanyakan hal BARU yang tidak berkaitan dengan topik sebelumnya (misal topik sebelumnya adalah jumlah gempa, lalu user tanya provinsi paling aman), HAPUS filter yang tidak relevan dari riwayat. Analisis topik pertanyaan, bukan hanya warisi filter secara membabi buta.
- PENTING UNTUK KONTEKS: Analisis apakah pertanyaan user merujuk pada topik sebelumnya atau menanyakan informasi global/keseluruhan. Jika user bertanya kelanjutan data (misal: "yang paling parah?"), pertahankan filter (seperti lokasi) dari riwayat. NAMUN, jika user jelas menanyakan keseluruhan data (misal: "tahun berapa data terakhir?", "berapa total semua data?"), HAPUS filter lokasi/waktu sebelumnya (set null) agar pencarian dilakukan secara global.

--- ATURAN INTENT (urutan prioritas dari atas ke bawah) ---

[KNOWLEDGE] JIKA pertanyaan bersifat edukasi/konsep/prosedur (misal: "apa itu...", "mengapa...", "bagaimana cara...", "apa perbedaan...", "tips saat gempa", "cara kerja seismograf"), WAJIB set intent "knowledge". ABAIKAN kata keterangan waktu/tempat.

[TREND] JIKA pertanyaan tentang POLA PERUBAHAN DARI WAKTU KE WAKTU (misal: "tren", "apakah makin sering/jarang", "bagaimana perubahan", "perkembangan dari tahun ke tahun", "per tahun", "per bulan", "dari waktu ke waktu", "frekuensi gempa per bulan", "selama dekade", "10 tahun terakhir ... bagaimana perubahannya"):
  - Set intent "trend"
  - Jika menyebut "per tahun" atau "tahunan" → group_by "year"
  - Jika menyebut "per bulan" atau "bulanan" → group_by "month"
  - Untuk rentang tahun: gunakan min_year/max_year
  - Contoh: "tren gempa per tahun" → trend/year, "perkembangan frekuensi per bulan" → trend/month, "apakah gempa makin sering?" → trend/year, "tren 10 tahun terakhir" → trend/year, min_year={DATA_TAHUN_TERBARU-9}

[LIST] JIKA pertanyaan menggunakan kata "sebutkan N", "tampilkan daftar N", "berikan daftar", "daftarkan", "list N gempa", "tolong berikan", atau menyebut angka spesifik dalam konteks MENAMPILKAN DATA (misal: "sebutkan 3 gempa terbesar", "tampilkan 5 gempa terkuat", "berikan daftar gempa di Jawa Barat"):
  - Set intent "list", bukan "max" atau "min"
  - Set limit sesuai angka yang disebutkan (default 10 jika tidak ada angka)
  - Set order_by dan order_dir sesuai kriteria:
    * terbesar/terkuat → order_by "magnitude", order_dir "DESC"
    * terdalam → order_by "depth", order_dir "DESC"
    * terdangkal/paling dangkal → order_by "depth", order_dir "ASC"
    * terbaru/terakhir/terkini → order_by "date", order_dir "DESC"
    * terlama/tertua/pertama → order_by "date", order_dir "ASC"

[MAX/MIN] JIKA pertanyaan mencari SATU nilai ekstrem tanpa kata "daftar/sebutkan" (misal: "apa gempa terbesar?", "di mana gempa paling dalam?", "kekuatan maksimal berapa?", "gempa terkuat yang pernah tercatat"):
  - Terbesar/terkuat/tertinggi/maksimal → intent "max", order_by sesuai metric, order_dir "DESC"
  - Terkecil/terdangkal/terendah/minimal → intent "min", order_by sesuai metric, order_dir "ASC"
  - PENTING: "paling dangkal" = depth KECIL → intent "min", metric "depth", order_by "depth", order_dir "ASC"
  - PENTING: "paling dalam/terdalam" = depth BESAR → intent "max", metric "depth", order_by "depth", order_dir "DESC"
  - PENTING: "gempa pertama/terlama/tertua yang tercatat" → intent "list", order_by "date", order_dir "ASC", limit 1
  - PENTING: "gempa terbaru" / "gempa terakhir" / "gempa terkini" / "gempa paling baru" / "kapan terakhir gempa" / "gempa apa yang terakhir" → intent "list", order_by "date", order_dir "DESC", limit 1
  - PENTING: Semua variasi frasa 'terbaru/terakhir/terkini' WAJIB menggunakan order_by "date" (BUKAN "year"), karena "date" memiliki resolusi hari sedangkan "year" hanya akurat sampai level tahun.
  - Contoh: "gempa terbaru" → list, order_by "date", DESC, limit 1
  - Contoh: "gempa terakhir di Aceh" → list, place "Aceh", order_by "date", DESC, limit 1
  - Contoh: "kapan gempa terkini di Sulawesi?" → list, place "Sulawesi", order_by "date", DESC, limit 1
  - Contoh: "gempa pertama yang tercatat" → list, order_by "date", ASC, limit 1


[AVERAGE] JIKA pertanyaan mengandung "rata-rata", "rerata", "average", atau "mean" → intent "average"
  - WAJIB ekstrak lokasi (place) dan waktu (year/month) jika disebutkan. Contoh: "Rata-rata magnitudo gempa di Sulawesi Tengah 2023" → intent "average", metric "magnitude", place "Sulawesi Tengah", year 2023.
  - Untuk rentang tahun: gunakan min_year/max_year (misal "rata-rata 10 tahun terakhir" → min_year={DATA_TAHUN_TERBARU-9})

[COUNT] JIKA pertanyaan mengandung "berapa jumlah", "berapa banyak", "berapa total", "berapa kali", "seberapa sering" (tanpa meminta detail data):
  - Set intent "count"
  - Jika menyebut "Indonesia" atau tidak ada lokasi spesifik → filters.place = null
  - Contoh: "Berapa total gempa di Indonesia 2023?" → count, place=null, year=2023
  - Contoh: "Berapa jumlah gempa di Aceh 2022?" → count, place="Aceh", year=2022
  - Untuk rentang: "Berapa gempa dalam 5 tahun terakhir?" → count, min_year={DATA_TAHUN_TERBARU-4}

[HARI] Jika user bertanya tentang HARI (misal: "hari apa paling sering gempa") → intent "count", group_by "day_of_week", order_by "count", order_dir "DESC".
[WILAYAH] Jika user bertanya wilayah/provinsi paling sering/aktif → intent "count", group_by "place", order_by "count", order_dir "DESC".

- Singkatan wilayah WAJIB dieja penuh: "jatim"→"Jawa Timur", "jabar"→"Jawa Barat", "jateng"→"Jawa Tengah", "jogja/diy"→"Yogyakarta", "dki"→"Jakarta", "jkt"→"Jakarta", "sby"→"Jawa Timur", "bdg"→"Jawa Barat".
- Jika user menyebut "Indonesia", "indo", atau bertanya secara keseluruhan → filters.place = null.

Kembalikan HANYA JSON."""


# ─── Session Intent Cache (in-memory, per-session) ────────────────────────────
# Menyimpan intent terakhir per sesi untuk inheritance pada pertanyaan pendek.
_last_intent_cache: dict = {}

def _session_key(session_id: str = None, history: list = None) -> str:
    """Buat key unik per sesi. Prioritaskan session_id jika tersedia."""
    if session_id:
        return session_id
    # Fallback: gunakan pesan user pertama dalam history sebagai anchor stabil
    if history:
        for m in history:
            if m.get("role") == "user":
                return str(hash(m.get("content", "")[:80]))
    return "no_session"


def parse_intent(question: str, history: list = []) -> dict:
    # Format history: user messages penuh, assistant sangat ringkas
    history_lines = []
    for m in history[-6:]:
        role = m['role']
        if role == 'user':
            history_lines.append(f"user: {m['content'][:200]}")
        else:
            preview = m['content'][:60].replace('\n', ' ')
            history_lines.append(f"assistant (ringkasan): {preview}...")
    history_str = "\n".join(history_lines)
    user_msg = (
        f"Riwayat percakapan:\n{history_str or '(tidak ada)'}\n\n"
        f"Pertanyaan baru dari user: {question}\n\n"
        f"PERINGATAN: Jika pertanyaan baru menyebut tahun/waktu secara eksplisit "
        f"(seperti '2024', 'tahun lalu', dll), WAJIB gunakan tahun tersebut dan ABAIKAN tahun dari riwayat."
    )
    try:
        text = call_groq(INTENT_SYSTEM, user_msg, max_tokens=400, response_format={"type": "json_object"})
        
        parsed = json.loads(text)
        with open("intent_debug.log", "a", encoding="utf-8") as f:
            f.write(f"SUCCESS\nQ: {question}\nRAW: {text}\nPARSED: {parsed}\n\n")
        return parsed
    except Exception as e:
        with open("intent_debug.log", "a", encoding="utf-8") as f:
            f.write(f"ERROR: {e}\nQ: {question}\nRAW: {text if 'text' in locals() else 'None'}\n\n")
        print(f"[PARSE INTENT ERROR] {e}")
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
        # Gunakan ILIKE (PostgreSQL) agar case-insensitive tanpa perlu transform nilai;
        # data di DB disimpan Title Case, tapi LLM bisa kirim lowercase/mixed
        where_parts.append("place ILIKE %s")
        params.append(f"%{place_filter}%")
    if filters.get("year"):
        where_parts.append("year = %s")
        params.append(int(filters["year"]))
    # ── Rentang tahun (min_year / max_year) ──────────────────────────────────
    if filters.get("min_year"):
        where_parts.append("year >= %s")
        params.append(int(filters["min_year"]))
    if filters.get("max_year"):
        where_parts.append("year <= %s")
        params.append(int(filters["max_year"]))
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
    elif group_by == "day_of_week":
        select = "SELECT trim(to_char(date::date, 'Day')) AS day_of_week, COUNT(*) AS count, ROUND(AVG(magnitude)::numeric, 2) AS avg_magnitude"
        group = "GROUP BY day_of_week ORDER BY count DESC"
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
        # Support date sebagai order column; fallback chain: order_by → metric → magnitude
        valid_order_cols = {"magnitude", "depth", "date", "year", "month"}
        order_col = order_by if order_by in valid_order_cols else (metric if metric in ("magnitude", "depth") else "magnitude")
        forced_dir = "DESC" if intent_type == "max" else "ASC"
        
        if order_col == "date":
            group = f"ORDER BY date {forced_dir}, time {forced_dir}"
        else:
            group = f"ORDER BY {order_col} {forced_dir}"
        try:
            limit_clause = f"LIMIT {int(limit or 5)}"
        except (ValueError, TypeError):
            limit_clause = "LIMIT 5"
    elif intent_type == "count":
        select = "SELECT COUNT(*) AS total_earthquakes"
        group, limit_clause = "", ""
    elif intent_type == "list":
        select = "SELECT date, place, magnitude, depth, depth_category, time"
        # Gunakan order_by dari LLM intent; fallback ke magnitude jika tidak ada
        list_order_col = order_by if order_by in SAFE_COLUMNS else "magnitude"
        list_order_dir = order_dir if order_dir in SAFE_DIRECTIONS else "DESC"
        
        if list_order_col == "date":
            group = f"ORDER BY date {list_order_dir}, time {list_order_dir}"
        else:
            group = f"ORDER BY {list_order_col} {list_order_dir}"
        try:
            limit_clause = f"LIMIT {int(limit or 10)}"
        except (ValueError, TypeError):
            limit_clause = "LIMIT 10"
    elif intent_type == "trend":
        # Trend tanpa group_by eksplisit: default ke per-tahun
        select = "SELECT year, COUNT(*) AS count, ROUND(AVG(magnitude)::numeric, 2) AS avg_magnitude, MAX(magnitude) AS max_magnitude"
        group = "GROUP BY year ORDER BY year ASC"
        limit_clause = ""
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
    if filters.get("min_magnitude"): filter_strs.append(f"Magnitudo Min: {filters['min_magnitude']}")
    if filters.get("max_magnitude"): filter_strs.append(f"Magnitudo Max: {filters['max_magnitude']}")
    
    lines = []
    if filter_strs:
        lines.append(f"📌 Filter Data: {', '.join(filter_strs)}")
        lines.append("-" * 30)

    if group_by == "year":
        lines.append("📊 Tren gempa per tahun (SEMUA baris, gunakan untuk validasi insight):")
        for row in data:
            lines.append(f"  • {row.get('year')}: {row.get('count')} kejadian | Rata-rata: {row.get('avg_magnitude')} | Max: {row.get('max_magnitude')}")
        # Hitung nilai aktual tertinggi/terendah untuk grounding LLM
        if data:
            max_count_row = max(data, key=lambda r: int(r.get('count', 0)))
            min_count_row = min(data, key=lambda r: int(r.get('count', 0)))
            max_mag_row = max(data, key=lambda r: float(r.get('max_magnitude', 0)))
            lines.append(f"\n📌 FAKTA TERVERIFIKASI (untuk insight):")
            lines.append(f"  → Tahun dengan kejadian TERBANYAK: {max_count_row.get('year')} ({max_count_row.get('count')} kejadian)")
            lines.append(f"  → Tahun dengan kejadian PALING SEDIKIT: {min_count_row.get('year')} ({min_count_row.get('count')} kejadian)")
            lines.append(f"  → Tahun dengan magnitudo MAX tertinggi: {max_mag_row.get('year')} (M{max_mag_row.get('max_magnitude')})")
    elif group_by == "day_of_week":
        lines.append("📅 Tren gempa per hari:")
        for row in data:
            lines.append(f"  • {row.get('day_of_week')}: {row.get('count')} kejadian | Rata-rata M{row.get('avg_magnitude')}")
    elif group_by == "place":
        lines.append("🗺️ Distribusi gempa per provinsi:")
        for i, row in enumerate(data, 1):
            lines.append(f"  {i}. {row.get('place')}: {row.get('count')} kejadian | Rata-rata: {row.get('avg_magnitude')}")
    elif intent_type == "count":
        row = data[0]
        total = row.get('total_earthquakes') or row.get('total') or row.get('count', '?')
        lines.append(f"  • Total gempa: {total}")
    elif intent_type in ("max", "min", "list"):
        lines.append(f"📋 Data Gempa {intent_type.upper()}:")
        for i, row in enumerate(data, 1):
            lines.append(f"  {i}. {row.get('date')} | {row.get('place')} | M{row.get('magnitude')} | {row.get('depth')} km")
    else:
        for i, row in enumerate(data, 1):
            row_str = " | ".join([f"{k}: {v}" for k, v in row.items()])
            lines.append(f"{i}. {row_str}")
            
    return "\n".join(lines)


# ─── 3b. Format Data Perbandingan ────────────────────────────────────────────

def format_comparison_data(results_per_place: list, intent: dict) -> str:
    """
    results_per_place: list of (place_name, db_data) tuples
    Format data dari beberapa lokasi menjadi konteks perbandingan.
    """
    intent_type = intent.get("intent", "general")
    metric = intent.get("metric") or "count"
    filters = intent.get("filters") or {}

    filter_strs = []
    if filters.get("year"): filter_strs.append(f"Tahun: {filters['year']}")
    if filters.get("min_year"): filter_strs.append(f"Dari: {filters['min_year']}")
    if filters.get("max_year"): filter_strs.append(f"Sampai: {filters['max_year']}")
    if filters.get("depth_category"): filter_strs.append(f"Kedalaman: {filters['depth_category']}")

    lines = ["🔀 DATA PERBANDINGAN ANTAR LOKASI"]
    if filter_strs:
        lines.append(f"📌 Filter: {', '.join(filter_strs)}")
    lines.append("-" * 40)

    for place_name, data in results_per_place:
        lines.append(f"\n📍 {place_name}:")
        if not data:
            lines.append("  (tidak ada data)")
            continue
        if intent_type == "count":
            row = data[0]
            lines.append(f"  • Total gempa: {row.get('total_earthquakes', '?')}")
        elif intent_type == "average":
            row = data[0]
            col = metric if metric in ("magnitude", "depth") else "magnitude"
            lines.append(f"  • Rata-rata {col}: {row.get(f'avg_{col}', '?')}")
            lines.append(f"  • Total sample: {row.get('total_earthquakes', '?')}")
        elif intent_type in ("max", "min"):
            row = data[0]
            lines.append(f"  • Magnitudo: M{row.get('magnitude', '?')}")
            lines.append(f"  • Kedalaman: {row.get('depth', '?')} km ({row.get('depth_category', '?')})")
            lines.append(f"  • Tanggal: {row.get('date', '?')}")
        elif intent_type == "list":
            for i, row in enumerate(data[:5], 1):
                lines.append(f"  {i}. M{row.get('magnitude')} | {row.get('date')} | {row.get('depth')} km")
        elif intent_type == "trend":
            for row in data[:5]:
                lines.append(f"  • {row.get('year', row.get('month'))}: {row.get('count')} kejadian")
            if len(data) > 5:
                lines.append(f"  ... (+{len(data)-5} baris lagi)")
        else:
            row = data[0]
            row_str = " | ".join([f"{k}: {v}" for k, v in row.items()])
            lines.append(f"  {row_str}")

    return "\n".join(lines)


# ─── 4. Generate Response via Groq ───────────────────────────────────────────

ANSWER_SYSTEM = """Kamu adalah asisten ahli seismologi Indonesia yang ramah.
TUGAS UTAMA: Jawablah pertanyaan user dengan panduan berikut:
1. Jika pertanyaan berkaitan dengan data (angka, statistik, lokasi, tanggal), gunakan HANYA data yang diberikan sebagai sumber informasimu. JANGAN sebutkan kata "database" sama sekali di jawabanmu. Jangan berhalusinasi angka.
2. Jika pertanyaan bersifat UMUM/EDUKASI (misal: "Apa itu gempa?", "Tips keselamatan"), gunakan pengetahuanmu sebagai ahli seismologi untuk menjawab secara jelas dan ramah.
3. JIKA data mencakup tanggal dan lokasi, sebutkan informasi tersebut KECUALI nama hari (Senin, Selasa, dst). JANGAN sebutkan nama hari dari tanggal kecuali user secara eksplisit bertanya tentang hari/waktu kejadian.
4. Jika data kosong padahal user meminta data statistik, katakan dengan sopan bahwa informasi tersebut belum tersedia.
5. JIKA user bertanya tentang kota spesifik (misal: Surabaya) tetapi data yang tersedia adalah tingkat Provinsi, LANGSUNG berikan data provinsi tersebut dengan pengantar yang percaya diri.
6. PENTING: Terjemahkan nama hari atau istilah bahasa Inggris yang ada di data ke bahasa Indonesia (misal: "Sunday" -> "Minggu").
7. EDUKASI SEISMOLOGI: Jika membahas besaran gempa, edukasi user secara singkat bahwa Magnitudo Momen (Mw) adalah standar modern yang lebih akurat dibandingkan Skala Richter.
8. STRUKTUR RESPONS WAJIB (untuk pertanyaan berbasis data):
   a. PEMBUKA (KONDISIONAL):
      - Jika Riwayat percakapan KOSONG / bertanda '(percakapan baru)': awali dengan "Halo! Berdasarkan data seismisitas yang tercatat [sebutkan konteks filter jika ada]:"
      - Jika Riwayat percakapan SUDAH ADA: LANGSUNG ke kalimat framing TANPA "Halo!". Contoh: "Berdasarkan catatan seismik untuk wilayah Aceh:" atau "Oke, berikut datanya:"
   b. DATA UTAMA: Sajikan data dengan label jelas.
      - Untuk statistik tunggal (avg/count): gunakan format "**Label:** Nilai" per baris.
      - Untuk data multi-baris (list/max/tren/distribusi): WAJIB gunakan tabel Markdown. JIKA data lebih dari 10 baris, tampilkan MAKSIMAL 10 baris yang paling relevan/tertinggi saja agar respons cepat.
   c. INSIGHT: Setelah data, SELALU tambahkan satu seksi insight:
      - "💡 Insight Singkat:" untuk intent avg/count — berisi 1-2 kalimat interpretasi.
      - "🔍 Insight Menarik:" untuk intent list/max/min/trend — berisi 2-3 poin bullet.
      KRITIS untuk insight tren: Klaim seperti "tertinggi", "terbesar", "paling banyak" WAJIB diverifikasi dari bagian 'insight' di data. JANGAN menyebut tahun berjalan (⚠️[data belum lengkap]) sebagai rekor tertinggi/terendah. Jika ada tahun dengan label ⚠️[data belum lengkap], sebutkan secara eksplisit bahwa data tersebut masih berjalan/belum lengkap.
      Gunakan kategori berikut untuk interpretasi:
      Magnitudo: <3.0=Mikro(tak terasa), 3.0-3.9=Kecil, 4.0-4.9=Ringan(mulai terasa), 5.0-5.9=Sedang(signifikan), 6.0-6.9=Kuat(berpotensi merusak), 7.0-7.9=Besar, >=8.0=Sangat Besar
      Kedalaman: Dangkal(<60km)=potensi daya rusak tinggi di permukaan, Menengah(60-300km)=berkurang, Dalam(>300km)=jarang merusak
   d. PENUTUP: Akhiri dengan "Ada lagi yang bisa saya bantu?" atau variasi natural lainnya.
9. JANGAN mengulang data mentah di seksi Insight. Insight harus berisi INTERPRETASI dan makna, bukan restatement angka.
10. OUT OF DOMAIN: JIKA pertanyaan SAMA SEKALI TIDAK ADA HUBUNGANNYA dengan gempa bumi, seismologi, atau mitigasi bencana (misal: resep masakan, percintaan, coding, kekerasan, dll), ABAIKAN data yang ada dan tolak dengan sopan. Katakan bahwa kamu adalah asisten ahli seismologi dan hanya bisa menjawab seputar gempa.
11. DATA TIDAK RELEVAN: JIKA pertanyaan jelas dan spesifik tentang gempa, TETAPI data yang diberikan memiliki struktur yang BENAR-BENAR BERBEDA (misal user bertanya tentang wilayah tapi data berisi hari-hari dalam seminggu, atau user bertanya total tapi data berisi list detail), JANGAN menjawab dengan data itu. Katakan: "Maaf, tampaknya ada kendala dalam mencari informasi tersebut. Coba ulangi pertanyaannya?" PENTING: JANGAN terapkan aturan ini jika pertanyaan pendek/ambigu — pertanyaan pendek seperti 'jika 2021?' adalah kelanjutan sesi, jawab saja berdasarkan data yang ada.
12. FORMAT ANGKA: Gunakan TITIK (.) sebagai pemisah desimal, BUKAN koma. Contoh: tulis "41.561 km" bukan "41,561 km".
13. LARANGAN KRITIS — JANGAN TOLAK DATA YANG SUDAH ADA: Jika bagian 'Data' sudah berisi angka/baris nyata (bukan kosong), DILARANG KERAS mengatakan 'saya tidak memiliki data', 'data tidak tersedia', 'saya hanya punya data tahun X', atau kalimat serupa. Konteks Query di bagian atas prompt menunjukkan tahun/filter yang SUDAH dieksekusi ke database. Percayai data tersebut dan sajikan apa adanya.
14. KONTEKS QUERY ADALAH FINAL: Bagian 'Konteks Query' di prompt menunjukkan parameter pencarian yang sudah digunakan. Gunakan informasi itu sebagai pembuka jawaban (misal 'Berdasarkan data tahun 2026:'). JANGAN menggantinya dengan tahun atau filter lain dari riwayat percakapan.
"""

CORRECTION_SYSTEM = """Kamu adalah asisten ahli seismologi yang sangat teliti.
PERINGATAN: Jawaban sebelumnya mungkin salah atau kurang tepat.
TUGAS: Gunakan Data yang benar di bawah ini untuk memberikan jawaban yang akurat kepada user.
- Jangan mengulangi kesalahan sebelumnya.
- Berikan informasi yang BENAR secara naratif dan natural. JANGAN sebutkan kata "database" atau "data database".
- Gunakan HANYA informasi yang secara eksplisit ada di Data yang diberikan untuk bagian angka/statistik.
- Terjemahkan istilah bahasa Inggris (misal "Sunday") ke bahasa user (misal "Minggu")."""


def generate_response(question: str, context: str, history: list, intent: dict = None, system_prompt: str = ANSWER_SYSTEM) -> str:
    # Bangun query context eksplisit dari intent agar LLM tidak terkecoh riwayat
    query_ctx_parts = []
    if intent:
        filters = intent.get("filters") or {}
        if filters.get("year"):       query_ctx_parts.append(f"Tahun: {filters['year']}")
        if filters.get("min_year"):   query_ctx_parts.append(f"Dari tahun: {filters['min_year']}")
        if filters.get("max_year"):   query_ctx_parts.append(f"Sampai tahun: {filters['max_year']}")
        if filters.get("place"):      query_ctx_parts.append(f"Wilayah: {filters['place']}")
        if filters.get("places"):     query_ctx_parts.append(f"Perbandingan: {' vs '.join(filters['places'])}")
        if filters.get("month"):      query_ctx_parts.append(f"Bulan: {filters['month']}")
        if intent.get("intent"):      query_ctx_parts.append(f"Tipe query: {intent['intent']}")
    query_ctx = ", ".join(query_ctx_parts) if query_ctx_parts else "(tidak ada filter spesifik — data keseluruhan)"

    # Format history untuk answer generator — ringkas agar tidak kontaminasi jawaban
    history_lines = []
    for m in history[-4:]:  # Batas 4 pesan terakhir
        role = m['role'].title()
        # Potong pendek untuk mencegah konteks lama mendominasi
        preview = m['content'][:120].replace('\n', ' ')
        history_lines.append(f"{role}: {preview}..." if len(m['content']) > 120 else f"{role}: {m['content']}")
    history_str = "\n".join(history_lines)

    # Prompt grounding: query context ditempatkan PERTAMA agar menjadi anchor utama LLM
    user_msg = (
        f"=== KONTEKS QUERY (PARAMETER YANG SUDAH DIEKSEKUSI KE DATABASE) ===\n"
        f"{query_ctx}\n"
        f"=== AKHIR KONTEKS QUERY ===\n\n"
        f"PENTING: Gunakan HANYA bagian 'Data' di bawah sebagai sumber angka/fakta. "
        f"JANGAN mengambil angka dari riwayat percakapan. "
        f"JANGAN mengatakan data tidak ada jika bagian Data sudah berisi baris nyata.\n\n"
        f"Riwayat percakapan (hanya untuk konteks gaya bicara, BUKAN sumber data):\n"
        f"{history_str or '(percakapan baru)'}\n\n"
        f"Data (SATU-SATUNYA sumber kebenaran):\n{context}\n\n"
        f"Pertanyaan User: {question}\n\nJawaban:"
    )
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
    intent_type = intent.get("intent", "general")
    
    # Hanya validasi metric utama yang dicari user
    if intent_type == "average":
        critical_keywords = {f"avg_{metric.lower()}", "avg"}
    elif intent_type == "count":
        critical_keywords = {"total", "count"}
    else:
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

    # Untuk query yang mengembalikan banyak baris (trend, distribusi, list), 
    # LLM mungkin merangkum/memotong tabel (max 10 baris). 
    # Validasi hanya 3 baris pertama agar tidak memicu correction loop yang lambat.
    if len(db_data) > 3:
        db_numbers = extract_key_numbers_from_db(db_data[:3], intent)

    if not db_numbers:
        return True, llm_answer

    # Cek apakah setiap angka penting ada dalam jawaban LLM
    mismatched = [n for n in db_numbers if not any(abs(ln - n) <= NUMERIC_TOLERANCE for ln in llm_numbers)]

    if mismatched:
        print(f"[VALIDATION] Mismatch detected (DB expected {db_numbers}, but LLM said {llm_numbers}). Correcting...")
        db_context = format_data(db_data, intent)
        # Panggil Groq lagi dengan prompt koreksi
        corrected_answer = generate_response(question, db_context, history, intent=intent, system_prompt=CORRECTION_SYSTEM)
        return False, corrected_answer

    return True, llm_answer


# ─── 7. Main Entry Point ─────────────────────────────────────────────────────

# Kata-kata yang menandakan pertanyaan pendek adalah kelanjutan / variasi tahun saja
_SHORT_Q_MARKERS = re.compile(
    r'^(jika|kalau|kalo|bagaimana|gimana|untuk|di|pada|tahun|year|dan|what about|how about)[\s\?]*'
    r'(19\d{2}|20\d{2})[\s\?]*$',
    re.IGNORECASE
)

def process_query(question: str, history: list = [], session_id: str = None) -> dict:
    sess_key = _session_key(session_id=session_id, history=history)
    last_intent = _last_intent_cache.get(sess_key)

    intent = parse_intent(question, history)
    intent_type = intent.get("intent", "general")
    print(f"[INTENT] {json.dumps(intent)}")

    # ── Normalisasi: ubah string "null" dari LLM → None Python ───────────────
    for field in ("group_by", "order_by", "order_dir", "metric"):
        if intent.get(field) in ("null", "none", "", "Null"):
            intent[field] = None

    # ── Pastikan filters selalu dict ──────────────────────────────────────────
    if "filters" not in intent or intent["filters"] is None:
        intent["filters"] = {}
    filters = intent["filters"]

    # ── Post-processing 1: ekstrak tahun eksplisit dari teks pertanyaan (REGEX) ─
    q_lower = question.lower()
    years_in_question = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', question)]
    if years_in_question:
        if len(years_in_question) >= 2:
            min_y, max_y = min(years_in_question), max(years_in_question)
            filters["min_year"] = min_y
            filters["max_year"] = max_y
            filters.pop("year", None)
            print(f"[POST-PROC REGEX] Rentang tahun: {min_y}–{max_y}")
        else:
            explicit_year = years_in_question[0]
            filters["year"] = explicit_year
            filters.pop("min_year", None)
            filters.pop("max_year", None)
            print(f"[POST-PROC REGEX] Tahun eksplisit: {explicit_year}")

    # ── Post-processing 2: inheritance struktural dari last_intent ────────────
    # Jika pertanyaan PENDEK (hanya ganti tahun), inherit group_by/order_by/limit
    # dari intent sesi sebelumnya agar konteks terjaga tanpa bergantung LLM.
    is_short_year_swap = bool(_SHORT_Q_MARKERS.match(question.strip()))
    # Heuristik tambahan: pendek + ada tahun → kemungkinan besar year-swap
    # KECUALI: mengandung frasa bermakna sendiri (terbaru, terakhir, terbesar, dll)
    _NO_INHERIT_PATTERNS = re.compile(
        r'\b(terbaru|terakhir|terkini|terbesar|terkuat|terkecil|paling|pertama|tertua|terlama|tertinggi|terendah|terdalam|terdangkal)\b',
        re.IGNORECASE
    )
    if not is_short_year_swap and len(question.strip()) <= 30 and years_in_question:
        if not _NO_INHERIT_PATTERNS.search(question):
            is_short_year_swap = True

    if is_short_year_swap and last_intent:
        print(f"[POST-PROC INHERIT] Pertanyaan pendek terdeteksi. Mewarisi struktur dari last_intent.")
        # Warisi field struktural jika LLM tidak mengisinya dengan benar
        for field in ("group_by", "order_by", "order_dir", "limit"):
            if not intent.get(field) and last_intent.get(field):
                intent[field] = last_intent[field]
                print(f"  ↳ Inherited {field} = {last_intent[field]}")
        # Warisi filter non-temporal (place, depth_category, dll) dari last_intent
        last_filters = last_intent.get("filters") or {}
        for fk in ("place", "depth_category", "min_magnitude", "max_magnitude"):
            if not filters.get(fk) and last_filters.get(fk):
                filters[fk] = last_filters[fk]
                print(f"  ↳ Inherited filter.{fk} = {last_filters[fk]}")
        # Jangan warisi filter temporal (year/min_year/max_year) — regex sudah handle

    # ── Post-processing 3: deteksi "data terbaru" → paksa filter year + order ──
    FRASA_TERBARU = ["data terbaru", "data paling baru", "paling terkini"]
    has_temporal = any(filters.get(k) for k in ["year", "min_year", "max_year"])
    if any(frasa in q_lower for frasa in FRASA_TERBARU) and not has_temporal:
        filters["year"] = DATA_TAHUN_TERBARU
        # Pastikan intent dan urutan juga benar untuk frasa 'data terbaru'
        if intent.get("intent") not in ("list", "max", "min"):
            intent["intent"] = "list"
            intent_type = "list"
        intent["order_by"] = "date"
        intent["order_dir"] = "DESC"
        if not intent.get("limit"):
            intent["limit"] = 10
        print(f"[POST-PROC] Frasa 'data terbaru' → year={DATA_TAHUN_TERBARU}, intent=list, order_by=date")

    # ── Greeting / chit-chat detection (bypass DB) ───────────────────────────
    # Pertanyaan berupa sapaan tidak boleh memicu DB query atau kontaminasi history.
    _GREETING_PATTERN = re.compile(
        r'^\s*(halo|hai|hi|hello|hey|selamat\s+(pagi|siang|sore|malam)|'
        r'permisi|terima\s*kasih|makasih|thanks?|oke|ok|siap|ya|mantap|'
        r'bagus|good|great|keren|boleh|lanjut)\s*[\!\.\?]*\s*$',
        re.IGNORECASE
    )
    if _GREETING_PATTERN.match(question):
        print("[MODE] Greeting/chit-chat — bypass DB")
        greeting_ctx = (
            "User mengirim sapaan atau respon singkat. "
            "Balas dengan ramah dan tanyakan apa yang bisa dibantu seputar gempa bumi Indonesia. "
            "JANGAN mengungkit topik percakapan sebelumnya."
        )
        answer = generate_response(question, greeting_ctx, [], intent=None)
        return {
            "answer": answer,
            "validated": True,
            "source": "llm-knowledge",
            "method": "greeting",
            "sql_query": None,
            "data_count": 0,
            "fetched_data": [],
        }

    # Knowledge mode: bypass database
    if intent_type == "knowledge":
        print("[MODE] Knowledge/Educational")
        answer = generate_response(question, "(Pertanyaan edukasi umum, gunakan pengetahuan internal)", history, intent=None)
        return {
            "answer": answer,
            "validated": True,
            "source": "llm-knowledge",
            "method": "direct-answer",
            "sql_query": None,
            "data_count": 0,
            "fetched_data": [],
        }

    # ── COMPARISON MODE: multi-place query ────────────────────────────────────
    places_list = filters.get("places")
    if isinstance(places_list, list) and len(places_list) >= 2:
        print(f"[MODE] Comparison — {len(places_list)} lokasi: {places_list}")
        results_per_place = []
        sql_queries = []

        for place_name in places_list:
            # Buat salinan intent dengan filter place tunggal untuk tiap lokasi
            intent_copy = json.loads(json.dumps(intent))  # deep copy
            intent_copy["filters"]["place"] = place_name
            intent_copy["filters"]["places"] = None
            try:
                sql_single, params_single = build_sql(intent_copy)
                sql_queries.append(f"{place_name}: {sql_single} | PARAMS: {params_single}")
                print(f"  [SQL-{place_name}][Intent: {intent_type}] {sql_single} | {params_single}")
            except Exception as e:
                sql_single, params_single = "SELECT COUNT(*) FROM earthquakes WHERE place ILIKE %s", [f"%{place_name}%"]
                print(f"  [SQL BUILD ERROR-{place_name}] {e}")

            data_single = execute_query(sql_single, params_single)
            print(f"  [DATA-{place_name}] {len(data_single)} rows")
            results_per_place.append((place_name, data_single))

        total_rows = sum(len(d) for _, d in results_per_place)
        context = format_comparison_data(results_per_place, intent)
        all_db_data = [row for _, data in results_per_place for row in data]

        comparison_question = (
            f"{question}\n\n"
            f"[INSTRUKSI UNTUK LLM: Ini adalah pertanyaan PERBANDINGAN antara {len(places_list)} lokasi. "
            f"Bandingkan data dari masing-masing lokasi secara eksplisit. "
            f"Sebutkan angka untuk tiap lokasi, lalu simpulkan mana yang lebih tinggi/rendah/besar/kecil sesuai pertanyaan. "
            f"Gunakan tabel Markdown untuk menyajikan perbandingan.]"
        )

        raw_answer = generate_response(comparison_question, context, history, intent=intent)
        validated, final_answer = validate_response(comparison_question, raw_answer, all_db_data, intent, history)
        print(f"[VALIDATION] validated={validated}")

        _last_intent_cache[sess_key] = intent
        all_sql = "; ".join(sql_queries)
        return {
            "answer": final_answer,
            "validated": validated,
            "source": "supabase",
            "method": "comparison",
            "sql_query": all_sql,
            "data_count": total_rows,
            "fetched_data": all_db_data,
        }

    # ── Single-place / general mode ────────────────────────────────────────────
    try:
        sql, params = build_sql(intent)
        print(f"[SQL][Intent: {intent_type}] {sql} | PARAMS: {params}")
    except Exception as e:
        print(f"[SQL BUILD ERROR] {e}")
        sql, params = "SELECT COUNT(*) FROM earthquakes", []

    db_data = execute_query(sql, params)
    print(f"[DATA] Returned {len(db_data)} rows")

    context = format_data(db_data, intent)

    # ── Rekonstruksi pertanyaan deskriptif untuk short year-swap ─────────────
    # "jika 2021?" → LLM tidak tahu itu kelanjutan. Beri konteks lebih jelas.
    effective_question = question
    if is_short_year_swap and last_intent:
        # Bangun kembali pertanyaan dari intent: "[topik] [lokasi] [tahun]"
        topic_map = {
            ("count", "place"): "provinsi dengan gempa terbanyak",
            ("count", "year"): "jumlah gempa per tahun",
            ("count", "month"): "jumlah gempa per bulan",
            ("average", None): "rata-rata gempa",
            ("max", None): "gempa terbesar",
            ("min", None): "gempa terkecil",
            ("trend", "year"): "tren gempa per tahun",
            ("list", None): "daftar gempa",
        }
        itype = intent.get("intent", "general")
        grpby = intent.get("group_by")
        topic = topic_map.get((itype, grpby)) or topic_map.get((itype, None)) or "data gempa"
        year_part = f"tahun {filters['year']}" if filters.get("year") else ""
        place_part = f"di {filters['place']}" if filters.get("place") else ""
        effective_question = f"{topic} {place_part} {year_part}".strip()
        print(f"[RECONSTRUCT] '{question}' → '{effective_question}'")

    raw_answer = generate_response(effective_question, context, history, intent=intent)

    # Validation & Potential Correction
    validated, final_answer = validate_response(effective_question, raw_answer, db_data, intent, history)
    print(f"[VALIDATION] validated={validated}")

    # ── Simpan intent ke cache untuk inheritance sesi berikutnya ─────────────
    _last_intent_cache[sess_key] = intent
    print(f"[CACHE] Saved intent for sess_key={sess_key[:8]}... → group_by={intent.get('group_by')}, year={intent.get('filters', {}).get('year')}")

    return {
        "answer": final_answer,
        "validated": validated,
        "source": "supabase",
        "method": "sql-comparison",
        "sql_query": sql,
        "data_count": len(db_data),
        "fetched_data": db_data,
    }
