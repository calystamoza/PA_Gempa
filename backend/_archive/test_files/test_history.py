import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag_engine import parse_intent

history = [
    {"role": "user", "content": "Tampilkan 10 gempa terbaru yang tercatat dalam data kita"},
    {"role": "assistant", "content": "Berdasarkan catatan seismik untuk wilayah Indonesia:\nTanggal\tWilayah\tMagnitudo\tKedalaman\n1/2/2024\tNusa Tenggara Timur\tM4.9\t35.0 km\n1/3/2024\tJawa Barat\tM4.8\t98.951 km\n1/3/2024\tSulawesi Selatan\tM4.3\t422.64 km"}
]

question = "Berapa rata-rata magnitudo gempa di Sulawesi Tengah tahun 2023?"

print("--- TESTING PARSE INTENT ---")
intent = parse_intent(question, history)
print("FINAL INTENT:", intent)
