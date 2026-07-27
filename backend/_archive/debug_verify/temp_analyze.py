import json
import pandas as pd

with open('eval_dataset_v2.json', 'r', encoding='utf-8') as f:
    ds = json.load(f)

df = pd.read_csv('evaluation_results_v2.csv')

scores = []
for i, q in enumerate(ds['question']):
    matches = df[df['user_input'] == q]
    if len(matches) > 0:
        valid_scores = matches['faithfulness'].dropna()
        if len(valid_scores) > 0:
            score = valid_scores.max()
        else:
            score = float('nan')
    else:
        score = float('nan')
    scores.append(score)

intents = ds['intent_label']
results = pd.DataFrame({'intent': intents, 'score': scores})
print('=== FINAL FAITHFULNESS PER INTENT (35 KASUS) ===')
for intent in ['count','average','max','min','list','trend','knowledge']:
    grp = results[results['intent'] == intent]['score']
    valid = grp.dropna()
    avg = valid.mean() if len(valid) > 0 else 0.0
    print(f'{intent:12s}: {avg:.4f} (Valid: {len(valid)}/5)')

print(f'\nOVERALL AVG: {results["score"].dropna().mean():.4f}')
print(f'Total Valid: {results["score"].notna().sum()}/35')

for i, (q, s) in enumerate(zip(ds['question'], scores)):
    if pd.isna(s):
        print(f'Missing/Failed: [{i+1}] {q}')
