import pandas as pd
df = pd.read_csv('evaluation_results_v3.csv')
intents = ['count', 'average', 'max', 'min', 'list', 'trend', 'knowledge']
for intent in intents:
    grp = df[df['intent_label'] == intent]
    f = grp['faithfulness'].mean()
    ar = grp['answer_relevancy'].mean()
    print(f'{intent:12} | F: {f:.4f} | AR: {ar:.4f} | (n={len(grp)})')

f_total = df['faithfulness'].mean()
ar_total = df['answer_relevancy'].mean()
print(f'TOTAL        | F: {f_total:.4f} | AR: {ar_total:.4f}')
