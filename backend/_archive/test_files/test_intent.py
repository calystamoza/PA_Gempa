import sys
import json
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag_engine import parse_intent

history = [
    {"role": "user", "content": "Berapa rata-rata magnitudo gempa di Sulawesi Tengah tahun 2023?"},
    {"role": "assistant", "content": "Berdasarkan catatan seismik untuk wilayah Sulawesi Tengah pada tahun 2023: Rata-rata Magnitudo: 4.796"}
]

question = "Berapa rata-rata magnitudo gempa di Sumatera 10 tahun terakhir?"

print("--- Q WITH HISTORY ---")
try:
    intent = parse_intent(question, history)
    print(f"PARSED: {intent}\n")
except Exception as e:
    print(e)
