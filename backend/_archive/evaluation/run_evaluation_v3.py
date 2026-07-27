"""
run_evaluation_v3.py
─────────────────────
Versi 3 — Evaluasi RAGAS lengkap:
  - Faithfulness       (apakah jawaban setia pada konteks/data?)
  - Answer Relevancy   (apakah jawaban relevan dengan pertanyaan?)

Membaca dari  : eval_dataset_v2.json  (dataset aktif setelah fix ILIKE)
Menyimpan ke  : evaluation_results_v3.csv  (tidak menimpa hasil lama)

Fitur:
  - Resume checkpoint berdasarkan index
  - Auto-save setelah setiap pertanyaan
  - Ringkasan akhir per-metric dan per-intent
"""

import json
import os
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.run_config import RunConfig
from dotenv import load_dotenv
import sys
import asyncio

load_dotenv()

from ragas.metrics import Faithfulness, AnswerRelevancy

METRICS = [Faithfulness(), AnswerRelevancy()]
METRIC_NAMES = ["faithfulness", "answer_relevancy"]

def run_evaluation():
    input_json = "eval_dataset_v2.json"
    output_csv = "evaluation_results_v3.csv"

    print(f"Memuat dataset evaluasi dari '{input_json}'...")
    try:
        with open(input_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: '{input_json}' tidak ditemukan.")
        print("Jalankan 'python create_eval_dataset_v2.py' terlebih dahulu.")
        return

    total = len(data["question"])
    print(f"Dataset dimuat: {total} pertanyaan\n")

    # --- Resume checkpoint ---
    already_done = 0
    results_list = []
    if os.path.exists(output_csv):
        try:
            existing_df = pd.read_csv(output_csv)
            already_done = len(existing_df)
            results_list = existing_df.to_dict("records")
            print(f"Melanjutkan dari checkpoint... ({already_done}/{total} sudah selesai)\n", flush=True)
        except Exception:
            pass
    print("Inisialisasi SequentialGroq Evaluator (Mencegah token burst)...", flush=True)
    from langchain_groq import ChatGroq
    from langchain_core.outputs import LLMResult
    from ragas.llms import LangchainLLMWrapper
    import asyncio
    
    class SequentialGroq(ChatGroq):
        async def agenerate_prompt(self, prompts, stop=None, callbacks=None, **kwargs):
            generations = []
            llm_output = {}
            for i, prompt in enumerate(prompts):
                res = await super().agenerate_prompt([prompt], stop=stop, callbacks=callbacks, **kwargs)
                generations.extend(res.generations)
                if res.llm_output:
                    llm_output.update(res.llm_output)
                
                if i < len(prompts) - 1:
                    print(f"    [Anti-Burst] Jeda 20s sebelum mengevaluasi n={i+2}...", flush=True)
                    await asyncio.sleep(20)
                    
            return LLMResult(generations=generations, llm_output=llm_output)

    base_llm = SequentialGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )
    
    # Bungkus LLM dengan wrapper resmi RAGAS dan aktifkan bypass_n
    evaluator_llm = LangchainLLMWrapper(base_llm)
    evaluator_llm.bypass_n = True

    results_list = []
    if os.path.exists(output_csv):
        try:
            df_existing = pd.read_csv(output_csv)
            results_list = df_existing.to_dict("records")
            print(f"Ditemukan {len(results_list)} hasil sebelumnya di CSV. Akan mengecek dan mengulang yang NaN...\n")
        except Exception:
            pass

    # --- Setup Evaluator Embeddings ---
    print("Inisialisasi Embedding Model (all-MiniLM-L6-v2)...", flush=True)
    from langchain_community.embeddings import HuggingFaceEmbeddings
    evaluator_embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    run_config = RunConfig(max_workers=1, max_retries=3, timeout=120)
    print(f"\nMemulai evaluasi RAGAS v3 -- {total} item...\n", flush=True)
    print(f"Metrics: {', '.join(METRIC_NAMES)}\n", flush=True)
    print("=" * 60, flush=True)
    
    import time
    import math

    # --- Loop Evaluasi ---
    for i in range(total):
        q = data["question"][i]
        
        # --- Cek apakah pertanyaan ini sudah berhasil dievaluasi sebelumnya ---
        if i < len(results_list):
            existing_f = results_list[i].get("faithfulness")
            existing_ar = results_list[i].get("answer_relevancy")
            
            # Cek apakah nilainya ada dan bukan NaN
            if pd.notna(existing_f) and pd.notna(existing_ar):
                print(f"[{i+1}/{total}] SKIP (Sudah ada) -> Intent: {data['intent_label'][i]} | Q: {q[:50]}...")
                continue
            else:
                print(f"[{i+1}/{total}] RETRY (Sebelumnya NaN/Gagal) -> Intent: {data['intent_label'][i]} | Q: {q[:50]}...")
        else:
            print(f"[{i+1}/{total}] EVALUASI -> Intent: {data['intent_label'][i]} | Q: {q[:50]}...")

        # Siapkan data dictionary untuk Ragas
        data_dict = {
            "question": [q],
            "answer": [data["answer"][i]],
            "contexts": [data["contexts"][i]],
            "ground_truth": [data["answer"][i]]
        }
        single_hf = Dataset.from_dict(data_dict)

        try:
            result = evaluate(
                dataset=single_hf,
                metrics=METRICS,
                llm=evaluator_llm,
                embeddings=evaluator_embeddings,
                run_config=run_config,
                raise_exceptions=True,
                show_progress=False,
            )
            res_df = result.to_pandas()
            row_dict = res_df.iloc[0].to_dict()
            
            # Tambahkan intent_label
            row_dict["intent_label"] = data["intent_label"][i]
            
            # Update list (timpa jika retry, append jika baru)
            if i < len(results_list):
                results_list[i] = row_dict
            else:
                results_list.append(row_dict)

            f_score  = row_dict.get("faithfulness",     "N/A")
            ar_score = row_dict.get("answer_relevancy", "N/A")
            print(f"  -> Faithfulness:     {f_score}", flush=True)
            print(f"  -> Answer Relevancy: {ar_score}", flush=True)
            
        except KeyboardInterrupt:
            print("\nDihentikan oleh user. Progress terakhir sudah tersimpan.", flush=True)
            break
        except Exception as e:
            print(f"  -> ERROR saat evaluasi: {e}", flush=True)
            # Isi dengan NaN agar bisa di-retry nanti
            fail_dict = {
                "question": q,
                "answer": data["answer"][i],
                "contexts": data["contexts"][i],
                "ground_truth": data["answer"][i],
                "intent_label": data["intent_label"][i],
                "faithfulness": float('nan'),
                "answer_relevancy": float('nan')
            }
            if i < len(results_list):
                results_list[i] = fail_dict
            else:
                results_list.append(fail_dict)

        # Auto-save setelah setiap pertanyaan
        pd.DataFrame(results_list).to_csv(output_csv, index=False)
        time.sleep(5)  # Jeda 5 detik cukup untuk API Gemini

    # --- Ringkasan Akhir ---
    print("\n" + "=" * 60, flush=True)
    print(f"Selesai! Hasil disimpan ke '{output_csv}'", flush=True)

    df_final = pd.DataFrame(results_list)

    for metric in METRIC_NAMES:
        if metric in df_final.columns:
            overall_avg = df_final[metric].mean()
            print(f"\nRATA-RATA {metric.upper()}: {overall_avg:.4f}", flush=True)

            if "intent_label" in df_final.columns:
                print(f"  Per Intent:", flush=True)
                for intent_name, grp in df_final.groupby("intent_label"):
                    avg = grp[metric].mean()
                    count = len(grp)
                    print(f"    {intent_name:12s}: {avg:.4f}  ({count} kasus)", flush=True)

    print("=" * 60, flush=True)


if __name__ == "__main__":
    run_evaluation()
