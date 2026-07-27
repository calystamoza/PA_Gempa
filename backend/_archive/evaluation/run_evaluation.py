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

    output_csv = "evaluation_results.csv"
    
    # Load existing results to support resuming
    evaluated_questions = set()
    results_list = []
    if os.path.exists(output_csv):
        try:
            existing_df = pd.read_csv(output_csv)
            evaluated_questions = set(existing_df['question'])
            results_list = existing_df.to_dict('records')
            print(f"Melanjutkan dari checkpoint... ({len(evaluated_questions)} evaluasi sudah selesai)\n", flush=True)
        except Exception:
            pass

    from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas.metrics import answer_relevancy
    
    # Inisialisasi Evaluator LLM
    print("Inisialisasi Groq Evaluator...", flush=True)
    evaluator_llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    print("Inisialisasi Embedding Model...", flush=True)
    evaluator_embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    run_config = RunConfig(max_workers=2, timeout=120)

    total = len(data["question"])
    print(f"\nMemulai evaluasi Ragas item per item ({total} total)...", flush=True)

    for i in range(total):
        q = data["question"][i]
        
        if q in evaluated_questions:
            print(f"[{i+1:02d}/{total}] Melewati: '{q}' (Sudah dievaluasi)", flush=True)
            continue
            
        print(f"[{i+1:02d}/{total}] Mengevaluasi: '{q}'", flush=True)
        
        # Buat dataset per 1 item agar bisa dipotong-potong
        item_dict = {k: [v[i]] for k, v in data.items()}
        single_hf = Dataset.from_dict(item_dict)
        
        try:
            result = evaluate(
                dataset=single_hf,
                metrics=[faithfulness, answer_relevancy],
                llm=evaluator_llm,
                embeddings=evaluator_embeddings,
                run_config=run_config,
                raise_exceptions=True,
                show_progress=False  # Matikan progress bar bawaan agar log terminal bersih
            )
            res_df = result.to_pandas()
            row_dict = res_df.iloc[0].to_dict()
            results_list.append(row_dict)
            
            f_score = row_dict.get('faithfulness', 'N/A')
            ar_score = row_dict.get('answer_relevancy', 'N/A')
            print(f"  -> Skor Faithfulness: {f_score} | Answer Relevancy: {ar_score}\n", flush=True)
            
        except Exception as e:
            print(f"  -> Error: {e}\n", flush=True)
            # Tetap simpan agar indeks tak geser, score dikosongkan
            item_dict_flat = {k: v[i] for k, v in data.items()}
            item_dict_flat['faithfulness'] = None
            results_list.append(item_dict_flat)
        
        # Simpan ke CSV SETIAP KALI 1 pertanyaan selesai (Auto-Save)
        pd.DataFrame(results_list).to_csv(output_csv, index=False)

    print("=" * 50, flush=True)
    print(f"Selesai! Seluruh hasil evaluasi disimpan ke '{output_csv}'", flush=True)
    
    df_final = pd.DataFrame(results_list)
    if 'faithfulness' in df_final.columns:
        avg_score = df_final['faithfulness'].mean()
        print(f"RATA-RATA FAITHFULNESS KESELURUHAN: {avg_score:.2f}", flush=True)

if __name__ == "__main__":
    run_evaluation()
