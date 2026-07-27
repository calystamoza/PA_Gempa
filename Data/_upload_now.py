import pandas as pd, requests, os

INPUT_FILE  = "add_2025-2026.csv"
OUTPUT_FILE = "add_2025-2026_transformed.csv"
API_BASE    = "http://localhost:8000"

PROVINCE_MAPPING = [
    (["Abepura","Jayapura","Sarmi","Agats","Asmat","Wamena","Merauke","Mimika","Timika","Sentani","Paniai","Biak","Insrom","Maba"], "Papua"),
    (["Manokwari","Sorong","Fef","Bintuni","Waisai","Kaimana","Fakfak","Fak-Fak","Ransiki"], "Papua Barat"),
    (["Nabire","Enarotali"], "Papua Tengah"),
    (["Teminabuan","Ayamaru"], "Papua Barat Daya"),
    (["Ternate","Tobelo","Sofifi","Labuha","Morotai","Halmahera","Tidore","Sanana","Modisi"], "Maluku Utara"),
    (["Ambon","Masohi","Namlea","Tual","Amahai","Katobu","Saumlaki","Dobo","Kepulauan Babar","Pulau Pulau Tanimbar","Waisarisa","Bula","Kairatu"], "Maluku"),
    (["Manado","Bitung","Tomohon","Tondano","Amurang","Kotamobagu","Lolak","Noongan","Laikit"], "Sulawesi Utara"),
    (["Gorontalo","Limboto","Tilamuta","Molibagu"], "Gorontalo"),
    (["Palu","Luwuk","Poso","Buol","Tolitoli","Ampana","Parigi","Donggala","Banggai"], "Sulawesi Tengah"),
    (["Kendari","Bau-Bau","Baubau","Kolaka","Raha","Unaaha","Lasolo","Pomalaa"], "Sulawesi Tenggara"),
    (["Makassar","Palopo","Parepare","Pare-Pare","Bulukumba","Watampone","Bone","Masamba","Malili","Sinjai","Enrekang","Sengkang"], "Sulawesi Selatan"),
    (["Mamuju","Mamasa","Pasangkayu","Polewali","Majene"], "Sulawesi Barat"),
    (["Kupang","Ende","Maumere","Labuan Bajo","Ruteng","Bajawa","Waingapu","Atambua","Soe","Tambolaka","Naisano Dua","Komodo","Kalabahi","Mbay","Larantuka","Lewoleba","Mount Lewotobi","Flores Sea","Adonara","Lembata","Kefamenanu"], "Nusa Tenggara Timur"),
    (["Mataram","Bima","Dompu","Sumbawa Besar","Sumbawa","Praya","Pototano","Taliwang","Baa","Raba","south of Sumbawa","South of Lombok","Lombok","Naisano","Sape","Gili Trawangan","Gili Air","Lembar","Kalianget"], "Nusa Tenggara Barat"),
    (["Denpasar","Singaraja","Tabanan","Gianyar","Klungkung","south of Bali","Karangasem","Negara","Buleleng","Jembrana","Bangli","Pundong","Jimbaran","Nusa Dua","Kuta","Seminyak","Amlapura","Munduk","Seririt","Lovina","Kerobokan"], "Bali"),
    (["Surabaya","Malang","Jember","Banyuwangi","Kediri","Blitar","Madiun","Mojokerto","Pasuruan","Probolinggo","Trenggalek","Tulungagung","Lumajang","Situbondo","Bondowoso","Jatiroto","Boyolangu","Dampit","Gambiran Satu","Bojonegoro","Tuban","Paciran","Wongsorejo","Ponorogo","Ngunut","Kencong","Muncar","Panji"], "Jawa Timur"),
    (["Semarang","Surakarta","Purwokerto","Cilacap","Kebumen","Purworejo","Wonosobo","Magelang","Klaten","Wonogiri","Blora","Cepu","Batang","Pekalongan","Tegal","Brebes","Tayu","Rembang","Demak","Purwodadi"], "Jawa Tengah"),
    (["Yogyakarta","Sleman","Bantul","Gunungkidul","Gunung Kidul","Kulon Progo","Sewon","Wonosari"], "DI Yogyakarta"),
    (["Bandung","Bekasi","Bogor","Sukabumi","Cirebon","Tasikmalaya","Garut","Cianjur","Ciamis","Pangandaran","Kawalu","Singaparna","Pelabuhanratu","Labuan","Sumedang Utara","Ciampea","Banjar","Cicurug","Cileungsir","Caringin","Cikarang","Ciranjang-hilir","Ciranjang"], "Jawa Barat"),
    (["Jakarta"], "DKI Jakarta"),
    (["Serang","Tangerang","Lebak","Pandeglang","Rangkasbitung","Teluknaga","Kresek"], "Banten"),
    (["Bandar Lampung","Metro","Kotabumi","Liwa","Pagar Alam","Kalianda"], "Lampung"),
    (["Palembang","Lubuklinggau","Muara Enim","Lahat","Prabumulih","Baturaja"], "Sumatera Selatan"),
    (["Bengkulu","Manna","Curup","Mukomuko","Kaur","Argamakmur"], "Bengkulu"),
    (["Jambi","Sungai Penuh","Muara Bungo","Kuala Tungkal","Sarolangun"], "Jambi"),
    (["Padang","Bukittinggi","Solok","Payakumbuh","Pariaman","Painan","Tuapejat","Lubuk Basung","Pasaman","Padang Panjang","Sijunjung"], "Sumatera Barat"),
    (["Pekanbaru","Dumai","Rengat","Bangkinang","Selat Panjang"], "Riau"),
    (["Batam","Tanjungpinang","Ranai","Natuna"], "Kepulauan Riau"),
    (["Medan","Pematangsiantar","Sibolga","Rantau Prapat","Padang Sidempuan","Gunungsitoli","Nias","Teluk Dalam","Singkil","Blangpidie","Sinabang","Tarutung","Parapat","Ambarita","Tomok Bolon","Pangkalan Brandan"], "Sumatera Utara"),
    (["Banda Aceh","Lhokseumawe","Langsa","Meulaboh","Sabang","Calang","Tapaktuan","Reuleuet","Bireun"], "Aceh"),
    (["Samarinda","Balikpapan","Bontang","Berau","Tarakan","Sangatta"], "Kalimantan Timur"),
    (["Banjarmasin","Banjarbaru","Martapura","Kandangan","Kotabaru"], "Kalimantan Selatan"),
    (["Palangka Raya","Sampit","Pangkalan Bun","Muara Teweh","Kuala Kapuas"], "Kalimantan Tengah"),
    (["Pontianak","Singkawang","Ketapang","Putussibau","Mempawah"], "Kalimantan Barat"),
    (["Tanjung Selor","Nunukan","Malinau"], "Kalimantan Utara"),
    (["southwest of Sumatra","Sumatra"], "Sumatera Utara"),
    (["south of Java","Java"], "Jawa Tengah"),
    (["Banda Sea"], "Maluku"),
    (["Flores"], "Nusa Tenggara Timur"),
    (["Celebes Sea","Sulawesi Sea"], "Sulawesi Utara"),
]

def map_province(place):
    if not isinstance(place, str): return "Unknown"
    for keywords, province in PROVINCE_MAPPING:
        for kw in keywords:
            if kw.lower() in place.lower(): return province
    return "Unknown"

def depth_cat(d):
    if d <= 60: return "dangkal"
    elif d <= 300: return "menengah"
    else: return "dalam"

# Get last_id from Supabase
resp = requests.get(f"{API_BASE}/admin/earthquakes/next-id", headers={"x-user-role": "admin"}, timeout=10)
resp.raise_for_status()
last_id = int(resp.json()["next_id"]) - 1
print(f"[INFO] last_id dari Supabase: {last_id}, ID baru mulai dari: {last_id+1}")

# Transform
df = pd.read_csv(INPUT_FILE)
df = df[df["place"].str.contains("Indonesia", na=False)].copy()
df = df.dropna(subset=["latitude","longitude","mag"])
df["latitude"] = df["latitude"].astype(float)
df["longitude"] = df["longitude"].astype(float)
df["mag"] = df["mag"].astype(float)
df["depth"] = pd.to_numeric(df["depth"], errors="coerce").fillna(0.0)
df["_dt"] = pd.to_datetime(df["time"], utc=True)
df["date"] = df["_dt"].apply(lambda x: f"{x.day}/{x.month}/{x.year}")
df["month"] = df["_dt"].dt.month
df["month_name"] = df["_dt"].dt.strftime("%B")
df["year"] = df["_dt"].dt.year
df["time_only"] = df["_dt"].dt.strftime("%H:%M:%S")
df["province"] = df["place"].apply(map_province)
df["depth_category"] = df["depth"].apply(depth_cat)
df = df.reset_index(drop=True)
df["new_id"] = range(last_id + 1, last_id + 1 + len(df))

output = pd.DataFrame({
    "id": df["new_id"].astype(str),
    "province": df["province"],
    "date": df["date"],
    "month": df["month"],
    "month_name": df["month_name"],
    "year": df["year"],
    "latitude": df["latitude"],
    "longitude": df["longitude"],
    "magnitude": df["mag"],
    "depth": df["depth"],
    "depth_category": df["depth_category"],
    "time": df["time_only"],
})

output.to_csv(OUTPUT_FILE, index=False)
print(f"[OK] CSV regenerated: {len(output)} baris")
print(f"     Kolom: {list(output.columns)}")
print(f"     ID range: {output.id.iloc[0]} - {output.id.iloc[-1]}")

# Upload
print(f"[INFO] Upload ke {API_BASE}/admin/earthquakes/upload ...")
with open(OUTPUT_FILE, "rb") as f:
    r = requests.post(
        f"{API_BASE}/admin/earthquakes/upload",
        headers={"x-user-role": "admin"},
        files={"file": (OUTPUT_FILE, f, "text/csv")},
        timeout=300,
    )
r.raise_for_status()
result = r.json()
print(f"[RESULT] {result['message']}")
print(f"  success : {result.get('success', 0)}")
print(f"  skipped : {result.get('skipped', 0)}")
print(f"  failed  : {result.get('failed', 0)}")
if result.get("errors"):
    for e in result["errors"][:5]:
        print(f"  ERR row {e['row']}: {e['error']}")
