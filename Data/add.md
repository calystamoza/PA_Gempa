# Technical Requirements: Transformasi Data Gempa (USGS → Dataset Internal)

## 🎯 Objective

Mengubah dataset gempa (format USGS) menjadi format dataset internal serta **memfilter hanya data gempa di Indonesia**, dengan ID yang melanjutkan dari data terakhir yang sudah ada.

---

## 📥 Input Data

Format CSV dengan kolom:

```
time, latitude, longitude, depth, mag, magType, nst, gap, dmin, rms, net, id, updated, place, type, horizontalError, depthError, magError, magNst, status, locationSource, magSource
```

---

## 📤 Output Data

Format CSV dengan struktur:

```
id, province, date, month, month_name, year, latitude, longitude, magnitude, depth, depth_category, fault_megathrust_id, time
```

---

## ⚙️ Data Processing Rules

### 1. 🔍 Filter Data Indonesia

#### Primary Rule (WAJIB)

* Ambil hanya data dengan:

```
place CONTAINS "Indonesia"
```

#### Optional Improvement (lebih akurat)

* Gunakan bounding box:

```
latitude BETWEEN -11 AND 6
longitude BETWEEN 95 AND 141
```

---

### 2. 🗓️ Transformasi Waktu

Dari:

```
time (ISO 8601, UTC)
```

Ekstrak menjadi:

| Kolom      | Format             |
| ---------- | ------------------ |
| date       | dd/mm/yyyy         |
| month      | integer (1–12)     |
| month_name | English month name |
| year       | yyyy               |
| time       | HH:mm:ss           |

Contoh:

```
2026-07-22T14:50:42.472Z →
date: 22/7/2026
month: 7
month_name: July
year: 2026
time: 14:50:42
```

---

### 3. 📍 Mapping Lokasi ke Province

Dari:

```
place (string)
```

Ke:

```
province
```

#### Aturan:

* Gunakan keyword matching:

  * "Abepura", "Papua" → Papua
  * "Bandung" → Jawa Barat
* Jika tidak ditemukan:

  * isi: `"Unknown"`

---

### 4. 🌊 Kategori Kedalaman

Buat kolom:

```
depth_category
```

Aturan:

```
depth ≤ 70 → dangkal
70 < depth ≤ 300 → menengah
depth > 300 → dalam
```

---

### 5. 📊 Mapping Kolom

| Output              | Source                    |
| ------------------- | ------------------------- |
| id                  | generated (lihat rule ID) |
| province            | hasil mapping             |
| date                | dari time                 |
| month               | dari time                 |
| month_name          | dari time                 |
| year                | dari time                 |
| latitude            | latitude                  |
| longitude           | longitude                 |
| magnitude           | mag                       |
| depth               | depth                     |
| depth_category      | hasil rule                |
| fault_megathrust_id | null / kosong             |
| time                | dari time                 |

---

### 6. 🧹 Data Cleaning

Hapus baris jika:

* latitude null
* longitude null
* mag null

Pastikan tipe data:

* latitude, longitude → float
* magnitude → float
* depth → float

---

### 7. 🆔 ID Generation (UPDATED REQUIREMENT)

ID **tidak dimulai dari 1**, tetapi:

#### Aturan:

* Ambil nilai **ID terakhir dari dataset existing**
* Misal:

```
last_id = 1500
```

* Maka data baru:

```
id pertama = last_id + 1 = 1501
```

* Increment per baris:

```
1501, 1502, 1503, ...
```

#### Catatan Implementasi:

* Jika dataset existing kosong → mulai dari 1
* ID harus unik (no duplicate)

---

## 📌 Contoh Output

```
id: 1501
province: Papua
date: 22/7/2026
month: 7
month_name: July
year: 2026
latitude: -2.5597
longitude: 138.8297
magnitude: 4.9
depth: 10
depth_category: dangkal
fault_megathrust_id: 
time: 14:50:42
```

---

## 🚀 Expected Deliverables

* Script transformasi (Python / SQL / Pandas)
* Output CSV sesuai schema
* Logging:

  * total data awal
  * data setelah filter Indonesia
  * data final
  * last_id yang digunakan

---

## 💡 Optional Enhancement

* Tambahkan kolom:

```
is_indonesia (boolean)
```

* Gunakan:

  * reverse geocoding API
  * shapefile Indonesia

---
