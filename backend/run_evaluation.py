import json
import os
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
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
    
    # Inisialisasi Evaluator LLM (menggunakan Gemini)
    print("Inisialisasi Gemini Evaluator...")
    evaluator_llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0,
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    print("Inisialisasi Gemini Embeddings...")
    evaluator_embeddings = GoogleGenerativeAIEmbeddings(
        model="text-embedding-004",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    # Batasi concurrency ke 1 (serial) agar tidak memicu rate limit 429 Gemini API (15 RPM)
    run_config = RunConfig(max_workers=1, timeout=240)

    print("\nMemulai evaluasi Ragas (proses ini mungkin memakan waktu beberapa menit)...")
    try:
        # Jalankan evaluasi
        result = evaluate(
            dataset=hf_dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
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
        cols = [c for c in ['question', 'faithfulness', 'answer_relevancy'] if c in df.columns]
        if cols:
            print(df[cols].head(5))
        else:
            print(df.head(5))
        
    except Exception as e:
        print(f"\nTerjadi error saat evaluasi: {e}")

if __name__ == "__main__":
    run_evaluation()
