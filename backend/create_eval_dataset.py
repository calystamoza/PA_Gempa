import json
import os
from rag_engine import process_query, format_data, parse_intent

# Daftar pertanyaan untuk testing (mencakup berbagai intent)
TEST_QUESTIONS = [
    "Berapa rata-rata kekuatan gempa di Jawa Barat?",
    "Di mana gempa paling dalam terjadi tahun 2023?",
    "Berapa total gempa bulan Januari?",
    "Sebutkan 3 gempa terbesar di Papua",
    "Hari apa gempa paling sering terjadi?",
    "Apa itu magnitudo momen?",
    "Gempa dangkal terdalam ada di mana?",
    "Tolong berikan daftar gempa di Sulawesi Tengah bulan Desember 2023",
    "Kekuatan gempa maksimal di Indonesia berapa?",
    "Berapa rata rata kedalaman gempa di Maluku Utara?"
]

def create_dataset():
    print(f"Memulai pembuatan dataset evaluasi dengan {len(TEST_QUESTIONS)} pertanyaan...\n")
    dataset = {
        "question": [],
        "answer": [],
        "contexts": []
    }
    
    for i, q in enumerate(TEST_QUESTIONS, 1):
        print(f"[{i}/{len(TEST_QUESTIONS)}] Memproses: '{q}'")
        try:
            # Gunakan proses query standar
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
            dataset["contexts"].append([context_str]) # Ragas membutuhkan list of string untuk contexts
            
            print(f"  -> Jawaban: {result['answer'][:100]}...\n")
            
        except Exception as e:
            print(f"  -> Error: {e}\n")
            
    # Simpan ke JSON
    output_file = "eval_dataset.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=4)
        
    print(f"Selesai! Dataset berhasil disimpan ke '{output_file}'")

if __name__ == "__main__":
    create_dataset()
