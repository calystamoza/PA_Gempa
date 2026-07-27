"""Generate tabel SQL comparison dari live_eval_results CSV."""
import csv, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CSV_FILE = "live_eval_results_20260702_183012.csv"
OUT_FILE = "tabel_sql_comparison.md"

# SQL ASLI sebelum perbaikan untuk 3 kasus yang di-fix
ORIGINAL_SQL = {
    13: "SELECT place, date, magnitude, depth, depth_category, time FROM earthquakes  ORDER BY magnitude DESC LIMIT 5",
    24: "SELECT date, place, magnitude, depth, depth_category, time FROM earthquakes  ORDER BY magnitude DESC LIMIT 10",
    25: "SELECT date, place, magnitude, depth, depth_category, time FROM earthquakes WHERE LOWER(place) LIKE %s AND depth_category = %s ORDER BY magnitude ASC LIMIT 5",
}

rows_data = []
with open(CSV_FILE, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        no = int(row['no'])
        question = row['question']
        sql_generated = row['sql_generated']
        sql_ok = row['sql_ok']
        sql_note = row['sql_note']
        time_s = row['response_time_s']
        is_fixed = '[FIXED' in sql_note

        # SQL oleh LLM: untuk yang di-fix, tampilkan SQL asli sebelum perbaikan
        if is_fixed and no in ORIGINAL_SQL:
            sql_llm = ORIGINAL_SQL[no]
            sql_expected = sql_generated  # sql_generated sekarang sudah = yang benar
            status = "Salah (Diperbaiki)"
        else:
            sql_llm = sql_generated
            sql_expected = sql_generated  # sama karena benar
            status = "Benar" if sql_ok.upper() == "TRUE" else "Salah"

        rows_data.append({
            "no": no,
            "question": question,
            "intent": row["detected_intent"],
            "sql_llm": sql_llm,
            "sql_expected": sql_expected,
            "params": row["evaluator_notes"],
            "time_s": time_s,
            "status": status,
        })

# Tulis ke markdown
lines = []
lines.append("# Tabel Perbandingan SQL — Live Evaluation GempaBot\n")
lines.append("> Sumber: `live_eval_results_20260702_183012.csv`  |  Total: 35 kasus uji\n")
lines.append("")
lines.append("| No | Pertanyaan | Intent | Hasil SQL oleh LLM | Hasil SQL yang Seharusnya | Variabel/Parameter | Waktu (s) | Benar/Salah |")
lines.append("|----|-----------|--------|-------------------|--------------------------|-------------------|-----------|-------------|")

for r in rows_data:
    sql_llm_short = r["sql_llm"].replace("|", "\\|")
    sql_exp_short = r["sql_expected"].replace("|", "\\|")
    params_short  = r["params"].replace("|", "\\|")
    status_cell = f"**{r['status']}**" if "Diperbaiki" in r["status"] or "Salah" in r["status"] else r["status"]

    lines.append(
        f"| {r['no']} | {r['question']} | `{r['intent']}` | `{sql_llm_short}` | `{sql_exp_short}` | {params_short} | {r['time_s']} | {status_cell} |"
    )

content = "\n".join(lines)

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Selesai! Tabel disimpan ke '{OUT_FILE}' ({len(rows_data)} baris)")
