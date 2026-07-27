"""
Verifikasi perbaikan 3 kasus SQL bermasalah dari live_eval.
Kasus #13, #24, #25
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_engine import parse_intent, build_sql

cases = [
    ("Gempa terbesar apa yang pernah tercatat dalam data terbaru kita?",
     "Harusnya: year = 2024 sebagai filter, ORDER BY magnitude DESC",
     "Kasus #13"),

    ("Tampilkan 10 gempa terbaru yang tercatat dalam data kita",
     "Harusnya: ORDER BY year DESC LIMIT 10",
     "Kasus #24"),

    ("Sebutkan 5 gempa paling dangkal yang pernah terjadi di Kalimantan",
     "Harusnya: ORDER BY depth ASC LIMIT 5, filter place kalimantan",
     "Kasus #25"),
]

for question, expected, label in cases:
    print(f"\n{'='*70}")
    print(f"[{label}] {question}")
    print(f"EXPECTED: {expected}")
    intent = parse_intent(question, [])
    print(f"INTENT  : {json.dumps(intent, ensure_ascii=False)}")
    sql, params = build_sql(intent)
    print(f"SQL     : {sql}")
    print(f"PARAMS  : {params}")
