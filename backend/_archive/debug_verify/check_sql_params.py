import csv
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CSV_FILE = "live_eval_results_20260702_183012.csv"

# ── Definisi pola yang SEHARUSNYA muncul berdasarkan kata kunci di pertanyaan ─
# Format: (regex pada question, nama variabel yang harus ada di SQL / params)
EXPECTED_PARAMS = [
    (r"aceh",                  "place/aceh"),
    (r"jawa barat",            "place/jawa barat"),
    (r"jawa timur",            "place/jawa timur"),
    (r"jawa",                  "place/jawa"),
    (r"sumatera",              "place/sumatera"),
    (r"sulawesi",              "place/sulawesi"),
    (r"maluku",                "place/maluku"),
    (r"papua",                 "place/papua"),
    (r"kalimantan",            "place/kalimantan"),
    (r"nusa tenggara",         "place/nusa tenggara"),
    (r"tahun 20\d{2}",         "year filter"),
    (r"10 tahun terakhir|dekade terakhir|10 tahun",  "temporal min_year"),
    (r"5 tahun terakhir",      "temporal min_year"),
    (r"bulan",                 "month filter"),
    (r"dangkal",               "depth_category"),
    (r"menengah",              "depth_category"),
    (r"dalam",                 "depth_category"),
    (r"terbaru|terakhir",      "ORDER BY year/date DESC"),
    (r"pertama|terlama",       "ORDER BY year ASC"),
    (r"terbesar|terkuat|maksim(?:al|um)", "ORDER BY magnitude DESC"),
    (r"terkecil|paling kecil|minim(?:al|um)", "ORDER BY magnitude/depth ASC"),
    (r"terdalam",              "ORDER BY depth DESC"),
    (r"paling dangkal",        "ORDER BY depth ASC"),
]

# ── Indikator bahwa filter SUDAH ADA dalam SQL ────────────────────────────────
def check_sql_has(sql, keyword):
    return keyword.lower() in sql.lower()

# ── Baca CSV ─────────────────────────────────────────────────────────────────
issues = []
all_rows = []

with open(CSV_FILE, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        all_rows.append(row)

print(f"Total rows: {len(all_rows)}\n")
print("=" * 90)
print("ANALISIS SQL GENERATED vs EXPECTED PARAMS")
print("=" * 90)

for row in all_rows:
    no       = row['no']
    q        = row['question'].lower()
    sql      = row['sql_generated']
    notes    = row['evaluator_notes']
    intent   = row['detected_intent']
    sql_ok   = row['sql_ok']
    problems = []

    for pattern, param_name in EXPECTED_PARAMS:
        if re.search(pattern, q, re.IGNORECASE):
            # Cek apakah SQL punya tanda filter ini
            param_present = False

            if "place" in param_name:
                param_present = "LOWER(place) LIKE" in sql or "LOWER(place) =" in sql
            elif "year filter" in param_name:
                param_present = "year = %s" in sql or "year=" in sql
            elif "temporal min_year" in param_name:
                param_present = "year >= %s" in sql or "min_year" in notes.lower()
            elif "month filter" in param_name:
                param_present = "month" in sql.lower()
            elif "depth_category" in param_name:
                param_present = "depth_category" in sql
            elif "ORDER BY year/date DESC" in param_name:
                param_present = "ORDER BY year DESC" in sql or "ORDER BY date DESC" in sql
            elif "ORDER BY year ASC" in param_name:
                param_present = "ORDER BY year ASC" in sql
            elif "ORDER BY magnitude DESC" in param_name:
                param_present = "ORDER BY magnitude DESC" in sql
            elif "ORDER BY magnitude/depth ASC" in param_name:
                param_present = "ASC" in sql and ("magnitude" in sql or "depth" in sql)
            elif "ORDER BY depth DESC" in param_name:
                param_present = "ORDER BY depth DESC" in sql
            elif "ORDER BY depth ASC" in param_name:
                param_present = "ORDER BY depth ASC" in sql

            if not param_present:
                problems.append(f"  [!] Mungkin HILANG: '{param_name}' (kata kunci: '{pattern}')")

    if problems:
        issues.append(row)
        q_display = row['question']
        print(f"\n[{no:>2}] {q_display}")
        print(f"     Intent : {intent} | SQL OK: {sql_ok}")
        print(f"     SQL    : {sql}")
        print(f"     Notes  : {notes}")
        for p in problems:
            print(p)

print("\n" + "=" * 90)
print(f"RINGKASAN: {len(issues)}/{len(all_rows)} kasus berpotensi ada parameter hilang")
print("=" * 90)
