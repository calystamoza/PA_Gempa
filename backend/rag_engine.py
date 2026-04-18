import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv
from database import execute_query

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-flash-latest")

# ─── Kolom aman untuk ORDER BY (whitelist anti SQL injection) ─────────────────
SAFE_COLUMNS = {"magnitude", "depth", "year", "month", "count", "avg_magnitude"}
SAFE_DIRECTIONS = {"ASC", "DESC"}


# ─── 1. Parse Intent via Gemini ───────────────────────────────────────────────

INTENT_PROMPT = """Kamu adalah parser intent untuk chatbot data gempa bumi Indonesia.
Tugasmu: konversi pertanyaan user ke JSON yang mendeskripsikan query database.

Schema database:
- Tabel: earthquakes
- Kolom:
  * place        : TEXT (nama provinsi, contoh: 'Jawa Barat', 'Sulawesi Tengah')
  * year         : INTEGER (tahun kejadian, contoh: 2020, 2023)
  * month        : INTEGER (angka bulan 1-12)
  * month_name   : TEXT (nama bulan dalam bahasa Inggris)
  * magnitude    : FLOAT (kekuatan gempa dalam skala Richter)
  * depth        : FLOAT (kedalaman dalam km)
  * depth_category: TEXT ('dangkal', 'menengah', 'dalam')
  * latitude, longitude: FLOAT
  * date, time   : TEXT

Format JSON yang HARUS dikembalikan:
{{
  "intent": "count|average|max|min|list|trend|general",
  "metric": "magnitude|depth|count|null",
  "filters": {{
    "place": null,
    "year": null,
    "month": null,
    "depth_category": null,
    "min_magnitude": null,
    "max_magnitude": null
  }},
  "group_by": "year|month|place|null",
  "order_by": "magnitude|depth|year|count|null",
  "order_dir": "DESC|ASC",
  "limit": 10
}}

Aturan:
- Jika user tanya "tren" / "per tahun" / "setiap tahun" → group_by = "year"
- Jika user tanya "per bulan" / "setiap bulan" → group_by = "month"
- Jika user tanya "wilayah mana" / "provinsi mana" → group_by = "place"
- Jika user tanya "berapa banyak" / "jumlah" → intent = "count"
- Jika user tanya "rata-rata" / "average" → intent = "average"
- Jika user tanya "terkuat" / "terbesar" / "tertinggi" → intent = "max"
- Jika user tanya "terkecil" / "terdangkal" → intent = "min"
- Jika user tanya data spesifik / detail → intent = "list"
- Jika pertanyaan umum tentang gempa → intent = "general"

Contoh:
Q: "berapa rata-rata magnitudo di Jawa Barat tahun 2024?"
A: {{"intent":"average","metric":"magnitude","filters":{{"place":"Jawa Barat","year":2024}},"group_by":null,"order_by":null,"order_dir":"DESC","limit":10}}

Q: "wilayah mana yang paling sering gempa?"
A: {{"intent":"count","metric":"count","filters":{{}},"group_by":"place","order_by":"count","order_dir":"DESC","limit":10}}

Q: "tren gempa per tahun"
A: {{"intent":"trend","metric":"count","filters":{{}},"group_by":"year","order_by":"year","order_dir":"ASC","limit":null}}

Q: "gempa terkuat yang pernah terjadi?"
A: {{"intent":"max","metric":"magnitude","filters":{{}},"group_by":null,"order_by":"magnitude","order_dir":"DESC","limit":5}}

Riwayat percakapan (untuk konteks):
{history}

Pertanyaan user: {question}

Kembalikan HANYA JSON, tanpa penjelasan, tanpa markdown."""


def parse_intent(question: str, history: list = []) -> dict:
    history_str = "\n".join(
        [f"{m['role']}: {m['content'][:100]}" for m in history[-6:]]
    )
    prompt = INTENT_PROMPT.format(history=history_str or "(tidak ada)", question=question)

    try:
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        # Bersihkan markdown code block jika ada
        text = re.sub(r"```(?:json)?", "", text).strip()
        return json.loads(text)
    except Exception as e:
        print(f"[INTENT PARSE ERROR] {e}")
        return {
            "intent": "general",
            "metric": None,
            "filters": {},
            "group_by": None,
            "order_by": None,
            "order_dir": "DESC",
            "limit": 10,
        }


# ─── 2. Build SQL dari Intent ─────────────────────────────────────────────────

def build_sql(intent: dict) -> tuple[str, list]:
    filters = intent.get("filters") or {}
    intent_type = intent.get("intent", "general")
    metric = intent.get("metric") or "count"
    group_by = intent.get("group_by")
    order_by = intent.get("order_by")
    order_dir = intent.get("order_dir", "DESC")
    limit = intent.get("limit", 10)

    # Sanitasi
    if order_by not in SAFE_COLUMNS:
        order_by = None
    if order_dir not in SAFE_DIRECTIONS:
        order_dir = "DESC"

    # WHERE clause
    where_parts, params = [], []

    if filters.get("place"):
        where_parts.append("LOWER(place) LIKE %s")
        params.append(f"%{filters['place'].lower()}%")
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

    # SELECT + GROUP BY
    if group_by == "year":
        select = "SELECT year, COUNT(*) AS count, ROUND(AVG(magnitude)::numeric, 2) AS avg_magnitude, MAX(magnitude) AS max_magnitude, MIN(magnitude) AS min_magnitude"
        group = "GROUP BY year ORDER BY year ASC"
        limit_clause = ""

    elif group_by == "month":
        select = "SELECT month, month_name, COUNT(*) AS count, ROUND(AVG(magnitude)::numeric, 2) AS avg_magnitude, MAX(magnitude) AS max_magnitude"
        group = "GROUP BY month, month_name ORDER BY month ASC"
        limit_clause = ""

    elif group_by == "place":
        select = "SELECT place, COUNT(*) AS count, ROUND(AVG(magnitude)::numeric, 2) AS avg_magnitude, MAX(magnitude) AS max_magnitude"
        group = f"GROUP BY place ORDER BY count {order_dir}"
        limit_clause = f"LIMIT {int(limit)}" if limit else "LIMIT 15"

    elif intent_type == "average":
        col = metric if metric in ("magnitude", "depth") else "magnitude"
        select = f"SELECT ROUND(AVG({col})::numeric, 3) AS avg_{col}, COUNT(*) AS total_earthquakes"
        group = ""
        limit_clause = ""

    elif intent_type in ("max", "min"):
        col = metric if metric in ("magnitude", "depth") else "magnitude"
        select = f"SELECT place, date, magnitude, depth, depth_category, time"
        order_col = order_by or col
        forced_dir = "DESC" if intent_type == "max" else "ASC"
        group = f"ORDER BY {order_col} {forced_dir}"
        limit_clause = f"LIMIT {int(limit)}" if limit else "LIMIT 5"

    elif intent_type == "count":
        select = "SELECT COUNT(*) AS total_earthquakes"
        group = ""
        limit_clause = ""

    elif intent_type == "list":
        select = "SELECT date, place, magnitude, depth, depth_category, time, latitude, longitude"
        order_col = order_by or "magnitude"
        group = f"ORDER BY {order_col} {order_dir}"
        limit_clause = f"LIMIT {int(limit)}" if limit else "LIMIT 10"

    else:  # general
        select = "SELECT COUNT(*) AS total, ROUND(AVG(magnitude)::numeric, 2) AS avg_magnitude, MAX(magnitude) AS max_magnitude, MIN(magnitude) AS min_magnitude, ROUND(AVG(depth)::numeric, 2) AS avg_depth"
        group = ""
        limit_clause = ""

    sql = f"{select} FROM earthquakes {where} {group} {limit_clause}".strip()
    return sql, params


# ─── 3. Format Data sebagai Context ──────────────────────────────────────────

def format_data(data: list, intent: dict) -> str:
    if not data:
        return "Tidak ada data yang ditemukan untuk kriteria ini."

    intent_type = intent.get("intent", "general")
    group_by = intent.get("group_by")
    lines = []

    if group_by == "year":
        lines.append("📊 Tren gempa per tahun:")
        for row in data:
            lines.append(
                f"  • {row.get('year')}: {row.get('count')} kejadian | "
                f"Rata-rata magnitudo: {row.get('avg_magnitude')} | "
                f"Tertinggi: {row.get('max_magnitude')}"
            )

    elif group_by == "month":
        lines.append("📅 Distribusi gempa per bulan:")
        for row in data:
            lines.append(
                f"  • {row.get('month_name')} (Bulan {row.get('month')}): "
                f"{row.get('count')} kejadian | Rata-rata: {row.get('avg_magnitude')}"
            )

    elif group_by == "place":
        lines.append("🗺️ Distribusi gempa per provinsi:")
        for i, row in enumerate(data, 1):
            lines.append(
                f"  {i}. {row.get('place')}: {row.get('count')} kejadian | "
                f"Rata-rata magnitudo: {row.get('avg_magnitude')} | "
                f"Tertinggi: {row.get('max_magnitude')}"
            )

    elif intent_type == "average":
        row = data[0]
        for k, v in row.items():
            lines.append(f"  • {k}: {v}")

    elif intent_type in ("max", "min"):
        lines.append(f"🗂️ Data gempa {intent_type.upper()} ({len(data)} hasil):")
        for i, row in enumerate(data, 1):
            lines.append(
                f"  {i}. Tanggal: {row.get('date')} | Lokasi: {row.get('place')} | "
                f"Magnitudo: {row.get('magnitude')} | Kedalaman: {row.get('depth')} km "
                f"({row.get('depth_category')})"
            )

    elif intent_type == "list":
        lines.append(f"📋 Daftar gempa ({len(data)} hasil):")
        for i, row in enumerate(data, 1):
            lines.append(
                f"  {i}. [{row.get('date')}] {row.get('place')} — "
                f"M{row.get('magnitude')} | Kedalaman: {row.get('depth')} km "
                f"({row.get('depth_category')})"
            )

    else:  # general
        row = data[0]
        lines.append("📈 Statistik umum:")
        for k, v in row.items():
            lines.append(f"  • {k}: {v}")

    return "\n".join(lines)


# ─── 4. Generate Response via Gemini ─────────────────────────────────────────

def generate_response(question: str, context: str, history: list) -> str:
    history_str = "\n".join(
        [f"{m['role'].title()}: {m['content'][:200]}" for m in history[-6:]]
    )

    prompt = f"""Kamu adalah asisten ahli seismologi untuk data gempa Indonesia.
Tugasmu: jawab pertanyaan user berdasarkan data yang diberikan secara informatif dan ramah.

Riwayat percakapan:
{history_str or '(percakapan baru)'}

Data dari database:
{context}

Pertanyaan: {question}

Instruksi:
1. Jawab HANYA berdasarkan data di atas, jangan mengarang angka
2. Gunakan bahasa yang sama dengan user (Indonesia/Inggris)
3. Jika data kosong, sampaikan bahwa tidak ada data yang sesuai
4. Berikan insight menarik jika relevan (contoh: dibandingkan rata-rata nasional, dsb)
5. Gunakan format yang rapi dengan bullet points atau tabel teks jika perlu
6. Jangan ulangi pertanyaan user
7. Jawab singkat tapi informatif (maks 300 kata)

Jawaban:"""

    try:
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        return f"Maaf, terjadi error saat memproses jawaban: {str(e)}"


# ─── 5. Main Entry Point ─────────────────────────────────────────────────────

def process_query(question: str, history: list = []) -> dict:
    """Pipeline lengkap: intent → SQL → data → response."""
    # Step 1: Parse intent
    intent = parse_intent(question, history)
    print(f"[INTENT] {json.dumps(intent, ensure_ascii=False)}")

    # Step 2: Build SQL
    try:
        sql, params = build_sql(intent)
        print(f"[SQL] {sql} | PARAMS: {params}")
    except Exception as e:
        print(f"[SQL BUILD ERROR] {e}")
        sql = "SELECT COUNT(*) AS total, ROUND(AVG(magnitude)::numeric,2) AS avg_magnitude FROM earthquakes"
        params = []

    # Step 3: Execute query
    data = execute_query(sql, params)
    print(f"[DATA] Returned {len(data)} rows")

    # Step 4: Format context
    context = format_data(data, intent)

    # Step 5: Generate response
    answer = generate_response(question, context, history)

    return {
        "answer": answer,
        "sql_query": sql,
        "data_count": len(data),
    }
