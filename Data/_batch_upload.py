import pandas as pd, requests, time

OUTPUT_FILE = "e:/COOLYEAH/PA/gempa/Data/add_2025-2026_transformed.csv"
API_BASE    = "http://localhost:8000"
BATCH_SIZE  = 200

# Baca CSV yang sudah di-transform (ID 1-2477)
df = pd.read_csv(OUTPUT_FILE)
total = len(df)
print(f"[INFO] Total baris: {total}")
print(f"[INFO] Kolom: {list(df.columns)}")
print(f"[INFO] ID range: {df['id'].iloc[0]} - {df['id'].iloc[-1]}")
print()

# Split jadi batch kecil dan upload satu per satu
batches = [df.iloc[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
print(f"[INFO] Total batch: {len(batches)} x {BATCH_SIZE} baris")
print()

success_total = 0
skip_total = 0
fail_total = 0

for idx, batch_df in enumerate(batches):
    batch_file = f"e:/COOLYEAH/PA/gempa/Data/_batch_tmp.csv"
    batch_df.to_csv(batch_file, index=False)
    
    try:
        with open(batch_file, "rb") as f:
            r = requests.post(
                f"{API_BASE}/admin/earthquakes/upload",
                headers={"x-user-role": "admin"},
                files={"file": ("batch.csv", f, "text/csv")},
                timeout=120,
            )
        r.raise_for_status()
        result = r.json()
        s = result.get("success", 0)
        sk = result.get("skipped", 0)
        fa = result.get("failed", 0)
        success_total += s
        skip_total += sk
        fail_total += fa
        
        start_id = batch_df["id"].iloc[0]
        end_id   = batch_df["id"].iloc[-1]
        print(f"  Batch {idx+1:3d}/{len(batches)} [ID {start_id}-{end_id}]: OK={s} skip={sk} fail={fa}")
        
        if result.get("errors"):
            for e in result["errors"][:2]:
                print(f"    ERR: {e}")
    except Exception as e:
        fail_total += len(batch_df)
        print(f"  Batch {idx+1:3d}/{len(batches)}: FAILED - {e}")

print()
print("=" * 50)
print(f"[DONE] Selesai!")
print(f"  Total success : {success_total}")
print(f"  Total skipped : {skip_total}")
print(f"  Total failed  : {fail_total}")
