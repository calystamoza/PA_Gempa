"""Update 3 baris CSV yang SQL-nya sudah diperbaiki (kasus #13, #24, #25)"""
import csv, io

CSV_FILE = "live_eval_results_20260702_183012.csv"

FIXES = {
    13: {
        "sql_generated": "SELECT place, date, magnitude, depth, depth_category, time FROM earthquakes WHERE year = %s ORDER BY magnitude DESC LIMIT 1",
        "sql_note": "[FIXED 2026-07-08] SQL sesuai pola intent 'max' + filter year=2024 via post-processing",
        "evaluator_notes": "ORDER BY magnitude DESC, year=2024 [FIXED: sebelumnya tanpa filter year, mengembalikan M9.0 Aceh 2004 sepanjang waktu]",
        "data_count": "1",
        "answer_preview": "Berdasarkan catatan seismik tahun 2024: Gempa Terbesar: Sulawesi Utara M6.7 (1/8/2024). [FIXED]",
    },
    24: {
        "sql_generated": "SELECT date, place, magnitude, depth, depth_category, time FROM earthquakes  ORDER BY year DESC LIMIT 10",
        "sql_note": "[FIXED 2026-07-08] SQL sesuai pola intent 'list' dengan ORDER BY year DESC",
        "evaluator_notes": "ORDER BY year DESC LIMIT 10 [FIXED: sebelumnya ORDER BY magnitude DESC, menampilkan terbesar bukan terbaru]",
    },
    25: {
        "sql_generated": "SELECT date, place, magnitude, depth, depth_category, time FROM earthquakes WHERE LOWER(place) LIKE %s ORDER BY depth ASC LIMIT 5",
        "sql_note": "[FIXED 2026-07-08] SQL sesuai pola intent 'list' dengan ORDER BY depth ASC",
        "evaluator_notes": "LIMIT 5, ORDER BY depth ASC, filter place LIKE '%kalimantan%' [FIXED: sebelumnya ORDER BY magnitude ASC, filter depth_category tidak perlu]",
    },
}

# Baca semua baris
with open(CSV_FILE, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

# Update baris yang perlu diperbaiki
updated = 0
for row in rows:
    no = int(row['no'])
    if no in FIXES:
        for key, val in FIXES[no].items():
            row[key] = val
        updated += 1
        print(f"[UPDATE] Baris #{no} diperbarui")

OUT_FILE = "live_eval_results_20260702_183012_fixed.csv"
with open(OUT_FILE, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nSelesai! {updated} baris diperbarui di '{OUT_FILE}'")
