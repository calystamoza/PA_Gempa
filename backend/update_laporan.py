import pandas as pd
import re

df = pd.read_csv('_archive/evaluation/evaluation_results_v3.csv')

def clean_full(text):
    if pd.isna(text): return ''
    s = str(text)
    # Ganti newline dengan spasi agar tidak merusak baris tabel markdown
    s = s.replace('\n', '<br>')
    # Escape pipe character agar tidak merusak kolom tabel
    s = s.replace('|', '&#124;')
    # Hapus beberapa karakter markdown yang rentan merusak layout jika tidak tertutup
    s = re.sub(r'[*_`]', '', s)
    return s.strip()

def faith_analisis(score, intent):
    if pd.isna(score): return 'Evaluasi gagal (NaN).'
    if intent == 'knowledge': return 'Menjawab dari pengetahuan umum, tidak ada di konteks data.'
    if score >= 0.9: return 'Seluruh fakta bersumber dari retrieved context.'
    elif score >= 0.5: return 'Fakta utama benar, ada tambahan narasi (Insight) di luar konteks.'
    elif score > 0: return 'Hanya sebagian kecil pernyataan yang dapat dilacak ke konteks.'
    else: return 'Tidak ada pernyataan yang bersumber dari konteks data.'

def rel_analisis(score, intent):
    if pd.isna(score): return 'Evaluasi gagal (NaN).'
    if score >= 0.9: return 'Jawaban sangat fokus dan langsung menjawab inti pertanyaan.'
    elif score >= 0.7: return 'Relevan, namun memuat beberapa detail tambahan yang kurang esensial.'
    elif score >= 0.4: return 'Kurang spesifik, melebar dari tujuan asli pertanyaan.'
    else: return 'Jawaban tidak relevan dengan pertanyaan yang diajukan.'

intents_order = ['count', 'average', 'max', 'min', 'list', 'trend', 'knowledge']
rows = []
for intent in intents_order:
    group = df[df['intent_label'] == intent]
    if len(group) > 0:
        rows.append(group.iloc[0])

# --- SUMMARY ANALYSIS TEXTS ---
summary_analysis = {
    'count': "Sangat relevan menjawab jumlah (AR: 0.79), namun Faithfulness rendah (0.27) karena bot selalu menambahkan 'Insight Singkat' yang merupakan halusinasi naratif (tidak ada di tabel).",
    'average': "Sukses mengekstraksi nilai agregasi rata-rata, namun kembali terhukum di Faithfulness (0.37) karena bot memberikan interpretasi atau opini bebas terhadap angka tersebut.",
    'max': "Mampu menyajikan rekor tertinggi dengan sangat fokus (AR: 0.84). Faithfulness membaik (0.55) karena porsi data faktual lebih mendominasi daripada basa-basi tambahan.",
    'min': "Salah satu performa terbaik. Sangat tajam mencari rekor terendah (AR: 0.89). Karena jawabannya ringkas dan lugas, Faithfulness-nya juga cukup tinggi (0.69).",
    'list': "Faithfulness tinggi (0.77) karena bot menyajikan data dalam bentuk Tabel Markdown murni yang disalin langsung dari konteks tanpa banyak merangkai paragraf opini.",
    'trend': "Faithfulness tertinggi (0.93) karena bot dipaksa meringkas data deret waktu yang sangat padat sehingga tidak ada celah untuk berhalusinasi. Namun AR agak rendah (0.71) karena penjelasan bot terlalu panjang dan bertele-tele.",
    'knowledge': "Pertanyaan teori umum (zero-shot). Bot menjawab menggunakan basis pengetahuannya sendiri karena data teori tidak ada di database, sehingga Faithfulness-nya hancur (0.09)."
}

with open(r'C:\Users\calys\.gemini\antigravity-ide\brain\dbe3c528-106a-4655-ae60-d099c1e8bc05\laporan_evaluasi_ragas.md', 'w', encoding='utf-8') as f:
    f.write('# Laporan Evaluasi RAGAS (1 Contoh per Intent + Jawaban Lengkap)\n\n')
    f.write('**Dataset:** eval_dataset_v2.json | **35 pertanyaan** | **7 intent** × **5 soal**\n\n---\n\n')

    # FAITHFULNESS
    f.write('## Tabel 1 — Faithfulness (Kesetiaan pada Data Konteks)\n\n')
    f.write('> Skor mengukur apakah jawaban bot murni berasal dari retrieved context, bukan pengetahuan luar.\n\n')
    f.write('| No | Pertanyaan Uji | Intent | Skor | Jawaban Bot (Lengkap) | Analisis Faktual |\n')
    f.write('|:--:|:---|:--:|:--:|:---|:---|\n')
    for no, row in enumerate(rows, start=1):
        q = clean_full(row['question'])
        ans = clean_full(row['answer'])
        score = row['faithfulness']
        intent = row['intent_label']
        analisis = faith_analisis(score, intent)
        score_str = f'{score:.2f}' if not pd.isna(score) else 'NaN'
        f.write(f'| {no} | {q} | `{intent}` | **{score_str}** | {ans} | {analisis} |\n')

    f.write('\n---\n\n')

    # ANSWER RELEVANCY
    f.write('## Tabel 2 — Answer Relevancy (Relevansi Jawaban)\n\n')
    f.write('> Skor mengukur seberapa fokus dan relevan jawaban bot terhadap pertanyaan yang diajukan.\n\n')
    f.write('| No | Pertanyaan Uji | Intent | Skor | Jawaban Bot (Lengkap) | Analisis Relevansi |\n')
    f.write('|:--:|:---|:--:|:--:|:---|:---|\n')
    for no, row in enumerate(rows, start=1):
        q = clean_full(row['question'])
        ans = clean_full(row['answer'])
        score = row['answer_relevancy']
        intent = row['intent_label']
        analisis = rel_analisis(score, intent)
        score_str = f'{score:.2f}' if not pd.isna(score) else 'NaN'
        f.write(f'| {no} | {q} | `{intent}` | **{score_str}** | {ans} | {analisis} |\n')

    f.write('\n---\n\n')
    
    # SUMMARY
    f.write('## Tabel 3 — Ringkasan Rata-rata & Analisis Per Intent\n\n')
    f.write('> Angka merupakan rata-rata dari 5 pertanyaan pengujian per masing-masing intent.\n\n')
    f.write('| Intent | Rata-rata Faithfulness | Rata-rata Answer Relevancy | Analisis Performa Intent |\n')
    f.write('|:---|:--:|:--:|:---|\n')
    for intent in intents_order:
        grp = df[df['intent_label'] == intent]
        f_avg = grp['faithfulness'].mean()
        ar_avg = grp['answer_relevancy'].mean()
        analisis = summary_analysis[intent]
        f.write(f'| `{intent}` | **{f_avg:.4f}** | **{ar_avg:.4f}** | {analisis} |\n')
        
    f_total = df['faithfulness'].mean()
    ar_total = df['answer_relevancy'].mean()
    f.write(f'| **Total (Overall)** | **{f_total:.4f}** | **{ar_total:.4f}** | Rata-rata keseluruhan sistem RAG. |\n')

print('Selesai update.')
