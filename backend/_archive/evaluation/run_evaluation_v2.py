"""
run_evaluation_v2.py
─────────────────────
Versi 2 — Membaca dari eval_dataset_v2.json (prompt baru)
           Menyimpan ke evaluation_results_v2.csv (TIDAK menimpa hasil lama)
"""

import json
import os
import pandas as pd
from datasets import Dataset
from ragas import evaluate
try:
    from ragas.metrics.collections import faithfulness
except ImportError:
    from ragas.metrics import faithfulness
from langchain_groq import ChatGroq
from ragas.run_config import RunConfig
from dotenv import load_dotenv
import sys
import asyncio

load_dotenv()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def run_evaluation():
    # ─── Input dari v2 dataset, output ke v2 results ───────────────────────
    input_json  = "eval_dataset_v2.json"
    output_csv  = "evaluation_results_v2.csv"

    print(f"Memuat dataset evaluasi v2 dari '{input_json}'...")
    try:
        with open(input_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: '{input_json}' tidak ditemukan.")
        print("Jalankan 'python create_eval_dataset_v2.py' terlebih dahulu.")
        return

    total = len(data["question"])
    print(f"Dataset dimuat: {total} pertanyaan\n")

    # Dukung resume berdasarkan INDEX (bukan question string, karena bisa NaN di output RAGAs)
    already_done = 0  # jumlah baris yang sudah ada di CSV
    results_list = []
    if os.path.exists(output_csv):
        try:
            existing_df = pd.read_csv(output_csv)
            already_done = len(existing_df)
            results_list = existing_df.to_dict("records")
            print(f"Melanjutkan dari checkpoint v2... ({already_done}/{total} sudah selesai)\n", flush=True)
        except Exception:
            pass

    # ─── Inisialisasi Evaluator ─────────────────────────────────────────────
    print("Inisialisasi Groq Evaluator (llama-3.3-70b-versatile)...", flush=True)
    evaluator_llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

    print("Inisialisasi Embedding Model (all-MiniLM-L6-v2)...", flush=True)
    from langchain_community.embeddings import HuggingFaceEmbeddings
    evaluator_embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    run_config = RunConfig(max_workers=2, timeout=120)
    print(f"\nMemulai evaluasi Ragas v2 — {total} item...\n", flush=True)

    for i in range(total):
        q = data["question"][i]
        intent = data["intent_label"][i]

        # Skip berdasarkan index — lebih reliable daripada string matching
        if i < already_done:
            print(f"[{i+1:02d}/{total}] SKIP ({intent.upper():10s}): '{q[:70]}'", flush=True)
            continue

        print(f"[{i+1:02d}/{total}] EVAL ({intent.upper():10s}): '{q[:70]}'", flush=True)

        item_dict = {k: [v[i]] for k, v in data.items()}
        single_hf = Dataset.from_dict(item_dict)

        try:
            result = evaluate(
                dataset=single_hf,
                metrics=[faithfulness],
                llm=evaluator_llm,
                embeddings=evaluator_embeddings,
                run_config=run_config,
                raise_exceptions=True,
                show_progress=False,
            )
            res_df = result.to_pandas()
            row_dict = res_df.iloc[0].to_dict()
            results_list.append(row_dict)

            f_score = row_dict.get("faithfulness", "N/A")
            print(f"  -> Faithfulness: {f_score}\n", flush=True)

        except Exception as e:
            print(f"  -> Error: {e}\n", flush=True)
            item_flat = {k: v[i] for k, v in data.items()}
            item_flat["faithfulness"] = None
            results_list.append(item_flat)

        # Auto-save setelah setiap pertanyaan
        pd.DataFrame(results_list).to_csv(output_csv, index=False)

    # ─── Ringkasan Akhir ───────────────────────────────────────────────────
    print("=" * 60, flush=True)
    print(f"Selesai! Hasil disimpan ke '{output_csv}'", flush=True)

    df_final = pd.DataFrame(results_list)
    if "faithfulness" in df_final.columns:
        overall_avg = df_final["faithfulness"].mean()
        print(f"\nRATA-RATA FAITHFULNESS (v2, prompt baru): {overall_avg:.4f}", flush=True)

        # Rata-rata per intent
        if "intent_label" in df_final.columns:
            print("\nPer Intent:", flush=True)
            for intent, grp in df_final.groupby("intent_label"):
                avg = grp["faithfulness"].mean()
                count = len(grp)
                print(f"  {intent:12s}: {avg:.4f} ({count} kasus)", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    run_evaluation()
