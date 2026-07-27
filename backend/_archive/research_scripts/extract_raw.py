import pandas as pd
import re

df = pd.read_csv('evaluation_results_v3.csv')

def clean(text, maxlen=100):
    if pd.isna(text): return ''
    s = str(text).replace('\n', ' ')
    # Remove emoji, pipe, asterisk, backtick, underscore
    s = re.sub(r'[|*_`]', '', s)
    s = re.sub(r'[^\x00-\x7F\u00C0-\u024F\u0100-\u017F]', '', s)  # strip emoji/non-latin
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) > maxlen:
        s = s[:maxlen] + '...'
    return s

intents = ['count', 'average', 'max', 'min', 'list', 'trend', 'knowledge']

with open('report_raw.txt', 'w', encoding='utf-8') as out:
    out.write('=== FAITHFULNESS ===\n')
    for i, intent in enumerate(intents, 1):
        row = df[df['intent_label'] == intent].iloc[0]
        q = clean(row['question'], 70)
        ans = clean(row['answer'], 110)
        sc = row['faithfulness']
        out.write(f'{i}||{q}||{intent}||{sc:.2f}||{ans}\n')

    out.write('\n=== ANSWER RELEVANCY ===\n')
    for i, intent in enumerate(intents, 1):
        row = df[df['intent_label'] == intent].iloc[0]
        q = clean(row['question'], 70)
        ans = clean(row['answer'], 110)
        sc = row['answer_relevancy']
        out.write(f'{i}||{q}||{intent}||{sc:.2f}||{ans}\n')

print('Done')
