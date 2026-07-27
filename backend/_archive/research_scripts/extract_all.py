import pandas as pd
import re

df = pd.read_csv('evaluation_results_v3.csv')

def clean(text, maxlen=120):
    if pd.isna(text): return ''
    s = str(text).replace('\n', ' ')
    s = re.sub(r'[|*_`]', '', s)
    s = re.sub(r'[^\x00-\x7F\u00C0-\u024F]', '', s)  # strip emoji
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) > maxlen:
        s = s[:maxlen] + '...'
    return s

def faith_label(score, intent):
    if pd.isna(score): return 'N/A'
    if intent == 'knowledge':
        return 'Menjawab dari pengetahuan umum, tidak ada di konteks data.'
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

with open('report_all.txt', 'w', encoding='utf-8') as f:
    f.write('=== FAITHFULNESS (35 Pertanyaan) ===\n')
    for idx, row in df.iterrows():
        q = clean(row['question'], 80)
        ans = clean(row['answer'], 120)
        intent = str(row['intent_label'])
        score = row['faithfulness']
        score_str = f'{score:.2f}' if not pd.isna(score) else 'NaN'
        label = faith_label(score, intent)
        f.write(f'{idx+1}|{q}|{intent}|{score_str}|{ans}|{label}\n')

    f.write('\n=== ANSWER RELEVANCY (35 Pertanyaan) ===\n')
    for idx, row in df.iterrows():
        q = clean(row['question'], 80)
        ans = clean(row['answer'], 120)
        intent = str(row['intent_label'])
        score = row['answer_relevancy']
        score_str = f'{score:.2f}' if not pd.isna(score) else 'NaN'
        label = rel_label(score)
        f.write(f'{idx+1}|{q}|{intent}|{score_str}|{ans}|{label}\n')

print('Done')
