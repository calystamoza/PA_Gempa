"""
test_comparison.py — Evaluasi Fitur Perbandingan (Comparison) GempaBot
=======================================================================
3 pertanyaan uji untuk fitur comparison (multi-place query).
Output: laporan CSV + Markdown dalam format yang sama dengan live_eval.

Jalankan dari folder backend/:
  python _archive/evaluation/test_comparison.py
"""

import time
import requests
import csv
import sys
from datetime import datetime

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_BASE      = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE}/chat"
TIMEOUT       = 120

# ─── 3 Test Cases Perbandingan ────────────────────────────────────────────────
# Format: (no, pertanyaan, expected_intent, expected_places, expected_sql_pattern,
#          expected_params_desc, difficulty, catatan)
TEST_CASES = [
    (
        1,
        "Apakah Jawa Barat memiliki gempa lebih banyak dibanding Jawa Timur tahun 2024?",
        "count",
        ["Jawa Barat", "Jawa Timur"],
        "SELECT COUNT(*) AS total_earthquakes FROM earthquakes WHERE place ILIKE %s AND year = %s",
        "count, places=['Jawa Barat','Jawa Timur'], year=2024",
        "simple",
        "Perbandingan count 2 provinsi Jawa, filter tahun"
    ),
    (
        2,
        "Berapa rata-rata magnitudo gempa di Maluku vs Sulawesi Utara?",
        "average",
        ["Maluku", "Sulawesi Utara"],
        "SELECT ROUND(AVG(magnitude)::numeric, 3) AS avg_magnitude FROM earthquakes WHERE place ILIKE %s",
        "average, places=['Maluku','Sulawesi Utara'], metric=magnitude",
        "simple",
        "Perbandingan average 2 provinsi timur Indonesia, tanpa filter waktu"
    ),
    (
        3,
        "Gempa terbesar apa yang pernah terjadi di Aceh dibandingkan dengan Papua dan Sulawesi Tengah?",
        "max",
        ["Aceh", "Papua", "Sulawesi Tengah"],
        "SELECT place, date, magnitude, depth FROM earthquakes WHERE place ILIKE %s ORDER BY magnitude DESC LIMIT 1",
        "max, places=['Aceh','Papua','Sulawesi Tengah'], order_by=magnitude DESC",
        "medium",
        "Perbandingan max 3 provinsi berbeda region, 3-way comparison"
    ),
]

# ─── SQL yang diharapkan (per-place) ──────────────────────────────────────────
EXPECTED_SQL = {
    1: "SELECT COUNT(*) AS total_earthquakes FROM earthquakes WHERE place ILIKE %s AND year = %s",
    2: "SELECT ROUND(AVG(magnitude)::numeric, 3) AS avg_magnitude, COUNT(*) AS total_earthquakes FROM earthquakes WHERE place ILIKE %s",
    3: "SELECT place, date, magnitude, depth, depth_category, time FROM earthquakes WHERE place ILIKE %s ORDER BY magnitude DESC LIMIT 1",
}


def send_question(question: str) -> tuple:
    payload = {"query": question, "session_id": None, "user_id": None}
    t_start = time.perf_counter()
    try:
        resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=TIMEOUT)
        elapsed = time.perf_counter() - t_start
        return elapsed, resp.json()
    except Exception as e:
        elapsed = time.perf_counter() - t_start
        return elapsed, {"error": str(e)}


def evaluate_result(no: int, response: dict, expected_places: list) -> dict:
    """Evaluasi apakah response comparison benar."""
    method  = response.get("method", "")
    sql_raw = response.get("sql_query", "") or ""
    answer  = response.get("answer", "")
    data    = response.get("fetched_data", [])
    rows    = response.get("data_count", 0)

    # Cek 1: apakah berjalan dalam comparison mode?
    is_comparison_mode = method == "comparison"

    # Cek 2: apakah semua SQL mengandung pola yang benar?
    expected_sql_pat = EXPECTED_SQL.get(no, "")
    # SQL query berisi semua sub-queries dipisah ";"
    sql_parts = [s.strip() for s in sql_raw.split(";")]
    sql_ok = len(sql_parts) >= len(expected_places)

    # Cek 3: apakah jawaban menyebut semua lokasi?
    places_in_answer = [p for p in expected_places if p.lower() in answer.lower()]
    answer_mentions_all = len(places_in_answer) == len(expected_places)

    # Cek 4: apakah data dikembalikan (setidaknya 1 row per place)?
    data_ok = rows >= len(expected_places)

    # Keseluruhan: benar jika semua cek OK
    overall_ok = is_comparison_mode and sql_ok and answer_mentions_all and data_ok

    return {
        "is_comparison_mode": is_comparison_mode,
        "sql_ok": sql_ok,
        "answer_mentions_all_places": answer_mentions_all,
        "places_found_in_answer": places_in_answer,
        "data_ok": data_ok,
        "data_count": rows,
        "overall": overall_ok,
    }


def run_test():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path  = f"comparison_eval_results_{timestamp}.csv"
    md_path   = f"comparison_eval_report_{timestamp}.md"

    print(f"\n{'='*65}")
    print("  GempaBot — Comparison Feature Test")
    print(f"  Endpoint: {CHAT_ENDPOINT}")
    print(f"{'='*65}\n")

    rows_out = []
    md_rows  = []
    all_ok   = True

    for (no, question, expected_intent, expected_places,
         expected_sql_pat, params_desc, difficulty, notes) in TEST_CASES:

        print(f"[Test {no}] {question[:70]}...")
        elapsed, response = send_question(question)
        elapsed_s = round(elapsed, 2)

        eval_res = evaluate_result(no, response, expected_places)
        method   = response.get("method", "?")
        sql_raw  = response.get("sql_query", "") or ""

        # Tampilkan SQL per place (dipisah ";")
        sql_parts = [s.strip() for s in sql_raw.split(";") if s.strip()]
        sql_display = sql_parts[0] if sql_parts else "(tidak ada SQL)"
        # Ambil hanya bagian SQL tanpa nama place prefix
        if ": " in sql_display and "SELECT" in sql_display:
            sql_display = sql_display.split(": ", 1)[1]

        status = "Benar" if eval_res["overall"] else "Salah"
        print(f"  Method   : {method}")
        print(f"  SQL[0]   : {sql_display[:80]}...")
        print(f"  Data rows: {eval_res['data_count']}")
        print(f"  Places OK: {eval_res['answer_mentions_all_places']}")
        print(f"  Status   : {status} | Waktu: {elapsed_s}s\n")

        if not eval_res["overall"]:
            all_ok = False

        # Notes evaluator
        eval_notes = []
        if not eval_res["is_comparison_mode"]:
            eval_notes.append("GAGAL: bukan comparison mode")
        if not eval_res["sql_ok"]:
            eval_notes.append("SQL tidak mencukupi (kurang query per place)")
        missing = [p for p in expected_places if p not in eval_res["places_found_in_answer"]]
        if missing:
            eval_notes.append(f"Lokasi tidak disebut: {', '.join(missing)}")
        if not eval_res["data_ok"]:
            eval_notes.append(f"Data kurang: {eval_res['data_count']} rows")
        if not eval_notes:
            eval_notes.append("Semua cek OK")

        rows_out.append({
            "no":            no,
            "difficulty":    difficulty,
            "question":      question,
            "expected_intent": expected_intent,
            "expected_places": str(expected_places),
            "detected_method": method,
            "sql_generated": sql_display,
            "sql_expected":  expected_sql_pat,
            "params_desc":   params_desc,
            "comparison_mode_ok": eval_res["is_comparison_mode"],
            "sql_ok":        eval_res["sql_ok"],
            "answer_ok":     eval_res["answer_mentions_all_places"],
            "data_count":    eval_res["data_count"],
            "response_time_s": elapsed_s,
            "overall":       status,
            "evaluator_notes": " | ".join(eval_notes),
        })

        md_rows.append({
            "no": no,
            "question": question,
            "intent": expected_intent,
            "places": " vs ".join(expected_places),
            "sql_generated": sql_display[:100] + ("..." if len(sql_display) > 100 else ""),
            "sql_expected": expected_sql_pat[:100] + ("..." if len(expected_sql_pat) > 100 else ""),
            "params_desc": params_desc,
            "elapsed": elapsed_s,
            "status": status,
            "notes": " | ".join(eval_notes),
        })

        time.sleep(1.0)

    # ── Simpan CSV ──────────────────────────────────────────────────────────
    fieldnames = list(rows_out[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"[CSV] -> {csv_path}")

    # ── Markdown Report ─────────────────────────────────────────────────────
    n_benar = sum(1 for r in rows_out if r["overall"] == "Benar")
    n_total = len(rows_out)

    lines = [
        "# Laporan Evaluasi Fitur Comparison GempaBot",
        f"\n**Tanggal:** {datetime.now().strftime('%d %B %Y %H:%M')}",
        f"**Endpoint:** `{CHAT_ENDPOINT}`",
        f"**Total Test:** {n_total} pertanyaan",
        f"**Hasil:** {n_benar}/{n_total} Benar ({100*n_benar//n_total}%)\n",
        "---\n",
        "## Tabel Evaluasi\n",
        "| No | Pertanyaan | Intent | Lokasi Dibandingkan | SQL Dihasilkan LLM | SQL yang Seharusnya | Variabel/Parameter | Waktu (s) | Benar/Salah |",
        "|----|------------|--------|---------------------|--------------------|---------------------|--------------------|:---------:|:-----------:|",
    ]
    for r in md_rows:
        q_short = r["question"][:55] + "..." if len(r["question"]) > 55 else r["question"]
        lines.append(
            f"| {r['no']} | {q_short} | `{r['intent']}` | {r['places']} "
            f"| `{r['sql_generated']}` | `{r['sql_expected']}` "
            f"| {r['params_desc']} | {r['elapsed']} | **{r['status']}** |"
        )

    lines += [
        "\n---\n",
        "## Detail Evaluasi per Test Case\n",
    ]
    for r in rows_out:
        icon = "✅" if r["overall"] == "Benar" else "❌"
        lines += [
            f"### {icon} Test {r['no']}: `{r['detected_method']}` — {r['overall']}\n",
            f"**Pertanyaan:** {rows_out[r['no']-1]['question']}\n",
            f"| Cek | Hasil |",
            f"|-----|-------|",
            f"| Comparison Mode | {'OK' if r['comparison_mode_ok'] else 'GAGAL'} |",
            f"| SQL per lokasi  | {'OK' if r['sql_ok'] else 'GAGAL'} |",
            f"| Semua lokasi disebut | {'OK' if r['answer_ok'] else 'GAGAL'} |",
            f"| Data rows cukup | {r['data_count']} rows ({'OK' if r['data_count'] >= 2 else 'GAGAL'}) |",
            f"| Waktu Eksekusi  | {r['response_time_s']} detik |",
            f"\n**Catatan:** {r['evaluator_notes']}\n",
        ]

    lines += [
        "---\n",
        "## Ringkasan\n",
        "| Metric | Nilai |",
        "|--------|-------|",
        f"| Total test | {n_total} |",
        f"| Benar | {n_benar} |",
        f"| Salah | {n_total - n_benar} |",
        f"| Akurasi | {100*n_benar//n_total}% |",
        f"| Avg waktu | {sum(r['response_time_s'] for r in rows_out)/n_total:.2f} s |",
        f"\n**Kesimpulan:** {'Semua test berhasil!' if all_ok else 'Ada test yang gagal — perlu investigasi lebih lanjut.'}\n",
    ]

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[MD]  -> {md_path}")

    print(f"\n{'='*65}")
    print(f"  Hasil: {n_benar}/{n_total} Benar")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    run_test()
