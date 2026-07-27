"""
Analisis waktu eksekusi dari live_eval_results_20260702_183012.csv
"""
import pandas as pd

df = pd.read_csv('_archive/evaluation/live_eval_results_20260702_183012.csv')

print('=' * 60)
print('ANALISIS WAKTU EKSEKUSI GEMPABOT')
print('Sumber: live_eval_results_20260702_183012.csv')
print('Total sampel:', len(df))
print('=' * 60)

# ─── Per Intent ───────────────────────────────────────────────
print()
print('## 1. Rata-rata Waktu Eksekusi per Intent')
print()
header = "{:<12} {:>3} {:>9} {:>9} {:>9} {:>8}".format('Intent','N','Avg(s)','Min(s)','Max(s)','Std(s)')
print(header)
print('-' * 54)

intent_order = ['count','average','max','min','list','trend','knowledge']
intent_stats = {}
for intent in intent_order:
    sub = df[df['expected_intent'] == intent]['response_time_s']
    if sub.empty:
        continue
    avg = sub.mean()
    intent_stats[intent] = avg
    row = "{:<12} {:>3} {:>9.2f} {:>9.2f} {:>9.2f} {:>8.2f}".format(
        intent, len(sub), avg, sub.min(), sub.max(), sub.std()
    )
    print(row)

slowest = max(intent_stats, key=intent_stats.get)
fastest = min(intent_stats, key=intent_stats.get)
print()
print(f'  Tercepat : {fastest} ({intent_stats[fastest]:.2f} s)')
print(f'  Terlambat: {slowest} ({intent_stats[slowest]:.2f} s)')
print(f'  Selisih  : {intent_stats[slowest] - intent_stats[fastest]:.2f} s')

# ─── Per Complexity ────────────────────────────────────────────
print()
print('## 2. Rata-rata Waktu Eksekusi per Kompleksitas')
print()
header2 = "{:<12} {:>3} {:>9} {:>9} {:>9}".format('Kompleksitas','N','Avg(s)','Min(s)','Max(s)')
print(header2)
print('-' * 46)

comp_stats = {}
for comp in ['simple','medium','complex']:
    sub = df[df['difficulty'] == comp]['response_time_s']
    if sub.empty:
        continue
    avg = sub.mean()
    comp_stats[comp] = avg
    print("{:<12} {:>3} {:>9.2f} {:>9.2f} {:>9.2f}".format(
        comp, len(sub), avg, sub.min(), sub.max()
    ))

if 'simple' in comp_stats and 'complex' in comp_stats:
    delta = comp_stats['complex'] - comp_stats['simple']
    pct = (delta / comp_stats['simple']) * 100
    print()
    print(f'  Delta complex vs simple: {delta:+.2f} s ({pct:+.1f}%)')
    if abs(pct) < 15:
        print('  --> Kompleksitas TIDAK signifikan mempengaruhi waktu.')
    elif delta > 0:
        print('  --> Kompleksitas BERPENGARUH: semakin kompleks semakin lambat.')
    else:
        print('  --> Kompleksitas tidak linear: complex lebih cepat dari simple.')

# ─── Tabel silang ────────────────────────────────────────────
print()
print('## 3. Tabel Silang Intent x Kompleksitas (Avg seconds)')
print()
pivot = df.pivot_table(values='response_time_s', index='expected_intent', columns='difficulty', aggfunc='mean')
print(pivot.round(2).to_string())

# ─── Semua baris detail ───────────────────────────────────────
print()
print('## 4. Detail Semua Pertanyaan')
print()
for _, row in df.iterrows():
    q = str(row['question'])[:55]
    print("{:>2}. [{:<10}] ({:<7}) {:>6.2f}s | {}".format(
        int(row['no']), row['expected_intent'], row['difficulty'],
        row['response_time_s'], q
    ))
