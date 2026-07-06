"""
Script untuk upload data CSV gempa ke Supabase PostgreSQL.
Jalankan SETELAH setup_db.sql sudah di-run di Supabase.

Usage:
    python upload_csv.py
"""

import os
import sys
import math
import urllib.parse
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CSV_PATH = os.path.join(os.path.dirname(__file__), "../Data/data_gempa_processed.csv")
BATCH_SIZE = 1000


def get_connection():
    url = urllib.parse.urlparse(DATABASE_URL)
    return psycopg2.connect(
        dbname=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode="require",
    )


def clean_val(v):
    """Konversi NaN ke None untuk PostgreSQL NULL."""
    if v is None:
        return None
    try:
        if math.isnan(float(v)):
            return None
    except (TypeError, ValueError):
        pass
    return v


def upload():
    print(f"Reading CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    df.rename(columns={"province": "place"}, inplace=True)
    # Normalisasi depth_category ke lowercase agar konsisten dengan RAG engine
    if "depth_category" in df.columns:
        df["depth_category"] = df["depth_category"].str.lower().str.strip()
    print(f"Total rows: {len(df):,}")

    columns = [
        "id", "place", "date", "month", "month_name",
        "year", "latitude", "longitude", "magnitude", "depth",
        "depth_category", "time",
    ]

    # Pastikan kolom ada di df
    df = df[[c for c in columns if c in df.columns]]

    print(f"Connecting to Supabase...")
    conn = get_connection()
    cur = conn.cursor()

    print(f"Uploading {len(df):,} rows in batch {BATCH_SIZE}...")
    total_uploaded = 0
    total_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[i : i + BATCH_SIZE]
        values = [
            tuple(clean_val(row.get(col)) for col in columns)
            for _, row in batch.iterrows()
        ]

        try:
            execute_values(
                cur,
                f"""
                INSERT INTO earthquakes ({', '.join(columns)})
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET place = EXCLUDED.place
                """,
                values,
            )
            conn.commit()
            total_uploaded += len(batch)
            batch_num = i // BATCH_SIZE + 1
            print(f"  Batch {batch_num}/{total_batches} DONE ({total_uploaded:,}/{len(df):,})")
        except Exception as e:
            conn.rollback()
            print(f"  Error on batch {i//BATCH_SIZE + 1}: {e}")

    cur.close()
    conn.close()
    print(f"\nFinished! Total {total_uploaded:,} rows successfully uploaded.")


if __name__ == "__main__":
    upload()
