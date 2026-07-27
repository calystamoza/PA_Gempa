"""
create_eval_dataset_v2.py
─────────────────────────
Versi 2 — Dijalankan SETELAH perubahan prompt di rag_engine.py.
Output: eval_dataset_v2.json  (TIDAK menimpa eval_dataset.json lama)

Perubahan dari v1:
- Menambahkan test case temporal baru (dekade, data terbaru/terlama, dll.)
- Menyelaraskan pertanyaan dengan live_eval.py (35 kasus, 5 per intent)
"""

import json
import os
from rag_engine import process_query, format_data, parse_intent

# ─── 35 Pertanyaan Evaluasi Terstruktur (5 per intent) ───────────────────────
TEST_QUESTIONS = [
    # ── Intent: count ──────────────────────────────────────────────────────
    {"question": "Berapa total gempa yang terjadi di Indonesia sepanjang tahun 2023?",          "intent": "count"},
    {"question": "Berapa jumlah gempa yang terjadi di Aceh pada tahun 2022?",                   "intent": "count"},
    {"question": "Berapa jumlah gempa dangkal yang pernah terjadi di Maluku?",                  "intent": "count"},
    {"question": "Berapa banyak gempa yang terjadi dalam 10 tahun terakhir di Indonesia?",      "intent": "count"},
    {"question": "Berapa total gempa yang tercatat selama dekade 2010-an?",                     "intent": "count"},

    # ── Intent: average ────────────────────────────────────────────────────
    {"question": "Berapa rata-rata kekuatan gempa di Jawa Barat?",                              "intent": "average"},
    {"question": "Berapa rata-rata kedalaman gempa di Maluku Utara?",                           "intent": "average"},
    {"question": "Berapa rata-rata magnitudo gempa di Sulawesi Tengah tahun 2023?",             "intent": "average"},
    {"question": "Berapa rata-rata kedalaman gempa dalam 5 tahun terakhir di Indonesia?",       "intent": "average"},
    {"question": "Berapa rata-rata magnitudo gempa selama dekade terakhir di Sumatera?",        "intent": "average"},

    # ── Intent: max ────────────────────────────────────────────────────────
    {"question": "Kekuatan gempa maksimal di Indonesia berapa?",                                "intent": "max"},
    {"question": "Berapa kekuatan gempa terbesar yang pernah terjadi di Sulawesi Utara?",       "intent": "max"},
    {"question": "Gempa terbesar apa yang pernah tercatat dalam data terbaru kita?",            "intent": "max"},
    {"question": "Gempa terdalam apa yang pernah terjadi di Indonesia?",                        "intent": "max"},
    {"question": "Gempa terakhir apa yang tercatat dalam data kita?",                           "intent": "max"},

    # ── Intent: min ────────────────────────────────────────────────────────
    {"question": "Di mana lokasi gempa bumi paling dangkal yang tercatat?",                     "intent": "min"},
    {"question": "Gempa bumi pertama apa yang tercatat dalam data kita?",                       "intent": "min"},
    {"question": "Berapa magnitudo terkecil gempa yang pernah tercatat di Jawa Timur?",         "intent": "min"},
    {"question": "Apa gempa dengan kekuatan paling kecil yang terjadi di Indonesia?",           "intent": "min"},
    {"question": "Gempa dengan kedalaman paling kecil yang tercatat di Sulawesi apa?",          "intent": "min"},

    # ── Intent: list ───────────────────────────────────────────────────────
    {"question": "Sebutkan 3 gempa terbesar di Papua",                                          "intent": "list"},
    {"question": "Tampilkan daftar 5 gempa terkuat di Nusa Tenggara Timur",                     "intent": "list"},
    {"question": "Berikan daftar gempa yang terjadi di Jawa Barat pada tahun 2022",             "intent": "list"},
    {"question": "Tampilkan 10 gempa terbaru yang tercatat dalam data kita",                    "intent": "list"},
    {"question": "Sebutkan 5 gempa paling dangkal yang pernah terjadi di Kalimantan",           "intent": "list"},

    # ── Intent: trend ──────────────────────────────────────────────────────
    {"question": "Bagaimana tren jumlah gempa per tahun di Indonesia?",                         "intent": "trend"},
    {"question": "Apakah jumlah gempa di Indonesia cenderung meningkat atau menurun dari tahun ke tahun?", "intent": "trend"},
    {"question": "Bagaimana perkembangan frekuensi gempa per bulan di Indonesia?",              "intent": "trend"},
    {"question": "Bagaimana tren jumlah gempa selama 10 tahun terakhir di Sumatera?",           "intent": "trend"},
    {"question": "Apakah gempa makin sering terjadi di Jawa selama dekade terakhir?",           "intent": "trend"},

    # ── Intent: knowledge ──────────────────────────────────────────────────
    {"question": "Apa itu magnitudo momen?",                                                    "intent": "knowledge"},
    {"question": "Mengapa Indonesia sering mengalami gempa bumi?",                              "intent": "knowledge"},
    {"question": "Apa perbedaan antara gempa dangkal, menengah, dan dalam?",                    "intent": "knowledge"},
    {"question": "Apa yang harus dilakukan untuk menyelamatkan diri saat gempa bumi?",          "intent": "knowledge"},
    {"question": "Bagaimana cara kerja seismograf?",                                            "intent": "knowledge"},
]


def create_dataset():
    # ─── Output ke file BARU agar tidak menimpa eval_dataset.json lama ───
    output_file = "eval_dataset_v2.json"

    dataset = {
        "question": [],
        "answer": [],
        "contexts": [],
        "intent_label": [],
    }

    # Dukung resume jika script dihentikan di tengah jalan
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                dataset = json.load(f)
            print(f"Melanjutkan dari checkpoint v2... ({len(dataset['question'])} pertanyaan sudah diproses)\n", flush=True)
        except Exception:
            pass

    processed_questions = set(dataset["question"])
    total = len(TEST_QUESTIONS)
    print(f"Memulai pembuatan dataset v2 ({total} pertanyaan, prompt baru)...\n", flush=True)

    for i, item in enumerate(TEST_QUESTIONS, 1):
        q = item["question"]
        intent_label = item["intent"]

        if q in processed_questions:
            print(f"[{i:02d}/{total}] [{intent_label.upper():10s}] SKIP: '{q}'", flush=True)
            continue

        print(f"[{i:02d}/{total}] [{intent_label.upper():10s}] Memproses: '{q}'", flush=True)
        try:
            result = process_query(q, history=[])

            if result["fetched_data"]:
                intent = parse_intent(q, [])
                context_str = format_data(result["fetched_data"], intent)
            else:
                context_str = "Tidak ada data dari database."

            if result.get("source") == "llm-knowledge":
                context_str = "Pengetahuan umum LLM. Tidak memerlukan konteks spesifik dari database."

            dataset["question"].append(q)
            dataset["answer"].append(result["answer"])
            dataset["contexts"].append([context_str])
            dataset["intent_label"].append(intent_label)

            preview = result['answer'][:120].encode('ascii', 'replace').decode('ascii')
            print(f"  -> Jawaban: {preview}...\n", flush=True)

        except Exception as e:
            print(f"  -> Error: {e}\n", flush=True)
            dataset["question"].append(q)
            dataset["answer"].append(f"ERROR: {e}")
            dataset["contexts"].append(["Error saat memproses."])
            dataset["intent_label"].append(intent_label)

        # Auto-save setiap satu pertanyaan selesai
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=4)

    print("=" * 50, flush=True)
    print(f"Selesai! Dataset v2 disimpan ke '{output_file}'", flush=True)
    print(f"Total: {len(dataset['question'])} pertanyaan", flush=True)
    intents = {}
    for label in dataset["intent_label"]:
        intents[label] = intents.get(label, 0) + 1
    for k, v in sorted(intents.items()):
        print(f"  - {k:12s}: {v} pertanyaan", flush=True)


if __name__ == "__main__":
    create_dataset()
