import json
import os
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness
from langchain_groq import ChatGroq
from ragas.run_config import RunConfig
from dotenv import load_dotenv

load_dotenv()

def run_evaluation():
    import sys
    import asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print("Memuat dataset evaluasi...")
    try:
        with open("eval_dataset.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: 'eval_dataset.json' tidak ditemukan. Jalankan 'python create_eval_dataset.py' terlebih dahulu.")
        return

    # Konversi ke HuggingFace Dataset
    hf_dataset = Dataset.from_dict(data)
    
    # Inisialisasi Evaluator LLM (menggunakan Groq Llama 3.3 70B yang pintar & gratis)
    print("Inisialisasi Groq Evaluator...")
    evaluator_llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

    # Batasi concurrency agar tidak memicu rate limit Groq API
    run_config = RunConfig(max_workers=2, timeout=120)

    print("\nMemulai evaluasi Ragas (proses ini mungkin memakan waktu beberapa menit)...")
    try:
        # Jalankan evaluasi hanya untuk metrik faithfulness (kebenaran informasi / anti-halusinasi)
        result = evaluate(
            dataset=hf_dataset,
            metrics=[faithfulness],
            llm=evaluator_llm,
            run_config=run_config,
            raise_exceptions=True 
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
        cols = [c for c in ['question', 'faithfulness'] if c in df.columns]
        if cols:
            print(df[cols].head(5))
        else:
            print(df.head(5))
        
    except Exception as e:
        print(f"\nTerjadi error saat evaluasi: {e}")

if __name__ == "__main__":
    run_evaluation()
