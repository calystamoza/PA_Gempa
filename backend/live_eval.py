"""
live_eval.py — Evaluasi Live Sistem GempaBot
=============================================
Mengirim pertanyaan ke endpoint /chat yang sedang berjalan,
lalu mengevaluasi:
  1. Intent detection (apakah intent terdeteksi benar?)
  2. SQL generation (apakah SQL query yang dibangkitkan sesuai intent?)
  3. Data returned (apakah data dikembalikan / tidak?)
  4. Answer quality (heuristik: apakah angka penting ada di jawaban?)

Output: laporan CSV + Markdown di folder backend/
"""

import json
import re
import time
import requests
import pandas as pd
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE}/chat"
TIMEOUT = 120  # detik per request (dinaikkan untuk trend/knowledge yang lambat)

# ─── Test Cases ───────────────────────────────────────────────────────────────
# Format: (pertanyaan, expected_intent, difficulty, catatan_evaluator)
# Distribusi: count(5), average(5), max(5), min(5), list(5), trend(5), knowledge(5) = 35 total
TEST_CASES = [
    # ── COUNT (5) ──────────────────────────────────────────────────────────────
    (
        "Berapa total gempa yang terjadi di Indonesia sepanjang tahun 2023?",
        "count", "simple",
        "count, place=null, year=2023"
    ),
    (
        "Berapa jumlah gempa yang terjadi di Aceh pada tahun 2022?",
        "count", "simple",
        "count, place='aceh', year=2022"
    ),
    (
        "Berapa jumlah gempa dangkal yang pernah terjadi di Maluku?",
        "count", "medium",
        "count, place LIKE '%maluku%', depth_category='dangkal'"
    ),
    (
        "Berapa banyak gempa yang terjadi dalam 10 tahun terakhir di Indonesia?",
        "count", "medium",
        "count, place=null, min_year=2015 (2024-9)"
    ),
    (
        "Berapa total gempa yang tercatat selama dekade 2010-an?",
        "count", "complex",
        "count, min_year=2010, max_year=2019"
    ),

    # ── AVERAGE (5) ────────────────────────────────────────────────────────────
    (
        "Berapa rata-rata kekuatan gempa di Jawa Barat?",
        "average", "simple",
        "AVG(magnitude), filter place LIKE '%jawa barat%'"
    ),
    (
        "Berapa rata-rata kedalaman gempa di Maluku Utara?",
        "average", "simple",
        "AVG(depth), filter place LIKE '%maluku utara%'"
    ),
    (
        "Berapa rata-rata magnitudo gempa di Sulawesi Tengah tahun 2023?",
        "average", "medium",
        "AVG(magnitude), filter place + year=2023"
    ),
    (
        "Berapa rata-rata kedalaman gempa dalam 5 tahun terakhir di Indonesia?",
        "average", "medium",
        "AVG(depth), min_year=2020 (2024-4), place=null"
    ),
    (
        "Berapa rata-rata magnitudo gempa selama dekade terakhir di Sumatera?",
        "average", "complex",
        "AVG(magnitude), place LIKE '%sumatera%', min_year=2015"
    ),

    # ── MAX (5) ────────────────────────────────────────────────────────────────
    (
        "Kekuatan gempa maksimal di Indonesia berapa?",
        "max", "simple",
        "ORDER BY magnitude DESC LIMIT 5, place=null"
    ),
    (
        "Berapa kekuatan gempa terbesar yang pernah terjadi di Sulawesi Utara?",
        "max", "medium",
        "ORDER BY magnitude DESC, filter place LIKE '%sulawesi utara%'"
    ),
    (
        "Gempa terbesar apa yang pernah tercatat dalam data terbaru kita?",
        "max", "medium",
        "ORDER BY magnitude DESC, year=2024 (data terbaru)"
    ),
    (
        "Gempa terdalam apa yang pernah terjadi di Indonesia?",
        "max", "medium",
        "ORDER BY depth DESC, place=null, metric=depth"
    ),
    (
        "Gempa terakhir apa yang tercatat dalam data kita?",
        "max", "simple",
        "ORDER BY year DESC LIMIT 1 — data terbaru/terakhir"
    ),

    # ── MIN (5) ────────────────────────────────────────────────────────────────
    (
        "Di mana lokasi gempa bumi paling dangkal yang tercatat?",
        "min", "medium",
        "ORDER BY depth ASC LIMIT 1"
    ),
    (
        "Gempa bumi pertama apa yang tercatat dalam data kita?",
        "min", "medium",
        "ORDER BY year ASC LIMIT 1 — data terlama"
    ),
    (
        "Berapa magnitudo terkecil gempa yang pernah tercatat di Jawa Timur?",
        "min", "medium",
        "ORDER BY magnitude ASC LIMIT 1, filter place LIKE '%jawa timur%'"
    ),
    (
        "Apa gempa dengan kekuatan paling kecil yang terjadi di Indonesia?",
        "min", "simple",
        "ORDER BY magnitude ASC LIMIT 1, place=null"
    ),
    (
        "Gempa dengan kedalaman paling kecil yang tercatat di Sulawesi apa?",
        "min", "medium",
        "ORDER BY depth ASC LIMIT 1, filter place LIKE '%sulawesi%'"
    ),

    # ── LIST (5) ───────────────────────────────────────────────────────────────
    (
        "Sebutkan 3 gempa terbesar di Papua",
        "list", "simple",
        "LIMIT 3, ORDER BY magnitude DESC, filter place LIKE '%papua%'"
    ),
    (
        "Tampilkan daftar 5 gempa terkuat di Nusa Tenggara Timur",
        "list", "medium",
        "LIMIT 5, filter place LIKE '%nusa tenggara timur%'"
    ),
    (
        "Berikan daftar gempa yang terjadi di Jawa Barat pada tahun 2022",
        "list", "medium",
        "filter place + year=2022, ORDER BY magnitude DESC"
    ),
    (
        "Tampilkan 10 gempa terbaru yang tercatat dalam data kita",
        "list", "simple",
        "ORDER BY year DESC LIMIT 10, place=null — data terbaru"
    ),
    (
        "Sebutkan 5 gempa paling dangkal yang pernah terjadi di Kalimantan",
        "list", "medium",
        "LIMIT 5, ORDER BY depth ASC, filter place LIKE '%kalimantan%'"
    ),

    # ── TREND (5) ──────────────────────────────────────────────────────────────
    (
        "Bagaimana tren jumlah gempa per tahun di Indonesia?",
        "trend", "complex",
        "GROUP BY year ORDER BY year ASC, place=null"
    ),
    (
        "Apakah jumlah gempa di Indonesia cenderung meningkat atau menurun dari tahun ke tahun?",
        "trend", "complex",
        "GROUP BY year, interpretasi arah tren"
    ),
    (
        "Bagaimana perkembangan frekuensi gempa per bulan di Indonesia?",
        "trend", "complex",
        "GROUP BY month ORDER BY month ASC"
    ),
    (
        "Bagaimana tren jumlah gempa selama 10 tahun terakhir di Sumatera?",
        "trend", "complex",
        "GROUP BY year, min_year=2015, filter place LIKE '%sumatera%'"
    ),
    (
        "Apakah gempa makin sering terjadi di Jawa selama dekade terakhir?",
        "trend", "complex",
        "GROUP BY year, min_year=2015, filter place LIKE '%jawa%'"
    ),

    # ── KNOWLEDGE (5) ──────────────────────────────────────────────────────────
    (
        "Apa itu magnitudo momen?",
        "knowledge", "simple",
        "Tidak perlu SQL, jawaban dari LLM knowledge"
    ),
    (
        "Mengapa Indonesia sering mengalami gempa bumi?",
        "knowledge", "simple",
        "Tidak perlu SQL, edukasi seismologi"
    ),
    (
        "Apa perbedaan antara gempa dangkal, menengah, dan dalam?",
        "knowledge", "simple",
        "Tidak perlu SQL, definisi kategori kedalaman"
    ),
    (
        "Apa yang harus dilakukan untuk menyelamatkan diri saat gempa bumi?",
        "knowledge", "simple",
        "Tidak perlu SQL, tips mitigasi bencana"
    ),
    (
        "Bagaimana cara kerja seismograf?",
        "knowledge", "simple",
        "Tidak perlu SQL, penjelasan alat ukur gempa"
    ),
]

# ─── Intent validation keywords (heuristik SQL) ───────────────────────────────
SQL_INTENT_CHECKS = {
    "count":     lambda sql: sql and "count" in sql.lower(),
    "average":   lambda sql: sql and "avg(" in sql.lower(),
    "max":       lambda sql: sql and "order by" in sql.lower() and "desc" in sql.lower() and "limit" in sql.lower(),
    "min":       lambda sql: sql and "order by" in sql.lower() and "asc" in sql.lower() and "limit" in sql.lower(),
    "list":      lambda sql: sql and "limit" in sql.lower() and "select date" in sql.lower(),
    "trend":     lambda sql: sql and "group by" in sql.lower(),
    "knowledge": lambda sql: sql is None or sql == "",
    "general":   lambda sql: True,
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def call_chat(question: str) -> dict:
    """Panggil endpoint /chat dan kembalikan response dict."""
    payload = {"query": question}
    try:
        resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "CONNECTION_REFUSED — pastikan backend berjalan di port 8000"}
    except requests.exceptions.Timeout:
        return {"error": f"TIMEOUT — server tidak merespons dalam {TIMEOUT}s"}
    except Exception as e:
        return {"error": str(e)}


def evaluate_intent(detected: str, expected: str) -> tuple[bool, str]:
    """Bandingkan intent yang terdeteksi vs ground truth."""
    # Normalisasi: max/min keduanya valid sebagai 'max' atau 'min'
    d = detected.strip().lower()
    e = expected.strip().lower()
    
    # Alias mapping
    alias = {"general": "knowledge", "knowledge": "general"}
    
    if d == e:
        return True, "✅ Intent tepat"
    if alias.get(d) == e:
        return True, f"✅ Intent tepat (alias: '{d}' ≈ '{e}')"
    # max & min saling tertukar?
    if d in ("max", "min") and e in ("max", "min"):
        return False, f"❌ Intent terbalik — terdeteksi '{d}' seharusnya '{e}'"
    return False, f"❌ Intent salah — terdeteksi '{d}' seharusnya '{e}'"


def evaluate_sql(sql: str | None, expected_intent: str, detected_intent: str) -> tuple[bool, str]:
    """Evaluasi SQL berdasarkan intent yang seharusnya."""
    check_fn = SQL_INTENT_CHECKS.get(expected_intent, lambda s: True)
    
    if expected_intent == "knowledge":
        if sql is None or sql == "":
            return True, "✅ Tidak ada SQL (sesuai intent knowledge)"
        else:
            return False, f"❌ SQL tidak seharusnya dibangkitkan untuk intent 'knowledge'"
    
    if sql is None or sql.strip() == "":
        if detected_intent in ("knowledge", "general"):
            return False, f"❌ SQL tidak ada padahal intent adalah '{expected_intent}'"
        return False, "❌ SQL tidak dibangkitkan (mungkin error di pipeline)"
    
    if check_fn(sql):
        return True, f"✅ SQL sesuai pola intent '{expected_intent}'"
    else:
        hints = {
            "count":   "SQL harus mengandung COUNT(*)",
            "average": "SQL harus mengandung AVG()",
            "max":     "SQL harus ORDER BY ... DESC",
            "min":     "SQL harus ORDER BY ... ASC",
            "list":    "SQL harus memiliki LIMIT",
            "trend":   "SQL harus GROUP BY (year/month)",
        }
        return False, f"❌ SQL tidak sesuai pola — {hints.get(expected_intent, 'periksa manual')}"


def evaluate_answer(answer: str, sql: str | None, data_count: int, expected_intent: str) -> tuple[bool, str]:
    """Evaluasi sederhana kualitas jawaban."""
    if not answer:
        return False, "❌ Jawaban kosong"
    if len(answer) < 20:
        return False, f"❌ Jawaban terlalu pendek ({len(answer)} char)"
    
    # Untuk intent knowledge: cek minimal ada teks bermakna
    if expected_intent == "knowledge":
        if any(kw in answer.lower() for kw in ["gempa", "seism", "magnitud", "lempeng", "richter"]):
            return True, "✅ Jawaban mengandung konten seismologi"
        return False, "❌ Jawaban tidak mengandung konten seismologi yang relevan"
    
    # Untuk intent data: cek ada angka
    has_numbers = bool(re.search(r'\d+', answer))
    if not has_numbers and data_count > 0:
        return False, "❌ Data tersedia tapi jawaban tidak mengandung angka"
    
    if data_count == 0 and sql is not None:
        return True, "⚠️ Data tidak ditemukan di DB (mungkin filter terlalu spesifik)"
    
    return True, "✅ Jawaban valid"


# ─── Main Runner ──────────────────────────────────────────────────────────────

def run_live_eval():
    print("=" * 65)
    print("  GempaBot — LIVE EVALUATION")
    print(f"  Target: {CHAT_ENDPOINT}")
    print(f"  Total Test Cases: {len(TEST_CASES)}")
    print("=" * 65)
    
    # Cek koneksi dulu
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5).json()
        print(f"\n✅ Backend terhubung: {health.get('message', 'OK')}\n")
    except Exception:
        print("\n❌ Backend tidak dapat dijangkau! Pastikan 'python main.py' berjalan.\n")
        return

    results = []
    intent_correct = 0
    sql_correct = 0
    answer_correct = 0
    total = len(TEST_CASES)
    
    for idx, (question, expected_intent, difficulty, notes) in enumerate(TEST_CASES, 1):
        print(f"\n[{idx:02d}/{total}] [{difficulty.upper()}] {question[:70]}...")
        print(f"         Expected Intent: {expected_intent}")
        
        start_time = time.time()
        response = call_chat(question)
        elapsed = round(time.time() - start_time, 2)
        
        if "error" in response:
            print(f"         ❌ ERROR: {response['error']}")
            results.append({
                "no": idx,
                "difficulty": difficulty,
                "question": question,
                "expected_intent": expected_intent,
                "detected_intent": "ERROR",
                "intent_ok": False,
                "intent_note": f"❌ {response['error']}",
                "sql_generated": None,
                "sql_ok": False,
                "sql_note": "❌ Tidak dapat mengevaluasi (API error)",
                "data_count": 0,
                "answer_ok": False,
                "answer_note": "❌ Tidak dapat mengevaluasi",
                "answer_preview": "",
                "validated_by_system": False,
                "response_time_s": elapsed,
                "evaluator_notes": notes,
            })
            continue
        
        detected_intent = response.get("method", "?")
        # Ambil intent dari fetched_data atau sql_query analysis
        sql_query = response.get("sql_query") or ""
        data_count = response.get("data_count", 0)
        answer = response.get("answer", "")
        validated = response.get("validated", False)
        source = response.get("source", "?")
        
        # Deteksi intent dari SQL yang dibangkitkan (lebih akurat)
        # Karena API tidak mengembalikan intent JSON langsung, kita infer dari SQL
        inferred_intent = infer_intent_from_sql(sql_query, source)
        
        # Evaluasi
        intent_ok, intent_note = evaluate_intent(inferred_intent, expected_intent)
        sql_ok, sql_note = evaluate_sql(sql_query, expected_intent, inferred_intent)
        ans_ok, ans_note = evaluate_answer(answer, sql_query, data_count, expected_intent)
        
        if intent_ok: intent_correct += 1
        if sql_ok: sql_correct += 1
        if ans_ok: answer_correct += 1
        
        # Print ringkasan baris ini
        intent_icon = "✅" if intent_ok else "❌"
        sql_icon = "✅" if sql_ok else "❌"
        ans_icon = "✅" if ans_ok else "❌"
        print(f"         Detected Intent: {inferred_intent} {intent_icon}")
        print(f"         SQL: {sql_query[:80] if sql_query else 'None'} {sql_icon}")
        print(f"         Data Count: {data_count} | Answer: {ans_icon} | Time: {elapsed}s")
        
        results.append({
            "no": idx,
            "difficulty": difficulty,
            "question": question,
            "expected_intent": expected_intent,
            "detected_intent": inferred_intent,
            "intent_ok": intent_ok,
            "intent_note": intent_note,
            "sql_generated": sql_query,
            "sql_ok": sql_ok,
            "sql_note": sql_note,
            "data_count": data_count,
            "answer_ok": ans_ok,
            "answer_note": ans_note,
            "answer_preview": answer[:200].replace("\n", " "),
            "validated_by_system": validated,
            "response_time_s": elapsed,
            "evaluator_notes": notes,
        })
        
        time.sleep(2)  # Rate limiting Groq — hindari 429 setelah banyak request beruntun
    
    # ─── Simpan CSV ───────────────────────────────────────────────────────────
    df = pd.DataFrame(results)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"live_eval_results_{ts}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n\n📄 CSV tersimpan: {csv_path}")
    
    # ─── Laporan Ringkas ──────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  HASIL EVALUASI LIVE")
    print("=" * 65)
    print(f"  Intent Accuracy  : {intent_correct}/{total} = {intent_correct/total*100:.1f}%")
    print(f"  SQL Accuracy     : {sql_correct}/{total} = {sql_correct/total*100:.1f}%")
    print(f"  Answer Quality   : {answer_correct}/{total} = {answer_correct/total*100:.1f}%")
    print(f"  Avg Response Time: {df['response_time_s'].mean():.2f}s")
    
    # Per-difficulty
    print("\n  Breakdown per Kesulitan:")
    for diff in ["simple", "medium", "complex"]:
        sub = [r for r in results if r["difficulty"] == diff]
        if not sub: continue
        i_ok = sum(1 for r in sub if r["intent_ok"])
        s_ok = sum(1 for r in sub if r["sql_ok"])
        n = len(sub)
        print(f"    {diff.upper():8s}: {n} kasus | Intent {i_ok}/{n} | SQL {s_ok}/{n}")
    
    # Per-intent
    print("\n  Breakdown per Intent:")
    for intent in ["count", "average", "max", "min", "list", "trend", "knowledge"]:
        sub = [r for r in results if r["expected_intent"] == intent]
        if not sub: continue
        i_ok = sum(1 for r in sub if r["intent_ok"])
        s_ok = sum(1 for r in sub if r["sql_ok"])
        n = len(sub)
        print(f"    {intent:12s}: {n} kasus | Intent {i_ok}/{n} | SQL {s_ok}/{n}")
    
    # Kasus yang gagal
    failed = [r for r in results if not r["intent_ok"] or not r["sql_ok"]]
    if failed:
        print(f"\n  ⚠️  Kasus Bermasalah ({len(failed)}):")
        for r in failed:
            print(f"    [{r['no']:02d}] {r['question'][:55]}...")
            if not r["intent_ok"]:
                print(f"         {r['intent_note']}")
            if not r["sql_ok"]:
                print(f"         {r['sql_note']}")
    
    print("=" * 65)
    
    # ─── Buat Markdown Report ─────────────────────────────────────────────────
    md_path = f"live_eval_report_{ts}.md"
    generate_markdown_report(results, intent_correct, sql_correct, answer_correct, total, md_path, ts)
    print(f"📝 Laporan Markdown tersimpan: {md_path}")


def infer_intent_from_sql(sql: str | None, source: str) -> str:
    """
    Infer intent dari SQL yang dibangkitkan oleh build_sql().
    
    Kunci perbedaan yang dibuat oleh build_sql():
      - list    : SELECT date, place, ...       (date duluan, ada LIMIT)
      - max     : SELECT place, date, ...       (place duluan, ORDER BY DESC, LIMIT)
      - min     : SELECT place, date, ...       (place duluan, ORDER BY ASC, LIMIT)
      - count   : SELECT COUNT(*) ...           (tanpa LIMIT)
      - average : SELECT ROUND(AVG(...)) ...    (ada AVG)
      - trend   : ... GROUP BY year/month ...   (ada GROUP BY waktu)
      - knowledge: sql = None                   (tidak ada SQL)
    """
    if source == "llm-knowledge" or sql is None or sql.strip() == "":
        return "knowledge"

    sql_lower = sql.lower().strip()

    # 1. TREND — ada GROUP BY year atau month (paling spesifik)
    if "group by" in sql_lower and ("year" in sql_lower or "month" in sql_lower):
        return "trend"

    # 2. COUNT per place (wilayah aktif)
    if "group by place" in sql_lower:
        return "count"

    # 3. AVERAGE — ada AVG()
    if "avg(" in sql_lower:
        return "average"

    # 4. COUNT murni — ada COUNT(*) tanpa GROUP BY dan tanpa LIMIT
    if "count(*)" in sql_lower and "group by" not in sql_lower and "limit" not in sql_lower:
        return "count"

    # 5. Bedakan LIST vs MAX/MIN berdasarkan urutan kolom di SELECT
    #    build_sql():
    #      list  -> "SELECT date, place, ..."  (date pertama)
    #      max   -> "SELECT place, date, ..."  (place pertama, ORDER BY DESC)
    #      min   -> "SELECT place, date, ..."  (place pertama, ORDER BY ASC)
    if "limit" in sql_lower:
        # Cek urutan kolom SELECT
        select_part = sql_lower.split("from")[0] if "from" in sql_lower else sql_lower
        starts_with_date = "select date" in select_part  # list pattern
        starts_with_place = "select place" in select_part  # max/min pattern

        if starts_with_date:
            return "list"

        if starts_with_place:
            # Bedakan max (DESC) vs min (ASC)
            if "order by" in sql_lower:
                if "asc" in sql_lower:
                    return "min"
                else:  # DESC atau tidak ada arah eksplisit
                    return "max"
            return "list"  # fallback

        # Fallback: ada LIMIT tapi kolom tidak jelas
        if "order by" in sql_lower:
            return "max" if "desc" in sql_lower else "min"
        return "list"

    # 6. COUNT fallback — ada count di query tapi tidak tertangkap atas
    if "count" in sql_lower:
        return "count"

    return "general"


def generate_markdown_report(results, intent_ok, sql_ok, answer_ok, total, path, ts):
    """Generate laporan evaluasi dalam format Markdown."""
    lines = [
        f"# Laporan Evaluasi Live — GempaBot",
        f"",
        f"> Dijalankan pada: {ts[:8][:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}:{ts[13:15]}",
        f"> Target: `http://localhost:8000/chat`",
        f"> Total Test Cases: {total}",
        f"",
        f"## Ringkasan Hasil",
        f"",
        f"| Metrik | Benar | Total | Akurasi |",
        f"|--------|-------|-------|---------|",
        f"| Intent Detection | {intent_ok} | {total} | {intent_ok/total*100:.1f}% |",
        f"| SQL Generation | {sql_ok} | {total} | {sql_ok/total*100:.1f}% |",
        f"| Answer Quality | {answer_ok} | {total} | {answer_ok/total*100:.1f}% |",
        f"",
        f"## Detail Per Test Case",
        f"",
        f"| No | Difficulty | Pertanyaan | Expected | Detected | Intent | SQL | Answer |",
        f"|----|-----------|-----------|---------|---------|--------|-----|--------|",
    ]
    
    for r in results:
        q_short = r["question"][:45] + "..." if len(r["question"]) > 45 else r["question"]
        i_icon = "✅" if r["intent_ok"] else "❌"
        s_icon = "✅" if r["sql_ok"] else "❌"
        a_icon = "✅" if r["answer_ok"] else "❌"
        lines.append(
            f"| {r['no']} | {r['difficulty']} | {q_short} | `{r['expected_intent']}` "
            f"| `{r['detected_intent']}` | {i_icon} | {s_icon} | {a_icon} |"
        )
    
    lines += [
        f"",
        f"## Detail Kegagalan",
        f"",
    ]
    
    failed = [r for r in results if not r["intent_ok"] or not r["sql_ok"]]
    if failed:
        for r in failed:
            lines += [
                f"### [{r['no']:02d}] {r['question']}",
                f"- **Expected Intent:** `{r['expected_intent']}`",
                f"- **Detected Intent:** `{r['detected_intent']}`",
                f"- **Intent Note:** {r['intent_note']}",
                f"- **SQL:** `{r['sql_generated'][:120] if r['sql_generated'] else 'None'}`",
                f"- **SQL Note:** {r['sql_note']}",
                f"- **Evaluator Notes:** {r['evaluator_notes']}",
                f"",
            ]
    else:
        lines.append("*Tidak ada kegagalan yang terdeteksi!*")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_live_eval()
