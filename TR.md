# Technical Requirements
## Chatbot Analisis Gempa Indonesia Berbasis LLM + Pandas Query Engine (LlamaIndex)

---

## 1. Overview Sistem

Sistem ini merupakan web-based chatbot untuk analisis data gempa Indonesia yang memungkinkan pengguna mengajukan pertanyaan dalam bahasa natural.

Berbeda dengan pendekatan RAG tradisional yang berbasis text retrieval, sistem ini menggunakan:
- **Pandas Query Engine (LlamaIndex)** untuk analisis data tabular
- **LLM** untuk interpretasi query dan generasi jawaban

Sistem mampu:
- Memahami pertanyaan user
- Mengubahnya menjadi query terhadap data tabular
- Menghasilkan jawaban berbasis data secara deskriptif

---

## 2. Arsitektur Sistem

### 2.1 High-Level Architecture

User → Frontend → Backend API → Query Engine (LlamaIndex) → Pandas DataFrame → LLM → Response

---

### 2.2 Komponen Utama

1. **Frontend (Web UI)**
2. **Backend API (Python)**
3. **LlamaIndex Query Engine**
4. **Pandas DataFrame (Data Gempa)**
5. **LLM (Inference Engine)**

---

## 3. Functional Requirements

### 3.1 Chat System
- User dapat menginput pertanyaan dalam bahasa natural
- Sistem memberikan jawaban berbasis data
- Mendukung multi-turn conversation (optional)

### 3.2 Data Analysis Capability
Sistem harus mampu menjawab:

#### Statistik
- Rata-rata magnitudo
- Jumlah gempa dalam periode tertentu

#### Temporal Analysis
- Tren gempa per tahun / bulan
- Perbandingan antar periode

#### Spasial Analysis
- Wilayah dengan frekuensi gempa tertinggi
- Distribusi lokasi gempa

#### Filtering
- Berdasarkan:
  - waktu
  - magnitudo
  - lokasi
  - kedalaman

---

### 3.3 Chat History
- Menyimpan riwayat percakapan
- Sidebar untuk navigasi chat

### 3.4 Search Chat
- Pencarian chat berdasarkan keyword

### 3.5 Information Page
- Penjelasan sistem
- Cara kerja LLM + Query Engine

---

## 4. Non-Functional Requirements

### 4.1 Performance
- Response time < 5 detik
- Query Pandas efisien

### 4.2 Usability
- UI menyerupai ChatGPT
- Mudah digunakan non-technical user

### 4.3 Reliability
- Error handling jika query tidak valid
- Fallback jika LLM gagal generate query

---

## 5. Teknologi yang Digunakan

### 5.1 Frontend
- Next.js (recommended)
- React.js
- (Prototype: Streamlit)

### 5.2 Backend
- Python (FastAPI)

### 5.3 Data Processing
- Pandas

### 5.4 LLM Framework
- LlamaIndex

### 5.5 Query Engine
- **Pandas Query Engine (LlamaIndex)**

### 5.6 LLM
- Groq (LLaMA 3 / LLaMA 3.3)
- OpenAI (optional)

---

## 6. Data Handling

### 6.1 Data Source
- Dataset gempa (BMKG / historical dataset)

### 6.2 Format
- CSV / DataFrame

### 6.3 Preprocessing
- Cleaning data
- Normalisasi format waktu
- Handling missing values

---

## 7. Query Engine Design

### 7.1 Alur Query

1. User Input (Natural Language)
2. LLM memahami intent
3. LlamaIndex mengubah query → Pandas operation
4. Eksekusi pada DataFrame
5. Hasil dikembalikan ke LLM
6. LLM generate jawaban deskriptif

---

### 7.2 Contoh Transformasi Query

User:
"Berapa rata-rata magnitudo gempa tahun 2023?"

→ LLM generate:
df[df['year'] == 2023]['magnitude'].mean()

---

User:
"Wilayah mana paling sering gempa?"

→ LLM generate:
df['location'].value_counts()

---

## 8. (Optional) Hybrid RAG Integration

Meskipun fokus utama adalah tabular query, sistem dapat dikembangkan menjadi hybrid:

### Kapan RAG digunakan?
- Penjelasan konsep gempa
- Informasi non-numerik
- Knowledge tambahan

### Tools:
- ChromaDB / FAISS
- Embedding model

---

## 9. UI/UX Requirements

### 9.1 Layout

#### Sidebar
- Chat history
- New chat
- Search chat

#### Main Area
- Chat conversation
- Input box

#### Navigation
- Home
- Information page

---

## 10. API Design

### POST /chat
Request:
{
  "message": "string",
  "chat_id": "string"
}

Response:
{
  "response": "string",
  "type": "tabular | rag | hybrid"
}

---

### GET /history
- Mengambil riwayat chat

---

## 11. Deployment

### Development
- Local environment

### Production
- Frontend: Vercel
- Backend: Railway / Render
- LLM: API (Groq/OpenAI)

---

## 12. Risks & Limitations

- Query salah dari LLM (hallucinated code)
- Error pada Pandas execution
- Ambiguous query dari user
- Data tidak lengkap

---

## 13. Future Improvements

- Visualisasi grafik (matplotlib / plotly)
- Auto-generated charts dari query
- Real-time data integration
- Advanced analytics

---

## 14. Kesimpulan Teknis

Sistem ini mengadopsi pendekatan:
- **LLM + Pandas Query Engine (LlamaIndex)**

Keunggulan:
- Tidak perlu transformasi data ke text
- Lebih akurat untuk analisis numerik
- Lebih efisien dibanding RAG tradisional

Pendekatan ini menjadikan sistem lebih:
- Data-driven
- Scalable
- Modern dalam konteks NLP dan data analysis