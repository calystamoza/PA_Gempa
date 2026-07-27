# Laporan Analisis Kompleksitas Eksekusi GempaBot

**Tanggal:** 24 July 2026 16:54
**Sumber data:** `_archive/evaluation/evaluation_results_v3.csv`
**Total sampel:** 40 pertanyaan (5 per intent × 7 intent)

> **Metodologi:** Analisis dilakukan dari data evaluasi yang sudah ada. Karena data waktu eksekusi aktual tidak tersimpan di file evaluasi, analisis menggunakan **proxy metrics** yang berkorelasi dengan beban komputasi:
> - **Panjang Konteks (ctx_len):** panjang string data yang dikembalikan DB → proxy beban SQL
> - **Panjang Jawaban (ans_len):** panjang teks respons LLM → proxy beban generation
> - **Skor Faithfulness & Answer Relevancy:** kualitas output dari RAGAS evaluation

## 1. Pertanyaan Representatif per Intent

| Intent | Pertanyaan | Faithfulness | Answer Relevancy |
|--------|------------|:------------:|:----------------:|
| `count` | Berapa total gempa yang terjadi di Indonesia sepanjang tahun… | 0.333 | 0.914 |
| `average` | Berapa rata-rata kekuatan gempa di Jawa Barat? | 0.333 | 0.687 |
| `max` | Kekuatan gempa maksimal di Indonesia berapa? | 0.333 | 0.869 |
| `min` | Di mana lokasi gempa bumi paling dangkal yang tercatat? | 1.000 | 0.906 |
| `list` | Sebutkan 3 gempa terbesar di Papua | 0.375 | 0.810 |
| `trend` | Bagaimana tren jumlah gempa per tahun di Indonesia? | 1.000 | 0.757 |
| `knowledge` | Apa itu magnitudo momen? | 0.000 | 0.429 |

## 2. Rata-rata Proxy Metrics per Intent

*(Ukuran konteks dan jawaban sebagai indikator beban komputasi)*

| Intent | Avg Ctx Len (char) | Avg Ans Len (char) | Avg Faithfulness | Avg Relevancy | Keterangan SQL |
|--------|:-----------------:|:-----------------:|:----------------:|:-------------:|----------------|
| `count` | 🟢 **73** | 🟢 **287** | 0.267 | 0.791 | SELECT COUNT(*) — agregasi tunggal |
| `average` | 🟢 **109** | 🟢 **271** | 0.367 | 0.774 | SELECT AVG() — satu pass scan kolom numerik |
| `max` | 🟡 **207** | 🟡 **440** | 0.549 | 0.841 | ORDER BY DESC LIMIT — scan minimal |
| `min` | 🟡 **383** | 🟢 **289** | 0.693 | 0.886 | ORDER BY ASC LIMIT — scan minimal |
| `list` | 🟡 **400** | 🔴 **841** | 0.770 | 0.754 | SELECT * ORDER BY LIMIT N — transfer data lebih besar |
| `trend` | 🔴 **2994** | 🔴 **1139** | 0.926 | 0.711 | GROUP BY year/month — full scan + agregasi per grup |
| `knowledge` | 🟢 **74** | 🔴 **807** | 0.093 | 0.505 | Bypass DB — hanya LLM inference (2 Groq API call) |

> 🟢 Ringan &nbsp; 🟡 Sedang &nbsp; 🔴 Berat (estimasi beban)

## 3. Proxy Metrics per Tingkat Kompleksitas

*(Apakah pertanyaan yang lebih kompleks menghasilkan konteks dan jawaban yang lebih panjang?)*

| Kompleksitas | Definisi | Avg Ctx Len | Avg Ans Len | Avg Faithfulness | Avg Relevancy | Δ Ctx vs Simple |
|-------------|----------|:-----------:|:-----------:|:----------------:|:-------------:|:---------------:|
| **simple** | ≤1 filter, pertanyaan langsung | 114 | 396 | 0.412 | 0.674 | — |
| **medium** | 2 filter atau aggregasi + filter lokasi | 575 | 473 | 0.561 | 0.828 | +461 char |
| **complex** | Rentang waktu, GROUP BY, atau multi-konsep | 989 | 736 | 0.530 | 0.651 | +874 char |

## 4. Detail Semua Pertanyaan (per Intent, 5 Sampel)

| Intent | Kompleksitas | Pertanyaan | Ctx Len | Ans Len | Faith. | Relev. |
|--------|-------------|------------|:-------:|:-------:|:------:|:------:|
| `count` | medium | Berapa total gempa yang terjadi di Indonesia sepanjang … | 89 | 244 | 0.333 | 0.914 |
| `count` | medium | Berapa jumlah gempa yang terjadi di Aceh pada tahun 202… | 102 | 331 | 0.333 | 0.848 |
| `count` | medium | Berapa jumlah gempa dangkal yang pernah terjadi di Malu… | 114 | 358 | 0.333 | 0.673 |
| `count` | complex | Berapa banyak gempa yang terjadi dalam 10 tahun terakhi… | 31 | 229 | 0.000 | 0.826 |
| `count` | complex | Berapa total gempa yang tercatat selama dekade 2010-an? | 31 | 273 | 0.333 | 0.696 |
| `average` | medium | Berapa rata-rata kekuatan gempa di Jawa Barat? | 120 | 298 | 0.333 | 0.687 |
| `average` | medium | Berapa rata-rata kedalaman gempa di Maluku Utara? | 120 | 249 | 0.333 | 0.620 |
| `average` | medium | Berapa rata-rata magnitudo gempa di Sulawesi Tengah tah… | 136 | 288 | 0.667 | 0.928 |
| `average` | complex | Berapa rata-rata kedalaman gempa dalam 5 tahun terakhir… | 50 | 244 | 0.000 | 0.870 |
| `average` | complex | Berapa rata-rata magnitudo gempa selama dekade terakhir… | 118 | 276 | 0.500 | 0.765 |
| `max` | medium | Kekuatan gempa maksimal di Indonesia berapa? | 128 | 302 | 0.333 | 0.869 |
| `max` | medium | Berapa kekuatan gempa terbesar yang pernah terjadi di S… | 141 | 692 | 0.143 | 0.942 |
| `max` | medium | Gempa terbesar apa yang pernah tercatat dalam data terb… | 132 | 452 | 0.800 | 0.725 |
| `max` | medium | Gempa terdalam apa yang pernah terjadi di Indonesia? | 559 | 356 | 0.667 | 0.924 |
| `max` | simple | Gempa terakhir apa yang tercatat dalam data kita? | 75 | 397 | 0.800 | 0.743 |
| `min` | medium | Di mana lokasi gempa bumi paling dangkal yang tercatat? | 130 | 148 | 1.000 | 0.906 |
| `min` | simple | Gempa bumi pertama apa yang tercatat dalam data kita? | 494 | 373 | 0.800 | 0.815 |
| `min` | medium | Berapa magnitudo terkecil gempa yang pernah tercatat di… | 135 | 201 | 0.000 | 0.945 |
| `min` | medium | Apa gempa dengan kekuatan paling kecil yang terjadi di … | 554 | 404 | 1.000 | 0.990 |
| `min` | medium | Gempa dengan kedalaman paling kecil yang tercatat di Su… | 601 | 320 | 0.667 | 0.772 |
| `list` | medium | Sebutkan 3 gempa terbesar di Papua | 218 | 598 | 0.375 | 0.810 |
| `list` | medium | Tampilkan daftar 5 gempa terkuat di Nusa Tenggara Timur | 377 | 1040 | 0.800 | 0.799 |
| `list` | medium | Berikan daftar gempa yang terjadi di Jawa Barat pada ta… | 532 | 1201 | 1.000 | 0.823 |
| `list` | simple | Tampilkan 10 gempa terbaru yang tercatat dalam data kit… | 507 | 787 | 0.818 | 0.654 |
| `list` | medium | Sebutkan 5 gempa paling dangkal yang pernah terjadi di … | 368 | 578 | 0.857 | 0.684 |
| `trend` | complex | Bagaimana tren jumlah gempa per tahun di Indonesia? | 6439 | 1088 | 1.000 | 0.757 |
| `trend` | medium | Apakah jumlah gempa di Indonesia cenderung meningkat at… | 6373 | 934 | 0.692 | 0.867 |
| `trend` | complex | Bagaimana perkembangan frekuensi gempa per bulan di Ind… | 928 | 1386 | 1.000 | 0.734 |
| `trend` | complex | Bagaimana tren jumlah gempa selama 10 tahun terakhir di… | 616 | 1190 | 1.000 | 0.592 |
| `trend` | complex | Apakah gempa makin sering terjadi di Jawa selama dekade… | 612 | 1096 | 0.938 | 0.605 |
| `knowledge` | simple | Apa itu magnitudo momen? | 74 | 454 | 0.000 | 0.429 |
| `knowledge` | simple | Mengapa Indonesia sering mengalami gempa bumi? | 74 | 663 | 0.000 | 1.000 |
| `knowledge` | complex | Apa perbedaan antara gempa dangkal, menengah, dan dalam… | 74 | 843 | 0.000 | 0.015 |
| `knowledge` | simple | Apa yang harus dilakukan untuk menyelamatkan diri saat … | 74 | 1115 | 0.214 | 0.864 |
| `knowledge` | simple | Bagaimana cara kerja seismograf? | 74 | 962 | 0.250 | 0.216 |

## 5. Analisis & Kesimpulan

### 5.1 Intent dengan Beban Data Terbesar & Terkecil

- **Beban konteks terbesar:** `trend` — rata-rata **2994 char** konteks
- **Beban konteks terkecil:** `count` — rata-rata **73 char** konteks
- **Rasio:** `trend` menghasilkan ~40.8× lebih banyak data dari `count`

### 5.2 Apakah Kompleksitas Mempengaruhi Beban Eksekusi?

**Ya, berpengaruh.** Pertanyaan complex menghasilkan konteks 765% lebih panjang dari simple.

| Metrik | Simple | Complex | Selisih |
|--------|:------:|:-------:|:-------:|
| Avg Ctx Len | 114 | 989 | +874 char |
| Avg Ans Len | 396 | 736 | +340 char |

### 5.3 Estimasi Komponen Waktu Eksekusi per Intent

Berdasarkan arsitektur sistem (2–4 Groq API call + 1 DB query):

| Intent | Groq Intent Parse | DB Query | Groq Answer Gen | Groq Correction | Estimasi Total |
|--------|:-----------------:|:--------:|:---------------:|:---------------:|:--------------:|
| `count` | ~400 ms | ~100 ms | ~500 ms | kadang | **~1.0–2.0 detik** |
| `average` | ~400 ms | ~100 ms | ~500 ms | kadang | **~1.0–2.0 detik** |
| `max` | ~400 ms | ~100 ms | ~600 ms | kadang | **~1.1–2.1 detik** |
| `min` | ~400 ms | ~100 ms | ~500 ms | kadang | **~1.0–2.0 detik** |
| `list` | ~400 ms | ~200 ms | ~800 ms | kadang | **~1.4–2.5 detik** |
| `trend` | ~400 ms | ~500 ms | ~1200 ms | kadang | **~2.1–3.5 detik** |
| `knowledge` | ~400 ms | — (skip) | ~700 ms | tidak | **~1.1–1.5 detik** |

> **Catatan:** Groq API (llama-3.1-8b-instant) adalah **bottleneck utama** — setiap request memanggil Groq 2–4× (intent parse + answer gen + opsional correction). Beban DB relatif kecil kecuali untuk `trend` yang melakukan GROUP BY pada jutaan baris.