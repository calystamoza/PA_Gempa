"""
transform_usgs_to_internal.py
================================
Transformasi data gempa USGS → format internal database.

Spec: Data/add.md
Input : Data/add_2025-2026.csv
Output: Data/add_2025-2026_transformed.csv
Upload: POST /admin/earthquakes/upload (sebagai admin)

Koreksi depth_category (sesuai spec):
  D <= 60      -> dangkal
  60 < D <= 300 -> menengah
  D > 300     -> dalam
"""

import pandas as pd
import requests
import sys
import os

# ─── CONFIG ──────────────────────────────────────────────────────────────────
INPUT_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "add_2025-2026.csv")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "add_2025-2026_transformed.csv")

API_BASE_URL    = "http://localhost:8000"   # Ganti jika backend di deploy URL lain
ADMIN_USERNAME  = "admin"                   # Ganti sesuai credentials admin
ADMIN_PASSWORD  = "admin123"                # Ganti sesuai credentials admin

# ─── PROVINCE MAPPING ────────────────────────────────────────────────────────
# Format: ([keyword, ...], "Nama Provinsi")
# Diurutkan dari yang lebih spesifik ke general

PROVINCE_MAPPING = [
    # Papua
    (["Abepura", "Jayapura", "Sarmi", "Agats", "Asmat",
      "Wamena", "Merauke", "Mimika", "Timika", "Sentani", "Paniai",
      "Biak", "Insrom", "Maba"], "Papua"),

    # Papua Barat
    (["Manokwari", "Sorong", "Fef", "Bintuni", "Waisai",
      "Kaimana", "Fakfak", "Fak-Fak", "Ransiki"], "Papua Barat"),

    # Papua Tengah
    (["Nabire", "Enarotali"], "Papua Tengah"),

    # Papua Barat Daya
    (["Teminabuan", "Ayamaru"], "Papua Barat Daya"),

    # Maluku Utara
    (["Ternate", "Tobelo", "Sofifi", "Labuha", "Morotai",
      "Halmahera", "Tidore", "Sanana", "Modisi"], "Maluku Utara"),

    # Maluku
    (["Ambon", "Masohi", "Namlea", "Tual", "Amahai", "Katobu",
      "Saumlaki", "Dobo", "Kepulauan Babar", "Pulau Pulau Tanimbar",
      "Waisarisa", "Bula", "Kairatu"], "Maluku"),

    # Sulawesi Utara
    (["Manado", "Bitung", "Tomohon", "Tondano", "Amurang",
      "Kotamobagu", "Lolak", "Noongan",
      "Laikit"], "Sulawesi Utara"),

    # Gorontalo
    (["Gorontalo", "Limboto", "Tilamuta", "Molibagu"], "Gorontalo"),

    # Sulawesi Tengah
    (["Palu", "Luwuk", "Poso", "Buol", "Tolitoli", "Ampana",
      "Parigi", "Donggala", "Banggai"], "Sulawesi Tengah"),

    # Sulawesi Tenggara
    (["Kendari", "Bau-Bau", "Baubau", "Kolaka", "Raha",
      "Unaaha", "Lasolo", "Pomalaa"], "Sulawesi Tenggara"),

    # Sulawesi Selatan
    (["Makassar", "Palopo", "Parepare", "Pare-Pare", "Bulukumba",
      "Watampone", "Bone", "Masamba", "Malili",
      "Sinjai", "Enrekang", "Sengkang"], "Sulawesi Selatan"),

    # Sulawesi Barat
    (["Mamuju", "Mamasa", "Pasangkayu", "Polewali", "Majene"], "Sulawesi Barat"),

    # Nusa Tenggara Timur
    (["Kupang", "Ende", "Maumere", "Labuan Bajo", "Ruteng",
      "Bajawa", "Waingapu", "Atambua", "Soe", "Tambolaka",
      "Naisano Dua", "Komodo", "Kalabahi", "Mbay", "Larantuka",
      "Lewoleba", "Mount Lewotobi", "Flores Sea", "Adonara", "Lembata",
      "Kefamenanu"], "Nusa Tenggara Timur"),

    # Nusa Tenggara Barat
    (["Mataram", "Bima", "Dompu", "Sumbawa Besar", "Sumbawa",
      "Praya", "Pototano", "Taliwang", "Baa", "Raba",
      "south of Sumbawa", "South of Lombok", "Lombok", "Naisano",
      "Sape", "Gili Trawangan", "Gili Air", "Lembar", "Kalianget"], "Nusa Tenggara Barat"),

    # Bali
    (["Denpasar", "Singaraja", "Tabanan", "Gianyar", "Klungkung",
      "south of Bali", "Karangasem", "Negara", "Buleleng",
      "Jembrana", "Bangli", "Pundong",
      "Jimbaran", "Nusa Dua", "Kuta", "Seminyak",
      "Amlapura", "Munduk", "Seririt", "Lovina", "Kerobokan"], "Bali"),

    # Jawa Timur
    (["Surabaya", "Malang", "Jember", "Banyuwangi", "Kediri",
      "Blitar", "Madiun", "Mojokerto", "Pasuruan", "Probolinggo",
      "Trenggalek", "Tulungagung", "Lumajang", "Situbondo",
      "Bondowoso", "Jatiroto", "Boyolangu", "Dampit",
      "Gambiran Satu", "Bojonegoro", "Tuban",
      "Paciran", "Wongsorejo", "Ponorogo", "Ngunut",
      "Kencong", "Muncar", "Panji"], "Jawa Timur"),

    # Jawa Tengah
    (["Semarang", "Surakarta", "Purwokerto", "Cilacap",
      "Kebumen", "Purworejo", "Wonosobo", "Magelang",
      "Klaten", "Wonogiri", "Blora", "Cepu", "Batang", "Pekalongan",
      "Tegal", "Brebes", "Tayu", "Rembang", "Demak",
      "Purwodadi"], "Jawa Tengah"),

    # DI Yogyakarta
    (["Yogyakarta", "Sleman", "Bantul", "Gunungkidul",
      "Gunung Kidul", "Kulon Progo",
      "Sewon", "Wonosari"], "DI Yogyakarta"),

    # Jawa Barat
    (["Bandung", "Bekasi", "Bogor", "Sukabumi", "Cirebon",
      "Tasikmalaya", "Garut", "Cianjur", "Ciamis", "Pangandaran",
      "Kawalu", "Singaparna", "Pelabuhanratu", "Labuan",
      "Sumedang Utara", "Ciampea", "Banjar",
      "Cicurug", "Cileungsir", "Caringin", "Cikarang",
      "Ciranjang-hilir", "Ciranjang"], "Jawa Barat"),

    # DKI Jakarta
    (["Jakarta"], "DKI Jakarta"),

    # Banten
    (["Serang", "Tangerang", "Lebak", "Pandeglang",
      "Rangkasbitung", "Teluknaga", "Kresek"], "Banten"),

    # Lampung
    (["Bandar Lampung", "Metro", "Kotabumi", "Liwa",
      "Pagar Alam", "Kalianda"], "Lampung"),

    # Sumatera Selatan
    (["Palembang", "Lubuklinggau", "Muara Enim", "Lahat",
      "Prabumulih", "Baturaja"], "Sumatera Selatan"),

    # Bengkulu
    (["Bengkulu", "Manna", "Curup", "Mukomuko",
      "Kaur", "Argamakmur"], "Bengkulu"),

    # Jambi
    (["Jambi", "Sungai Penuh", "Muara Bungo",
      "Kuala Tungkal", "Sarolangun"], "Jambi"),

    # Sumatera Barat
    (["Padang", "Bukittinggi", "Solok", "Payakumbuh",
      "Pariaman", "Painan", "Tuapejat", "Lubuk Basung",
      "Pasaman", "Padang Panjang",
      "Sijunjung"], "Sumatera Barat"),

    # Riau
    (["Pekanbaru", "Dumai", "Rengat", "Bangkinang",
      "Selat Panjang"], "Riau"),

    # Kepulauan Riau
    (["Batam", "Tanjungpinang", "Ranai", "Natuna"], "Kepulauan Riau"),

    # Sumatera Utara
    (["Medan", "Pematangsiantar", "Sibolga", "Rantau Prapat",
      "Padang Sidempuan", "Gunungsitoli", "Nias", "Teluk Dalam",
      "Singkil", "Blangpidie", "Sinabang", "Tarutung",
      "Parapat", "Ambarita", "Tomok Bolon", "Pangkalan Brandan"], "Sumatera Utara"),

    # Aceh
    (["Banda Aceh", "Lhokseumawe", "Langsa", "Meulaboh",
      "Sabang", "Calang", "Tapaktuan",
      "Reuleuet", "Bireun", "Bireuën"], "Aceh"),

    # Kalimantan Timur
    (["Samarinda", "Balikpapan", "Bontang", "Berau",
      "Tarakan", "Sangatta"], "Kalimantan Timur"),

    # Kalimantan Selatan
    (["Banjarmasin", "Banjarbaru", "Martapura",
      "Kandangan", "Kotabaru"], "Kalimantan Selatan"),

    # Kalimantan Tengah
    (["Palangka Raya", "Sampit", "Pangkalan Bun",
      "Muara Teweh", "Kuala Kapuas"], "Kalimantan Tengah"),

    # Kalimantan Barat
    (["Pontianak", "Singkawang", "Ketapang",
      "Putussibau", "Mempawah"], "Kalimantan Barat"),

    # Kalimantan Utara
    (["Tanjung Selor", "Nunukan", "Malinau"], "Kalimantan Utara"),

    # General region fallback
    (["southwest of Sumatra", "Sumatra"], "Sumatera Utara"),
    (["south of Java", "Java"], "Jawa Tengah"),
    (["Banda Sea"], "Maluku"),
    (["Flores"], "Nusa Tenggara Timur"),
    (["Celebes Sea", "Sulawesi Sea"], "Sulawesi Utara"),
]


def map_province(place: str) -> str:
    if not isinstance(place, str):
        return "Unknown"
    for keywords, province in PROVINCE_MAPPING:
        for kw in keywords:
            if kw.lower() in place.lower():
                return province
    return "Unknown"


def depth_category(depth: float) -> str:
    if depth <= 60:
        return "dangkal"
    elif depth <= 300:
        return "menengah"
    else:
        return "dalam"


def get_last_id_from_supabase(api_base: str) -> int | None:
    try:
        resp = requests.get(
            f"{api_base}/admin/earthquakes/next-id",
            headers={"x-user-role": "admin"},
            timeout=10,
        )
        resp.raise_for_status()
        next_id = int(resp.json()["next_id"])
        last_id = next_id - 1
        print(f"[INFO] next_id dari Supabase: {next_id} (last_id = {last_id})")
        return last_id
    except Exception as e:
        print(f"[ERROR] Gagal ambil next-id dari Supabase: {e}")
        return None


def login_admin(api_base: str, username: str, password: str) -> bool:
    try:
        resp = requests.post(
            f"{api_base}/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        role = data.get("role")
        print(f"[INFO] Login berhasil: {data.get('username')} (role: {role})")
        return role == "admin"
    except Exception as e:
        print(f"[ERROR] Login gagal: {e}")
        return False


def transform(input_file: str, output_file: str, start_id: int) -> pd.DataFrame:
    print(f"\n{'='*60}")
    print(f"[STEP 1] Load: {input_file}")
    df_raw = pd.read_csv(input_file)
    print(f"         Total baris awal        : {len(df_raw):,}")

    print(f"\n[STEP 2] Filter Indonesia")
    df = df_raw[df_raw["place"].str.contains("Indonesia", na=False)].copy()
    print(f"         Setelah filter Indonesia : {len(df):,} baris")

    print(f"\n[STEP 3] Cleaning (drop null lat/lon/mag)")
    before = len(df)
    df = df.dropna(subset=["latitude", "longitude", "mag"])
    print(f"         Baris dihapus  : {before - len(df)}")
    print(f"         Baris valid    : {len(df):,}")

    df["latitude"]  = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)
    df["mag"]       = df["mag"].astype(float)
    df["depth"]     = pd.to_numeric(df["depth"], errors="coerce").fillna(0.0)

    print(f"\n[STEP 4] Parsing waktu")
    df["_dt"] = pd.to_datetime(df["time"], utc=True)
    df["date"]       = df["_dt"].apply(lambda x: f"{x.day}/{x.month}/{x.year}")
    df["month"]      = df["_dt"].dt.month
    df["month_name"] = df["_dt"].dt.strftime("%B")
    df["year"]       = df["_dt"].dt.year
    df["time_only"]  = df["_dt"].dt.strftime("%H:%M:%S")

    print(f"\n[STEP 5] Mapping place -> province")
    df["province"] = df["place"].apply(map_province)
    unknown = (df["province"] == "Unknown").sum()
    print(f"         Unknown province: {unknown} baris")
    if unknown > 0:
        print("         Sample Unknown places:")
        for s in df[df["province"] == "Unknown"]["place"].unique()[:10]:
            print(f"           - {s}")

    print(f"\n[STEP 6] Depth category (<=60 dangkal / 60-300 menengah / >300 dalam)")
    df["depth_category"] = df["depth"].apply(depth_category)
    for cat, cnt in df["depth_category"].value_counts().items():
        print(f"         {cat}: {cnt:,}")

    print(f"\n[STEP 7] ID generation (start: {start_id + 1})")
    df = df.reset_index(drop=True)
    df["new_id"] = range(start_id + 1, start_id + 1 + len(df))
    print(f"         ID range: {df['new_id'].iloc[0]} - {df['new_id'].iloc[-1]}")

    output = pd.DataFrame({
        "id":             df["new_id"].astype(str),
        "province":       df["province"],
        "date":           df["date"],
        "month":          df["month"],
        "month_name":     df["month_name"],
        "year":           df["year"],
        "latitude":       df["latitude"],
        "longitude":      df["longitude"],
        "magnitude":      df["mag"],
        "depth":          df["depth"],
        "depth_category": df["depth_category"],
        "time":           df["time_only"],
    })

    output.to_csv(output_file, index=False)
    print(f"\n[OUTPUT] Tersimpan: {output_file}")
    print(f"         Total baris: {len(output):,}")
    return output


def upload_csv(api_base: str, csv_file: str) -> bool:
    print(f"\n[STEP 8] Upload ke {api_base}/admin/earthquakes/upload")
    try:
        with open(csv_file, "rb") as f:
            resp = requests.post(
                f"{api_base}/admin/earthquakes/upload",
                headers={"x-user-role": "admin"},
                files={"file": (os.path.basename(csv_file), f, "text/csv")},
                timeout=180,
            )
        resp.raise_for_status()
        result = resp.json()
        print(f"[SUCCESS] {result.get('message', 'Upload selesai')}")
        print(f"          success : {result.get('success', 0)}")
        print(f"          skipped : {result.get('skipped', 0)}")
        print(f"          failed  : {result.get('failed', 0)}")
        if result.get("errors"):
            print("[ERRORS]")
            for err in result["errors"][:5]:
                print(f"  Row {err['row']}: {err['error']}")
        return True
    except requests.HTTPError as e:
        print(f"[HTTP ERROR] {e.response.status_code}: {e.response.text[:300]}")
        return False
    except Exception as e:
        print(f"[ERROR] Upload gagal: {e}")
        return False


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  USGS -> Internal Transform & Upload")
    print("=" * 60)

    # ── STEP 1-2: Coba ambil last_id dari Supabase (opsional) ────────────────
    backend_available = False
    last_id = None

    print("\n[INFO] Mencoba koneksi ke backend ...")
    try:
        is_admin = login_admin(API_BASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
        if is_admin:
            backend_available = True
            last_id = get_last_id_from_supabase(API_BASE_URL)
        else:
            print("[WARN] Login gagal, mode transform-only (tanpa upload otomatis).")
    except Exception:
        print("[WARN] Backend tidak tersedia, mode transform-only.")

    # ── Fallback last_id dari file lokal ─────────────────────────────────────
    if last_id is None:
        print("[FALLBACK] Menghitung last_id dari data_gempa_processed.csv ...")
        fallback_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_gempa_processed.csv")
        try:
            df_existing = pd.read_csv(fallback_file, usecols=["id"])
            last_id = int(df_existing["id"].astype(int).max())
            print(f"[FALLBACK] last_id dari file lokal: {last_id}")
        except Exception as e:
            print(f"[ERROR] Tidak bisa baca fallback file: {e}")
            print("[DEFAULT] Gunakan last_id = 157332 (sesuai snapshot terakhir)")
            last_id = 157332

    # ── STEP 3: Transformasi (selalu jalan) ───────────────────────────────────
    transform(INPUT_FILE, OUTPUT_FILE, last_id)

    # ── STEP 4: Upload (opsional, hanya jika backend tersedia) ────────────────
    print()
    if backend_available:
        answer = input("Upload sekarang ke database? (y/n): ").strip().lower()
        if answer == "y":
            success = upload_csv(API_BASE_URL, OUTPUT_FILE)
            if success:
                print("\n[DONE] Proses selesai!")
            else:
                print("\n[FAILED] Upload gagal. Periksa error di atas.")
        else:
            print(f"\n[SKIP] Upload dilewati.")
            print(f"       File siap di: {OUTPUT_FILE}")
            print("       Upload manual via Admin UI dengan file tersebut.")
    else:
        print("[INFO] Backend tidak tersedia — transformasi selesai.")
        print(f"       File output: {OUTPUT_FILE}")
        print()
        print("  Langkah selanjutnya:")
        print("  1. Jalankan backend: uvicorn main:app --reload")
        print("  2. Upload via Admin UI, atau jalankan ulang script ini.")
        print("     (last_id akan otomatis diambil dari Supabase saat itu)")

    print("=" * 60)
