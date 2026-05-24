import json
import os
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

def run_evaluation():
    print("Memuat dataset evaluasi...")
    try:
        with open("eval_dataset.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: 'eval_dataset.json' tidak ditemukan. Jalankan 'python create_eval_dataset.py' terlebih dahulu.")
        return

    # Konversi ke HuggingFace Dataset
    hf_dataset = Dataset.from_dict(data)
    
    # Inisialisasi Evaluator LLM (menggunakan Groq)
    # Sangat disarankan menggunakan model yang besar untuk evaluator
    print("Inisialisasi Groq Evaluator...")
    evaluator_llm = ChatGroq(
        model="llama-3.3-70b-versatile", # Atau gunakan "llama-3.1-8b-instant" jika limit 70b habis
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

    print("\nMemulai evaluasi Ragas (proses ini mungkin memakan waktu beberapa menit)...")
    try:
        # Jalankan evaluasi
        result = evaluate(
            dataset=hf_dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=evaluator_llm,
            raise_exceptions=False 
        )
        
        print("\n=== HASIL EVALUASI RAGAS ===")
        print(result)
        
        # Konversi ke Pandas DataFrame untuk melihat skor per pertanyaan
        df = result.to_pandas()
        
        # Simpan ke CSV
        output_csv = "evaluation_results.csv"
        df.to_csv(output_csv, index=False)
        print(f"\nHasil detail per pertanyaan disimpan ke '{output_csv}'")
        
        # Tampilkan ringkasan
        print("\nPreview Skor Detail:")
        # Tangani kemungkinan kolom belum ada jika API gagal
        cols = ['question']
        if 'faithfulness' in df.columns: cols.append('faithfulness')
        if 'answer_relevancy' in df.columns: cols.append('answer_relevancy')
        
        print(df[cols].head(5))
        
    except Exception as e:
        print(f"\nTerjadi error saat evaluasi: {e}")

if __name__ == "__main__":
    run_evaluation()
