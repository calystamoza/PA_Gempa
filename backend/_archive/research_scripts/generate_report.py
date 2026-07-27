import pandas as pd
import re

df = pd.read_csv('evaluation_results_v3.csv')

def clean(text, maxlen=140):
    if pd.isna(text):
        return ''
    s = str(text).replace('\n', ' ')
    s = re.sub(r'\*\*|__|\*|_|`', '', s)
    if len(s) > maxlen:
        s = s[:maxlen] + '...'
    return s.strip()

def score_color(score):
    if pd.isna(score): return '#9ca3af'
    if score >= 0.8: return '#16a34a'
    if score >= 0.5: return '#d97706'
    return '#dc2626'

def score_bg(score):
    if pd.isna(score): return '#f3f4f6'
    if score >= 0.8: return '#dcfce7'
    if score >= 0.5: return '#fef3c7'
    return '#fee2e2'

def faith_analisis(score, intent):
    if pd.isna(score): return 'Evaluasi gagal (NaN).'
    if intent == 'knowledge':
        return 'Pertanyaan umum di luar konteks data. Bot menjawab dari pengetahuan seismologi umum, bukan dari retrieved context.'
    if score >= 0.9: return 'Jawaban mengutip fakta secara akurat dan konsisten sesuai retrieved context.'
    elif score >= 0.5: return 'Fakta utama benar, namun terdapat tambahan kalimat pembuka/penutup yang tidak bersumber dari konteks.'
    elif score > 0: return 'Hanya sebagian kecil pernyataan yang dapat dilacak ke konteks, sisanya merupakan elaborasi bebas.'
    else: return 'Tidak ada pernyataan yang bersumber dari konteks data (halusinasi eksternal).'

def rel_analisis(score, intent):
    if pd.isna(score): return 'Evaluasi gagal (NaN).'
    if score >= 0.9: return 'Jawaban sangat fokus dan langsung menjawab inti pertanyaan.'
    elif score >= 0.7: return 'Jawaban relevan, namun memuat beberapa detail tambahan yang kurang esensial.'
    elif score >= 0.4: return 'Jawaban kurang spesifik, sedikit melebar dari tujuan asli pertanyaan.'
    else: return 'Jawaban tidak cukup relevan dengan pertanyaan yang diajukan.'

intents_order = ['count', 'average', 'max', 'min', 'list', 'trend', 'knowledge']
intent_colors = {
    'count': '#3b82f6',
    'average': '#8b5cf6',
    'max': '#ef4444',
    'min': '#06b6d4',
    'list': '#f59e0b',
    'trend': '#10b981',
    'knowledge': '#ec4899',
}

# One representative row per intent
rows = []
for intent in intents_order:
    group = df[df['intent_label'] == intent]
    if len(group) > 0:
        rows.append(group.iloc[0])

def make_table_rows(rows, metric, analisis_fn):
    html = ''
    for no, row in enumerate(rows, start=1):
        q = clean(row['question'], 80)
        ans = clean(row['answer'], 140)
        score = row[metric]
        intent = row['intent_label']
        analisis = analisis_fn(score, intent)
        score_str = f'{score:.2f}' if not pd.isna(score) else 'N/A'
        color = score_color(score)
        bg = score_bg(score)
        ic = intent_colors.get(intent, '#6b7280')
        html += f'''
        <tr>
            <td class="no">{no}</td>
            <td class="question">{q}</td>
            <td><span class="badge" style="background:{ic}">{intent}</span></td>
            <td><span class="score-pill" style="background:{bg};color:{color}">{score_str}</span></td>
            <td class="snippet">{ans}</td>
            <td class="analisis">{analisis}</td>
        </tr>'''
    return html

faith_rows = make_table_rows(rows, 'faithfulness', faith_analisis)
rel_rows = make_table_rows(rows, 'answer_relevancy', rel_analisis)

html = f'''<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Laporan Evaluasi RAGAS</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Inter', sans-serif;
    background: #f8fafc;
    color: #1e293b;
    padding: 40px 32px;
  }}

  h1 {{
    font-size: 1.8rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 6px;
  }}

  .subtitle {{
    color: #64748b;
    font-size: 0.9rem;
    margin-bottom: 40px;
  }}

  .section {{
    margin-bottom: 48px;
  }}

  h2 {{
    font-size: 1.15rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .section-desc {{
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 14px;
  }}

  .table-wrap {{
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.83rem;
  }}

  thead tr {{
    background: #0f172a;
    color: #fff;
  }}

  thead th {{
    padding: 12px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }}

  tbody tr {{
    background: #fff;
    border-bottom: 1px solid #f1f5f9;
    transition: background 0.15s;
  }}

  tbody tr:hover {{
    background: #f8fafc;
  }}

  tbody tr:last-child {{
    border-bottom: none;
  }}

  td {{
    padding: 11px 14px;
    vertical-align: top;
    line-height: 1.5;
  }}

  td.no {{
    width: 40px;
    text-align: center;
    font-weight: 600;
    color: #94a3b8;
  }}

  td.question {{
    font-weight: 500;
    color: #0f172a;
    min-width: 220px;
    max-width: 260px;
  }}

  td.snippet {{
    color: #475569;
    font-size: 0.78rem;
    min-width: 220px;
    max-width: 280px;
    font-style: italic;
  }}

  td.analisis {{
    color: #334155;
    font-size: 0.8rem;
    min-width: 200px;
  }}

  .badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    color: #fff;
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
  }}

  .score-pill {{
    display: inline-block;
    padding: 3px 12px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.85rem;
    white-space: nowrap;
  }}

  .legend {{
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 10px;
    font-size: 0.78rem;
  }}

  .legend-item {{
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  .dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }}
</style>
</head>
<body>

<h1>Laporan Evaluasi RAGAS</h1>
<p class="subtitle">Dataset: eval_dataset_v2.json &nbsp;|&nbsp; 35 pertanyaan &nbsp;|&nbsp; 7 intent (5 soal/intent) &nbsp;|&nbsp; Metrik: Faithfulness &amp; Answer Relevancy</p>

<div class="section">
  <h2>📊 Tabel 1 — Faithfulness <small style="font-weight:400;color:#64748b;font-size:0.85rem">(Kesetiaan pada Data Konteks)</small></h2>
  <p class="section-desc">Mengukur apakah jawaban bot murni bersumber dari retrieved context, bukan halusinasi. Skor 1.00 = seluruh pernyataan dapat dilacak ke konteks.</p>
  <div class="legend">
    <div class="legend-item"><div class="dot" style="background:#16a34a"></div> Baik (≥ 0.80)</div>
    <div class="legend-item"><div class="dot" style="background:#d97706"></div> Cukup (0.50–0.79)</div>
    <div class="legend-item"><div class="dot" style="background:#dc2626"></div> Kurang (< 0.50)</div>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>No</th>
          <th>Pertanyaan Uji</th>
          <th>Intent</th>
          <th>Skor</th>
          <th>Jawaban Bot (Snippet)</th>
          <th>Analisis Faktual</th>
        </tr>
      </thead>
      <tbody>
        {faith_rows}
      </tbody>
    </table>
  </div>
</div>

<div class="section">
  <h2>🎯 Tabel 2 — Answer Relevancy <small style="font-weight:400;color:#64748b;font-size:0.85rem">(Relevansi Jawaban)</small></h2>
  <p class="section-desc">Mengukur seberapa fokus jawaban bot pada inti pertanyaan. Skor 1.00 = jawaban sangat relevan dan tidak melebar ke topik lain.</p>
  <div class="legend">
    <div class="legend-item"><div class="dot" style="background:#16a34a"></div> Baik (≥ 0.80)</div>
    <div class="legend-item"><div class="dot" style="background:#d97706"></div> Cukup (0.50–0.79)</div>
    <div class="legend-item"><div class="dot" style="background:#dc2626"></div> Kurang (< 0.50)</div>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>No</th>
          <th>Pertanyaan Uji</th>
          <th>Intent</th>
          <th>Skor</th>
          <th>Jawaban Bot (Snippet)</th>
          <th>Analisis Relevansi</th>
        </tr>
      </thead>
      <tbody>
        {rel_rows}
      </tbody>
    </table>
  </div>
</div>

</body>
</html>'''

with open('Laporan_Evaluasi_RAGAS.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Selesai! File Laporan_Evaluasi_RAGAS.html berhasil dibuat.')
