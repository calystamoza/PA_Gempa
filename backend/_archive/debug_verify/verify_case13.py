"""Verifikasi kasus #13 via process_query (bukan build_sql langsung)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_engine import process_query

q = "Gempa terbesar apa yang pernah tercatat dalam data terbaru kita?"
print(f"Pertanyaan: {q}\n")
result = process_query(q, history=[])
print(f"\nSQL    : {result['sql_query']}")
print(f"Params : (lihat [SQL] di atas)")
print(f"Rows   : {result['data_count']}")
print(f"Jawaban: {result['answer'][:200]}")
