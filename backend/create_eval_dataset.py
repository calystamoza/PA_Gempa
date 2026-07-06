import json
import os
from rag_engine import process_query, format_data, parse_intent

# ─── 30 Pertanyaan Evaluasi Terstruktur (5 per intent) ────────────────────────
# Setiap intent diwakili oleh 5 pertanyaan yang representatif dan bervariasi.
# Intent trend = analisis POLA PERUBAHAN dari waktu ke waktu (per tahun/bulan),
#                BUKAN sekadar melihat distribusi hari.

TEST_QUESTIONS = [
    # ── Intent: count (menghitung jumlah kejadian) ──────────────────────────
    {"question": "Berapa total gempa yang terjadi di Indonesia sepanjang tahun 2023?", "intent": "count"},
    {"question": "Berapa jumlah gempa yang terjadi di Aceh pada tahun 2022?", "intent": "count"},
    {"question": "Berapa total gempa yang tercatat di Jawa Timur?", "intent": "count"},
    {"question": "Berapa banyak gempa yang terjadi di Sulawesi Tengah pada tahun 2021?", "intent": "count"},
    {"question": "Berapa jumlah gempa dangkal yang pernah terjadi di Maluku?", "intent": "count"},

    # ── Intent: average (rata-rata nilai metrik) ────────────────────────────
    {"question": "Berapa rata-rata kekuatan gempa di Jawa Barat?", "intent": "average"},
    {"question": "Berapa rata-rata kedalaman gempa di Maluku Utara?", "intent": "average"},
    {"question": "Berapa rata-rata magnitudo gempa di Sulawesi Tengah tahun 2023?", "intent": "average"},
    {"question": "Berapa rata-rata kedalaman gempa yang terjadi di Nusa Tenggara Timur?", "intent": "average"},
    {"question": "Berapa rata-rata magnitudo gempa di Papua tahun 2020?", "intent": "average"},

    # ── Intent: max/min (nilai ekstrim) ────────────────────────────────────
    {"question": "Di mana gempa paling dalam terjadi pada tahun 2023?", "intent": "max"},
    {"question": "Kekuatan gempa maksimal di Indonesia berapa?", "intent": "max"},
    {"question": "Berapa kekuatan gempa terbesar yang pernah terjadi di Sulawesi Utara?", "intent": "max"},
    {"question": "Di mana lokasi gempa bumi paling dangkal yang tercatat?", "intent": "min"},
    {"question": "Gempa terkuat apa yang pernah tercatat di Maluku?", "intent": "max"},

    # ── Intent: list (menampilkan daftar data spesifik) ─────────────────────
    {"question": "Sebutkan 3 gempa terbesar di Papua", "intent": "list"},
    {"question": "Tolong berikan daftar gempa di Sulawesi Tengah bulan Desember 2023", "intent": "list"},
    {"question": "Tampilkan daftar 5 gempa terkuat di Nusa Tenggara Timur", "intent": "list"},
    {"question": "Berikan daftar gempa yang terjadi di Jawa Barat pada tahun 2022", "intent": "list"},
    {"question": "Sebutkan 5 gempa terdalam yang pernah tercatat di Indonesia", "intent": "list"},

    # ── Intent: trend (pola perubahan dari waktu ke waktu) ──────────────────
    {"question": "Bagaimana tren jumlah gempa per tahun di Indonesia?", "intent": "trend"},
    {"question": "Apakah jumlah gempa di Indonesia cenderung meningkat atau menurun dari tahun ke tahun?", "intent": "trend"},
    {"question": "Bagaimana perubahan rata-rata magnitudo gempa per tahun?", "intent": "trend"},
    {"question": "Bagaimana tren gempa bumi di Jawa Timur dari tahun ke tahun?", "intent": "trend"},
    {"question": "Bagaimana perkembangan frekuensi gempa per bulan di Indonesia?", "intent": "trend"},

    # ── Intent: knowledge (edukasi / pengetahuan umum seismologi) ───────────
    {"question": "Apa itu magnitudo momen?", "intent": "knowledge"},
    {"question": "Mengapa Indonesia sering mengalami gempa bumi?", "intent": "knowledge"},
    {"question": "Apa perbedaan antara gempa dangkal, menengah, dan dalam?", "intent": "knowledge"},
    {"question": "Apa yang harus dilakukan untuk menyelamatkan diri saat gempa bumi?", "intent": "knowledge"},
    {"question": "Apa perbedaan antara Magnitudo Momen (Mw) dan Skala Richter?", "intent": "knowledge"},
]


def create_dataset():
    output_file = "eval_dataset.json"
    
    # Load existing dataset if it exists to support pausing/resuming
    dataset = {
        "question": [],
        "answer": [],
        "contexts": [],
        "intent_label": [],
    }
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            print(f"Melanjutkan dari checkpoint sebelumnya... ({len(dataset['question'])} pertanyaan sudah diproses)\n", flush=True)
        except Exception:
            pass

    processed_questions = set(dataset["question"])
    
    total = len(TEST_QUESTIONS)
    print(f"Memulai pembuatan dataset evaluasi dengan {total} pertanyaan...\n", flush=True)

    for i, item in enumerate(TEST_QUESTIONS, 1):
        q = item["question"]
        intent_label = item["intent"]
        
        if q in processed_questions:
            print(f"[{i:02d}/{total}] [{intent_label.upper():10s}] Melewati: '{q}' (Sudah diproses)", flush=True)
            continue
            
        print(f"[{i:02d}/{total}] [{intent_label.upper():10s}] Memproses: '{q}'", flush=True)
        try:
            result = process_query(q, history=[])

            # Format context
            if result["fetched_data"]:
                intent = parse_intent(q, [])
                context_str = format_data(result["fetched_data"], intent)
            else:
                context_str = "Tidak ada data dari database."

            if result["source"] == "llm-knowledge":
                context_str = "Pengetahuan umum LLM. Tidak memerlukan konteks spesifik dari database."

            dataset["question"].append(q)
            dataset["answer"].append(result["answer"])
            dataset["contexts"].append([context_str])
            dataset["intent_label"].append(intent_label)

            print(f"  -> Jawaban: {result['answer'][:120]}...\n", flush=True)

        except Exception as e:
            print(f"  -> Error: {e}\n", flush=True)
            # Tetap tambahkan placeholder agar indeks tidak geser
            dataset["question"].append(q)
            dataset["answer"].append(f"ERROR: {e}")
            dataset["contexts"].append(["Error saat memproses."])
            dataset["intent_label"].append(intent_label)

        # Save to JSON after EVERY question (Checkpointing)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=4)

    # Ringkasan per intent
    print("=" * 50, flush=True)
    print(f"Selesai! Dataset utuh disimpan ke '{output_file}'", flush=True)
    print(f"Total pertanyaan: {len(dataset['question'])}", flush=True)
    intents = {}
    for label in dataset["intent_label"]:
        intents[label] = intents.get(label, 0) + 1
    print("Distribusi per intent:", flush=True)
    for k, v in sorted(intents.items()):
        print(f"  - {k:12s}: {v} pertanyaan", flush=True)


if __name__ == "__main__":
    create_dataset()
