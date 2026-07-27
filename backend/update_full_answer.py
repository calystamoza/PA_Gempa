import pandas as pd
import re

df = pd.read_csv('_archive/evaluation/evaluation_results_v3.csv')

def clean_full(text):
    if pd.isna(text): return ''
    s = str(text)
    # Ganti newline dengan spasi agar tidak merusak baris tabel markdown
    # Jika ingin ada enter di dalam sel tabel, gunakan <br>
    s = s.replace('\n', '<br>')
    # Escape pipe character agar tidak merusak kolom tabel
    s = s.replace('|', '&#124;')
    # Hapus beberapa karakter markdown yang rentan merusak layout jika tidak tertutup
    s = re.sub(r'[*_`]', '', s)
    return s.strip()

def faith_label(score, intent):
    if pd.isna(score): return 'N/A'
    if intent == 'knowledge': return 'Menjawab dari pengetahuan umum, tidak ada di konteks data.'
    if score >= 0.9: return 'Seluruh fakta bersumber dari retrieved context.'
    elif score >= 0.5: return 'Fakta utama benar, ada tambahan narasi di luar konteks.'
    elif score > 0: return 'Sebagian kecil saja yang bisa dilacak ke konteks.'
    return 'Tidak ada fakta yang bersumber dari konteks.'

def rel_label(score):
    if pd.isna(score): return 'N/A'
    if score >= 0.9: return 'Sangat fokus dan langsung menjawab inti pertanyaan.'
    elif score >= 0.7: return 'Relevan, sedikit tambahan info yang tidak diminta.'
    elif score >= 0.4: return 'Kurang spesifik, sedikit melebar dari pertanyaan.'
    return 'Jawaban tidak relevan dengan pertanyaan.'

with open(r'C:\Users\calys\.gemini\antigravity-ide\brain\dbe3c528-106a-4655-ae60-d099c1e8bc05\laporan_per_pertanyaan.md', 'w', encoding='utf-8') as f:
    f.write('# Laporan Evaluasi RAGAS — Per Pertanyaan (35 Soal) [FULL ANSWER]\n\n')
    f.write('**Dataset:** eval_dataset_v2.json | **35 pertanyaan** | **7 intent** × **5 soal**\n\n---\n\n')

    # FAITHFULNESS
    f.write('## Tabel 1 — Faithfulness (Kesetiaan pada Data Konteks)\n\n')
    f.write('> Skor mengukur apakah jawaban bot murni berasal dari retrieved context, bukan pengetahuan luar.\n\n')
    f.write('| No | Pertanyaan Uji | Intent | Skor | Jawaban Bot (Lengkap) | Analisis |\n')
    f.write('|:--:|:---|:--:|:--:|:---|:---|\n')
    for idx, row in df.iterrows():
        q = clean_full(row['question'])
        ans = clean_full(row['answer'])
        intent = str(row['intent_label'])
        score = row['faithfulness']
        score_str = f'{score:.2f}' if not pd.isna(score) else 'NaN'
        label = faith_label(score, intent)
        f.write(f'| {idx+1} | {q} | {intent} | {score_str} | {ans} | {label} |\n')

    f.write('\n---\n\n')

    # ANSWER RELEVANCY
    f.write('## Tabel 2 — Answer Relevancy (Relevansi Jawaban)\n\n')
    f.write('> Skor mengukur seberapa fokus jawaban bot terhadap pertanyaan yang diajukan.\n\n')
    f.write('| No | Pertanyaan Uji | Intent | Skor | Jawaban Bot (Lengkap) | Analisis |\n')
    f.write('|:--:|:---|:--:|:--:|:---|:---|\n')
    for idx, row in df.iterrows():
        q = clean_full(row['question'])
        ans = clean_full(row['answer'])
        intent = str(row['intent_label'])
        score = row['answer_relevancy']
        score_str = f'{score:.2f}' if not pd.isna(score) else 'NaN'
        label = rel_label(score)
        f.write(f'| {idx+1} | {q} | {intent} | {score_str} | {ans} | {label} |\n')

print('Berhasil update artifact dengan jawaban lengkap.')
