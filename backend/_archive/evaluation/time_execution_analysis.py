"""
time_complexity_analysis.py — Analisis Kompleksitas Eksekusi GempaBot
======================================================================
Menganalisis DATA YANG SUDAH ADA di evaluation_results_v3.csv tanpa
melakukan API call tambahan. Menggunakan proxy metrics:
  - Panjang konteks (ctx_len)   → proxy beban SQL & data yang dikembalikan
  - Panjang jawaban (ans_len)   → proxy beban LLM answer generation
  - Skor faithfulness & relevancy → kualitas output

Output: time_complexity_report_<timestamp>.md
"""

import pandas as pd
import statistics
from datetime import datetime

# ─── Load data ────────────────────────────────────────────────────────────────
EVAL_CSV = "_archive/evaluation/evaluation_results_v3.csv"
df = pd.read_csv(EVAL_CSV)

# ─── Tambah proxy metrics ─────────────────────────────────────────────────────
df["ctx_len"]   = df["contexts"].fillna("").apply(len)
df["ans_len"]   = df["answer"].fillna("").apply(len)
df["q_len"]     = df["question"].fillna("").apply(len)
df["n_words"]   = df["question"].fillna("").apply(lambda x: len(x.split()))

# Klasifikasi kompleksitas berdasarkan panjang pertanyaan & kata kunci
def classify_complexity(row):
    q = str(row["question"]).lower()
    complex_kw  = ["dekade", "rentang", "selama", "antara", "perkembangan", "dalam.*tahun terakhir",
                   "10 tahun", "5 tahun", "per tahun", "per bulan", "bagaimana tren"]
    medium_kw   = ["dan", "pada tahun", "tahun 20", "di ", "paling", "terbanyak", "terdalam",
                   "terbesar", "terkuat", "terkecil", "rata-rata"]
    for kw in complex_kw:
        import re
        if re.search(kw, q):
            return "complex"
    for kw in medium_kw:
        if kw in q:
            return "medium"
    return "simple"

df["complexity"] = df.apply(classify_complexity, axis=1)

# ─── Config ──────────────────────────────────────────────────────────────────
INTENT_ORDER = ["count", "average", "max", "min", "list", "trend", "knowledge"]
COMPLEXITY_ORDER = ["simple", "medium", "complex"]

INTENT_NOTES = {
    "count":     "SELECT COUNT(*) — agregasi tunggal",
    "average":   "SELECT AVG() — satu pass scan kolom numerik",
    "max":       "ORDER BY DESC LIMIT — scan minimal",
    "min":       "ORDER BY ASC LIMIT — scan minimal",
    "list":      "SELECT * ORDER BY LIMIT N — transfer data lebih besar",
    "trend":     "GROUP BY year/month — full scan + agregasi per grup",
    "knowledge": "Bypass DB — hanya LLM inference (2 Groq API call)",
}

COMPLEXITY_DEF = {
    "simple":  "≤1 filter, pertanyaan langsung",
    "medium":  "2 filter atau aggregasi + filter lokasi",
    "complex": "Rentang waktu, GROUP BY, atau multi-konsep",
}

# ─── Bangun laporan Markdown ──────────────────────────────────────────────────
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
md_path   = f"time_complexity_report_{timestamp}.md"

lines = []
lines.append("# Laporan Analisis Kompleksitas Eksekusi GempaBot")
lines.append(f"\n**Tanggal:** {datetime.now().strftime('%d %B %Y %H:%M')}")
lines.append(f"**Sumber data:** `{EVAL_CSV}`")
lines.append(f"**Total sampel:** {len(df)} pertanyaan (5 per intent × 7 intent)")
lines.append(
    "\n> **Metodologi:** Analisis dilakukan dari data evaluasi yang sudah ada. "
    "Karena data waktu eksekusi aktual tidak tersimpan di file evaluasi, "
    "analisis menggunakan **proxy metrics** yang berkorelasi dengan beban komputasi:\n"
    "> - **Panjang Konteks (ctx_len):** panjang string data yang dikembalikan DB → proxy beban SQL\n"
    "> - **Panjang Jawaban (ans_len):** panjang teks respons LLM → proxy beban generation\n"
    "> - **Skor Faithfulness & Answer Relevancy:** kualitas output dari RAGAS evaluation\n"
)

# ── Tabel 1: Satu pertanyaan representatif per intent ────────────────────────
lines.append("## 1. Pertanyaan Representatif per Intent\n")
lines.append("| Intent | Pertanyaan | Faithfulness | Answer Relevancy |")
lines.append("|--------|------------|:------------:|:----------------:|")
for intent in INTENT_ORDER:
    sub = df[df["intent_label"] == intent]
    if sub.empty:
        continue
    row = sub.iloc[0]
    q_short = row["question"][:60] + "…" if len(str(row["question"])) > 60 else row["question"]
    faith = f"{row['faithfulness']:.3f}" if pd.notna(row["faithfulness"]) else "—"
    relev = f"{row['answer_relevancy']:.3f}" if pd.notna(row["answer_relevancy"]) else "—"
    lines.append(f"| `{intent}` | {q_short} | {faith} | {relev} |")

# ── Tabel 2: Proxy metrics per intent ────────────────────────────────────────
lines.append("\n## 2. Rata-rata Proxy Metrics per Intent\n")
lines.append("*(Ukuran konteks dan jawaban sebagai indikator beban komputasi)*\n")
lines.append("| Intent | Avg Ctx Len (char) | Avg Ans Len (char) | Avg Faithfulness | Avg Relevancy | Keterangan SQL |")
lines.append("|--------|:-----------------:|:-----------------:|:----------------:|:-------------:|----------------|")

intent_metrics = {}
for intent in INTENT_ORDER:
    sub = df[df["intent_label"] == intent]
    if sub.empty:
        continue
    ctx  = sub["ctx_len"].mean()
    ans  = sub["ans_len"].mean()
    faith = sub["faithfulness"].mean()
    relev = sub["answer_relevancy"].mean()
    intent_metrics[intent] = {"ctx": ctx, "ans": ans, "faith": faith, "relev": relev}
    # Beri tanda beban tinggi
    ctx_mark = "🔴" if ctx > 1000 else ("🟡" if ctx > 200 else "🟢")
    ans_mark = "🔴" if ans > 700 else ("🟡" if ans > 350 else "🟢")
    lines.append(
        f"| `{intent}` | {ctx_mark} **{ctx:.0f}** | {ans_mark} **{ans:.0f}** | {faith:.3f} | {relev:.3f} | {INTENT_NOTES.get(intent, '')} |"
    )

lines.append("\n> 🟢 Ringan &nbsp; 🟡 Sedang &nbsp; 🔴 Berat (estimasi beban)\n")

# ── Tabel 3: Per kompleksitas ──────────────────────────────────────────────────
lines.append("## 3. Proxy Metrics per Tingkat Kompleksitas\n")
lines.append("*(Apakah pertanyaan yang lebih kompleks menghasilkan konteks dan jawaban yang lebih panjang?)*\n")
lines.append("| Kompleksitas | Definisi | Avg Ctx Len | Avg Ans Len | Avg Faithfulness | Avg Relevancy | Δ Ctx vs Simple |")
lines.append("|-------------|----------|:-----------:|:-----------:|:----------------:|:-------------:|:---------------:|")

baseline_ctx = None
complexity_metrics = {}
for comp in COMPLEXITY_ORDER:
    sub = df[df["complexity"] == comp]
    if sub.empty:
        lines.append(f"| **{comp}** | {COMPLEXITY_DEF.get(comp, '')} | — | — | — | — | — |")
        continue
    ctx   = sub["ctx_len"].mean()
    ans   = sub["ans_len"].mean()
    faith = sub["faithfulness"].mean()
    relev = sub["answer_relevancy"].mean()
    complexity_metrics[comp] = {"ctx": ctx, "ans": ans, "faith": faith, "relev": relev, "n": len(sub)}
    if baseline_ctx is None:
        baseline_ctx = ctx
        delta_str = "—"
    else:
        delta = ctx - baseline_ctx
        sign = "+" if delta >= 0 else ""
        delta_str = f"{sign}{delta:.0f} char"
    lines.append(
        f"| **{comp}** | {COMPLEXITY_DEF.get(comp, '')} | {ctx:.0f} | {ans:.0f} | {faith:.3f} | {relev:.3f} | {delta_str} |"
    )

# ── Tabel 4: Detail semua pertanyaan ──────────────────────────────────────────
lines.append("\n## 4. Detail Semua Pertanyaan (per Intent, 5 Sampel)\n")
lines.append("| Intent | Kompleksitas | Pertanyaan | Ctx Len | Ans Len | Faith. | Relev. |")
lines.append("|--------|-------------|------------|:-------:|:-------:|:------:|:------:|")
for intent in INTENT_ORDER:
    sub = df[df["intent_label"] == intent].reset_index(drop=True)
    for _, row in sub.iterrows():
        q_short = str(row["question"])[:55] + "…" if len(str(row["question"])) > 55 else row["question"]
        faith = f"{row['faithfulness']:.3f}" if pd.notna(row["faithfulness"]) else "—"
        relev = f"{row['answer_relevancy']:.3f}" if pd.notna(row["answer_relevancy"]) else "—"
        lines.append(
            f"| `{intent}` | {row['complexity']} | {q_short} | {row['ctx_len']} | {row['ans_len']} | {faith} | {relev} |"
        )

# ── Analisis kesimpulan ────────────────────────────────────────────────────────
lines.append("\n## 5. Analisis & Kesimpulan\n")

# Intent dengan ctx terbesar/terkecil
if intent_metrics:
    heaviest = max(intent_metrics, key=lambda i: intent_metrics[i]["ctx"])
    lightest = min(intent_metrics, key=lambda i: intent_metrics[i]["ctx"])

    lines.append("### 5.1 Intent dengan Beban Data Terbesar & Terkecil\n")
    lines.append(f"- **Beban konteks terbesar:** `{heaviest}` — rata-rata **{intent_metrics[heaviest]['ctx']:.0f} char** konteks")
    lines.append(f"- **Beban konteks terkecil:** `{lightest}` — rata-rata **{intent_metrics[lightest]['ctx']:.0f} char** konteks")
    ratio = intent_metrics[heaviest]["ctx"] / max(intent_metrics[lightest]["ctx"], 1)
    lines.append(f"- **Rasio:** `{heaviest}` menghasilkan ~{ratio:.1f}× lebih banyak data dari `{lightest}`\n")

    lines.append("### 5.2 Apakah Kompleksitas Mempengaruhi Beban Eksekusi?\n")
    if "simple" in complexity_metrics and "complex" in complexity_metrics:
        ctx_delta = complexity_metrics["complex"]["ctx"] - complexity_metrics["simple"]["ctx"]
        ans_delta = complexity_metrics["complex"]["ans"] - complexity_metrics["simple"]["ans"]
        ctx_pct   = (ctx_delta / max(complexity_metrics["simple"]["ctx"], 1)) * 100
        if abs(ctx_pct) < 20:
            verdict = "**Tidak signifikan.** Perbedaan panjang konteks antara simple dan complex < 20%."
        elif ctx_pct > 0:
            verdict = f"**Ya, berpengaruh.** Pertanyaan complex menghasilkan konteks {ctx_pct:.0f}% lebih panjang dari simple."
        else:
            verdict = f"**Tidak linear.** Pertanyaan complex justru menghasilkan konteks lebih pendek ({ctx_pct:.0f}%)."
        lines.append(verdict)
        lines.append(f"\n| Metrik | Simple | Complex | Selisih |")
        lines.append(f"|--------|:------:|:-------:|:-------:|")
        sign = "+" if ctx_delta >= 0 else ""
        lines.append(f"| Avg Ctx Len | {complexity_metrics['simple']['ctx']:.0f} | {complexity_metrics['complex']['ctx']:.0f} | {sign}{ctx_delta:.0f} char |")
        sign = "+" if ans_delta >= 0 else ""
        lines.append(f"| Avg Ans Len | {complexity_metrics['simple']['ans']:.0f} | {complexity_metrics['complex']['ans']:.0f} | {sign}{ans_delta:.0f} char |")

lines.append("\n### 5.3 Estimasi Komponen Waktu Eksekusi per Intent\n")
lines.append("Berdasarkan arsitektur sistem (2–4 Groq API call + 1 DB query):\n")
lines.append("| Intent | Groq Intent Parse | DB Query | Groq Answer Gen | Groq Correction | Estimasi Total |")
lines.append("|--------|:-----------------:|:--------:|:---------------:|:---------------:|:--------------:|")
TIMING_EST = {
    "count":     ("~400 ms", "~100 ms", "~500 ms", "kadang",  "~1.0–2.0 detik"),
    "average":   ("~400 ms", "~100 ms", "~500 ms", "kadang",  "~1.0–2.0 detik"),
    "max":       ("~400 ms", "~100 ms", "~600 ms", "kadang",  "~1.1–2.1 detik"),
    "min":       ("~400 ms", "~100 ms", "~500 ms", "kadang",  "~1.0–2.0 detik"),
    "list":      ("~400 ms", "~200 ms", "~800 ms", "kadang",  "~1.4–2.5 detik"),
    "trend":     ("~400 ms", "~500 ms", "~1200 ms","kadang",  "~2.1–3.5 detik"),
    "knowledge": ("~400 ms", "— (skip)","~700 ms", "tidak",   "~1.1–1.5 detik"),
}
for intent in INTENT_ORDER:
    est = TIMING_EST.get(intent, ("?", "?", "?", "?", "?"))
    lines.append(f"| `{intent}` | {est[0]} | {est[1]} | {est[2]} | {est[3]} | **{est[4]}** |")

lines.append(
    "\n> **Catatan:** Groq API (llama-3.1-8b-instant) adalah **bottleneck utama** — "
    "setiap request memanggil Groq 2–4× (intent parse + answer gen + opsional correction). "
    "Beban DB relatif kecil kecuali untuk `trend` yang melakukan GROUP BY pada jutaan baris."
)

# ── Tulis file ────────────────────────────────────────────────────────────────
md_content = "\n".join(lines)
with open(md_path, "w", encoding="utf-8") as f:
    f.write(md_content)

print(f"[DONE] Laporan disimpan → {md_path}")
print(f"       Total baris data: {len(df)}")
print(f"       Intent unik: {df['intent_label'].nunique()}")
