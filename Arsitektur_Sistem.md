# 🏗️ Arsitektur & Dokumentasi GempaBot

Dokumen ini menjelaskan rancangan arsitektur lengkap aplikasi GempaBot berserta peran masing-masing folder, kegunaan setiap file secara mendetail, dan penugasan baris-baris kode kuncinya.

---

## 📂 1. Folder `backend`
Di sinilah "otak" sistem Anda berada. Menggunakan FastAPI (Python), backend bertugas menerima pertanyaan, mengolahnya dengan AI (Gemini), mengambil data di PostgreSQL, dan mengembalikan jawaban.

### 📄 `main.py`
**Fungsi:** Titik masuk utama aplikasi (entry point) dan penyedia jalur API (*Endpoints*).
*   **Baris 14:** `app = FastAPI(...)` - Inisialisasi peladen web utama FastAPI.
*   **Baris 16-22:** `CORSMiddleware` - Mengizinkan *frontend* (yang jalan di port lain) untuk berbicara ke backend tanpa diblokir browser.
*   **Baris 30-59:** `@app.post("/chat")` - Endpoint paling penting! Ini adalah jalur yang dipanggil frontend saat user mengirim pesan. Alurnya (Baris 34-52): mengecek session ID, membuat history baru jika kosong, menyimpan percakapan `user` ke database, lalu mengeksekusi mesin AI melalui fungsi `process_query()`, dan akhirnya menyimpan balasan `assistant` kembali ke DB.
*   **Baris 83-85:** `if __name__ == "__main__":` - Agar backend langsung menyala (`uvicorn.run`) di port 8000 ketika dieksekusi dengan `python main.py`.

### 📄 `rag_engine.py`
**Fungsi:** Mesin pemikir utama untuk proses RAG (Retrieval-Augmented Generation) milik Anda.
*   **Baris 10-11:** `model = genai.GenerativeModel(...)` - Menghidupkan agen AI Gemini. Baru-baru ini kita mengubahnya beberapa kali untuk menyiasati limit kuota Google (menggunakan versi `flash-latest`).
*   **Baris 18+ :** Rantai Pemrosesan Intent (*Prompting*). Bagian ini adalah "system prompt" yang mengarahkan instruksi ke agen AI agar AI **menerjemahkan** percakapan Bahasa Indonesia menjadi parameter objek JSON `{"query_type": ..., "filters": {...}}`.
*   **Fungsi `build_sql()`:** Bagian yang menerima output JSON AI lalu dikompilasi menjadi kueri SQL nyata (seperti mencocokkan `LOWER(place) LIKE '%aceh%'` atau `ORDER BY depth DESC LIMIT 5`).
*   **Fungsi `process_query(query, history)`:** Ini adalah **inti pipa logika (Pipeline)**. AI 1 (*Intent Parser*) ➔ Query Database ➔ AI 2 (*Response Generator*) yang membaca riwayat + data konkret, lalu menghasilkan balasan luwes ke user.

### 📄 `database.py`
**Fungsi:** Konektor dan pengelola perintah ke database cloud Supabase Anda.
*   **Baris 12-23:** `def get_connection():` - Menyambungkan `psycopg2` ke Supabase menggunakan `DATABASE_URL` yang diambil dari file rahasia `.env`.
*   **Baris 26-48:** Fungsi `execute_query(sql, params)` dan `execute_write(...)`. Ini adalah fungsi serbaguna yang aman (anti-bocor memory karena menggunakan *context manager* `with`) untuk menjalankan *SELECT*, maupun aksi *INSERT/UPDATE*.
*   **Baris 50+ :** Berisi pengelolaan Tabel Session (`create_session`, `get_sessions`) dan Tabel Message (`save_message`, `get_messages`), yang mencatat historis percakapan Anda layaknya struktur akun ChatGPT.

### 📄 `setup_db.sql`
**Fungsi:** Kerangka dasar pembuatan kolom pada tabel di Postgres. Berisi skript `CREATE TABLE earthquakes` beserta tipe datanya seperti Text, Float, Timestamp, dll., untuk dijalankan hanya satu kali di awal *deployment*.

### 📄 `upload_csv.py`
**Fungsi:** Skrip pengimpor data ribuan baris dari CSV ke dalam database.
*   **Baris 49-62:** Membaca file di folder `Data/` menggunakan Pandas (`pd.read_csv`). File *province* juga di-*rename* menjadi *place* sesuai perbaikan kita sebelumnya agar sesuai struktur database Supabase.
*   **Baris 83-110:** *Batching Insertion*. Karena *insert* 157.000 data sekaligus tidak mungkin, skrip ini memotongnya per 1000 baris lalu mengeksekusi `psycopg2.extras.execute_values`.

---

## 📂 2. Folder `frontend`
Folder ini berisi proyek Node.js/Next.js 16 berbasis React + TypeScript yang mengatur wajah dari aplikasi (Sistem UI).

### 📄 `app/page.tsx`
**Fungsi:** Komponen halaman utama (tampilan layar yang Anda buka di browser).
*   **Baris 16-21:** State manajemen lokal React (menampung `messages`, `loading`, status integrasi `sessionId`).
*   **Baris 44-74:** `handleSend(query)`. Fungsi yang aktif saat Anda menekan kirim. Dia memanggil API `sendMessage` (Backend), menampilkan gelembung teks user di layar, me-*loading* animasi "Gunung Meletus", lalu mencetak balasan AI.
*   **Baris 83+ :** Elemen tata letak HTML-React (JSX) yang merakit Sidebar, ChatHeader, dan Komponen Messages.

### 📄 `components/ChatWindow.tsx` & `MessageBubble.tsx`
**Fungsi:** Desain gelembung chat (User vs Assistant).
*   **MessageBubble.tsx - Baris 17:** `<ReactMarkdown>{message.content}</ReactMarkdown>`. (Perombakan yang baru kita kerjakan). Kode inilah yang bertanggung jawab menyulap *string* teks mentah AI, yang memiliki `**bintang**`, menjadi grafis cetak **tebal** (strong) yang cantik di browser.

### 📄 `app/globals.css`
**Fungsi:** Lembar penataan gaya absolut CSS seluruh web.
*   Membentuk nuansa kosmos / dark-mode yang solid.
*   **Baris 415-440 (Kira-kira):** Mengatur gaya `.bubble p` dan `.bubble strong`, yang menyesuaikan *margin* teks hasil cetakan Markdown kita.

### 📄 `lib/api.ts`
**Fungsi:** Pembungkus (*Wrapper*) fungsi AJAX agar bersih. Didalamnya ada fungsi `sendMessage` yang melakukan pemanggilan HTTP `fetch("http://localhost:8000/chat", ...)` untuk menembak API backend.

---

## 📂 3. Folder Akar / Lingkungan Kerja (Root)

### 📄 `.env`
**Fungsi:** Sangat penting dan sensitif! Ini adalah dompet rahasia keamanan Anda. (Tidak boleh naik ke internet publik / GitHub).
*   Menyimpan akses `GEMINI_API_KEY`.
*   Menyimpan akses Supabase (`DATABASE_URL`). Trik baru untuk masuk menggunakan fitur **IPv4 Supavisor** (Connection Pooler) harus dimasukkan melalui file ini.

### 📄 `Data/` (Folder)
**Fungsi:** "Gudang Berkas". Menampung aset `data_gempa_processed.csv` dengan ratusan ribu historikal gempa asli (BMKG / Institusi lain). Ini adalah bahan mentah yang tadi disedot oleh `upload_csv.py`.

---
*Dokumen ini dibuat otomatis sebagai rangkuman dan paduan sistem Anda oleh Agen Asisten AI. Simpan file ini sebagai referensi arsitektur saat mengembangkan fitur berikutnya!* 🚀
