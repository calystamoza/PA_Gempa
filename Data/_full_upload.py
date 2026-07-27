import os, sys, time, urllib.parse
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv("e:/COOLYEAH/PA/gempa/.env")
DATABASE_URL = os.getenv("DATABASE_URL")

url = urllib.parse.urlparse(DATABASE_URL)
conn = psycopg2.connect(
    dbname=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port,
    sslmode="require",
)
conn.autocommit = False
cur = conn.cursor()

print("=" * 60)
print("  TRUNCATE + BULK INSERT: earthquakes")
print("=" * 60)

# ── STEP 1: TRUNCATE ───────────────────────────────────────────
print("\n[STEP 1] Truncate tabel earthquakes ...")
cur.execute("TRUNCATE TABLE earthquakes RESTART IDENTITY;")
conn.commit()
print("  OK - tabel dikosongkan")

# ── Helper: bulk insert dengan execute_values ──────────────────
def bulk_insert(df, label):
    print(f"\n[{label}] Menyiapkan data ({len(df):,} baris) ...")

    rows = []
    for _, r in df.iterrows():
        rows.append((
            str(r["id"]),
            str(r["place"]) if pd.notna(r.get("place", None)) else str(r.get("province", "")),
            str(r["date"]) if pd.notna(r["date"]) else None,
            int(r["month"]) if pd.notna(r["month"]) else None,
            str(r["month_name"]) if pd.notna(r["month_name"]) else None,
            int(r["year"]) if pd.notna(r["year"]) else None,
            float(r["latitude"]) if pd.notna(r["latitude"]) else None,
            float(r["longitude"]) if pd.notna(r["longitude"]) else None,
            float(r["magnitude"]) if pd.notna(r["magnitude"]) else None,
            float(r["depth"]) if pd.notna(r["depth"]) else None,
            str(r["depth_category"]) if pd.notna(r.get("depth_category", None)) else None,
            str(r["time"]) if pd.notna(r["time"]) else None,
        ))

    CHUNK = 1000
    total = len(rows)
    inserted = 0
    skipped = 0
    t0 = time.time()

    for i in range(0, total, CHUNK):
        chunk = rows[i:i+CHUNK]
        try:
            result = execute_values(cur,
                """
                INSERT INTO earthquakes
                    (id, place, date, month, month_name, year,
                     latitude, longitude, magnitude, depth, depth_category, time)
                VALUES %s
                ON CONFLICT (id) DO NOTHING
                RETURNING id
                """,
                chunk,
                fetch=True,
            )
            conn.commit()
            ins = len(result)
            sk  = len(chunk) - ins
            inserted += ins
            skipped  += sk
            pct = (i + len(chunk)) / total * 100
            elapsed = time.time() - t0
            print(f"  [{pct:5.1f}%] chunk {i//CHUNK+1}: +{ins} inserted, {sk} skip | elapsed {elapsed:.0f}s")
        except Exception as e:
            conn.rollback()
            print(f"  [ERR] chunk {i//CHUNK+1}: {e}")

    print(f"  DONE: {inserted:,} inserted, {skipped:,} skipped ({time.time()-t0:.1f}s total)")
    return inserted, skipped

# ── STEP 2: data_gempa_processed.csv ──────────────────────────
print("\n[STEP 2] Load data_gempa_processed.csv ...")
df1 = pd.read_csv("e:/COOLYEAH/PA/gempa/Data/data_gempa_processed.csv")
print(f"  Loaded: {len(df1):,} baris | kolom: {list(df1.columns)}")
# rename province -> place jika ada
if "province" in df1.columns and "place" not in df1.columns:
    df1 = df1.rename(columns={"province": "place"})
bulk_insert(df1, "PROCESSED")

# ── STEP 3: add_2025-2026_transformed.csv ─────────────────────
print("\n[STEP 3] Load add_2025-2026_transformed.csv ...")
df2 = pd.read_csv("e:/COOLYEAH/PA/gempa/Data/add_2025-2026_transformed.csv")
print(f"  Loaded: {len(df2):,} baris | kolom: {list(df2.columns)}")

# Hitung last_id dari data yang sudah masuk (dari processed)
last_id = int(df1["id"].astype(int).max())
print(f"  last_id dari processed: {last_id}, ID add mulai dari: {last_id+1}")
# Re-assign ID agar lanjut dari processed
df2 = df2.reset_index(drop=True)
df2["id"] = range(last_id + 1, last_id + 1 + len(df2))

# rename province -> place
if "province" in df2.columns:
    df2 = df2.rename(columns={"province": "place"})

bulk_insert(df2, "ADD 2025-2026")

# ── Verifikasi ────────────────────────────────────────────────
print("\n[VERIFY] Cek total di database ...")
cur.execute("SELECT COUNT(*) FROM earthquakes")
total_db = cur.fetchone()[0]
cur.execute("SELECT MIN(id::int), MAX(id::int) FROM earthquakes")
mn, mx = cur.fetchone()
print(f"  Total rows : {total_db:,}")
print(f"  ID range   : {mn} - {mx}")

cur.execute("SELECT year, COUNT(*) FROM earthquakes GROUP BY year ORDER BY year DESC LIMIT 5")
print("  Recent years:")
for row in cur.fetchall():
    print(f"    {row[0]}: {row[1]:,} rows")

cur.close()
conn.close()
print("\n[DONE] Semua selesai!")
