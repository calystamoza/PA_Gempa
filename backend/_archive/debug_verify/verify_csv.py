import csv
with open('live_eval_results_20260702_183012.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        no = int(row['no'])
        if no in [13, 24, 25]:
            sql = row["sql_generated"]
            note = row["sql_note"]
            enotes = row["evaluator_notes"]
            print(f"=== Baris #{no} ===")
            print(f"SQL     : {sql}")
            print(f"SQL Note: {note}")
            print(f"Notes   : {enotes}")
            print()
