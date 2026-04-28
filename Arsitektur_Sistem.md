# 🏗️ Arsitektur Lengkap & Alur Kerja GempaBot

Dokumen ini menjelaskan peta jalan sistem GempaBot, mulai dari teknologi yang digunakan, alur data, hingga navigasi file di dalam kode program. Gunakan dokumen ini sebagai referensi utama untuk memahami cara kerja sistem.

---

## 🛠️ 1. Teknologi Utama (Tech Stack)
- **Frontend**: Next.js (TypeScript) & Tailwind CSS.
- **Backend**: FastAPI (Python 3.12).
- **Database**: Supabase (PostgreSQL) - menyimpan data gempa & riwayat chat.
- **Brain (LLM)**: Groq API (`llama-3.1-8b-instant`) - untuk inferensi cepat dan akurat.
- **Validation**: Custom Data-Driven Validation Layer (Mencegah Halusinasi).

---

## 📂 2. Navigasi Kode & Fungsi File

### 📁 Folder `backend/` (Pusat Kendali)
Tempat semua logika kecerdasan buatan dan pemrosesan data terjadi.

- **📄 `main.py`**
  - **Kegunaan**: Entry point API. Menghubungkan Frontend ke logic Backend.
  - **Baris 30 (`@app.post("/chat")`)**: Endpoint utama yang menerima pertanyaan user.
  - **Baris 46-52**: Logika menyimpan riwayat percakapan agar asisten memiliki memori.
  - **Baris 49**: Memanggil fungsi `process_query()` untuk memulai pipeline RAG.

- **📄 `rag_engine.py`**
  - **Kegunaan**: "Otak" utama sistem yang mengelola alur RAG (Retrieval-Augmented Generation).
  - **Baris 43 (`INTENT_SYSTEM`)**: Instruksi agar AI memahami maksud user (misal: "Jatim" dipetakan ke "Jawa Timur").
  - **Baris 100 (`def build_sql`)**: Mengubah hasil pemikiran AI menjadi query SQL yang aman.
  - **Baris 215 (`ANSWER_SYSTEM`)**: Panduan gaya bicara asisten (ramah, berbasis data, jujur).
  - **Baris 224 (`CORRECTION_SYSTEM`)**: **(Fitur Unggulan)** Prompt khusus untuk memperbaiki jawaban jika angka yang disebutkan AI tidak sesuai dengan Database.
  - **Baris 322 (`def validate_response`)**: **(Fitur Unggulan)** "Wasit" sistem yang membandingkan jawaban AI dengan data asli (Ground Truth) dari database.

- **📄 `database.py`**
  - **Kegunaan**: Pengelola koneksi dan query ke Supabase.
  - **Baris 15-41**: Fungsi `execute_query` untuk mengambil data gempa secara real-time.

### 📁 Folder `frontend/` (Tampilan Visual)
- **📄 `app/page.tsx`**: Halaman utama chat. Mengatur state pesan dan menampilkan badge validasi.
- **📄 `components/MessageBubble.tsx`**: Komponen yang merender balon chat, termasuk logo "Validated" jika data akurat.
- **📄 `lib/api.ts`**: API Client yang mengirim data ke backend port 8000.

---

## 🔄 3. Alur Kerja Sistem (System Workflow)

Alur perjalanan sebuah pesan dari user hingga mendapatkan jawaban akurat:

1.  **Input User**: User mengetik pertanyaan di browser (misal: *"Gempa terbesar di Aceh tahun 2004?"*).
2.  **Intent Parsing (`rag_engine.py`)**: AI membaca pertanyaan dan memutuskan: *"User ingin melihat data MAX Magnitude dengan filter Place=Aceh dan Year=2004"*.
3.  **SQL Execution (`database.py`)**: Sistem menjalankan query ke Supabase. Database memberikan data asli: `Tanggal 26 Des, Magnitude 9.0`.
4.  **Drafting Answer (`rag_engine.py`)**: AI menyusun kalimat jawaban berdasarkan data tersebut.
5.  **Validation Layer (`validate_response`)**:
    - Sistem mengecek: *"Apakah angka 9.0 ada di dalam kalimat jawaban AI?"*
    - **Jika ADA**: Jawaban langsung dikirim ke user (Status: ✅ *Validated*).
    - **Jika TIDAK ADA / SALAH**: Sistem masuk ke tahap **Conversational Correction**.
6.  **Conversational Correction**: AI diminta menulis ulang jawabannya menggunakan data yang benar secara naratif (Status: ⚠️ *Dikoreksi dari DB*).
7.  **Response**: User menerima jawaban di layar lengkap dengan sumber data dan transparansi query SQL.

---

## 💡 Navigasi Cepat Lingkungan (Root)
- **📄 `.env`**: Berisi `GROQ_API_KEY` dan `DATABASE_URL`.
- **📄 `requirements.txt`**: Daftar library Python yang diperlukan (FastAPI, Groq, Psycopg2).

---
*Terakhir diperbarui: April 2026. Dokumentasi ini disesuaikan dengan implementasi Conversational RAG terkini.*
