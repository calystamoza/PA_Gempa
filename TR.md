# Technical Requirements

## Earthquake Data Chatbot with RAG (Tabular Approach)

---

## 1. Project Overview

This project aims to develop a web-based chatbot application similar to ChatGPT that provides insights and answers related to earthquake data in Indonesia. The system utilizes a Retrieval-Augmented Generation (RAG) approach with structured (tabular) data instead of unstructured text.

The chatbot will allow users to:

* Ask questions about earthquake statistics
* Explore trends and patterns
* Retrieve contextual insights based on data
* Multi-turn conversation

---

## 2. System Architecture

### 2.1 High-Level Architecture

Frontend (Next.js)
↓
Backend API (Python - FastAPI)
↓
Database (PostgreSQL via Supabase)
↓
LLM (Gemini / OpenAI)

---

## 3. Core Features

### 3.1 Chat Interface

* Chat input and response display
* Streaming or real-time response (optional)
* Chat history per user
* UI menyerupai ChatGPT
* Mudah digunakan non-technical user

### 3.2 Chat History Management

* Save previous conversations
* Allow user to revisit past queries

### 3.3 Information Page

* Description of the system
* Explanation of earthquake data usage
* Disclaimer on AI limitations

### 3.4 Search Functionality

* Search past chats
* Search based on keywords

### 3.5 Data-Driven Insights (RAG)

* Answer questions based on earthquake dataset
* Perform statistical reasoning using structured data
* **Data Analysis Capability**

  Sistem harus mampu menjawab:

  * **Statistik** - Rata-rata magnitudo - Jumlah gempa dalam periode tertentu

  * **Temporal Analysis**
    - Tren gempa per tahun / bulan
    - Perbandingan antar periode

  * **Spasial Analysis**
    - Wilayah dengan frekuensi gempa tertinggi
    - Distribusi lokasi gempa

---

## 4. Data Specification

### 4.1 Dataset Structure

The dataset consists of ~150,000 rows with the following columns:

* id
* province
* date
* month
* month_name
* year
* latitude
* longitude
* magnitude
* depth
* depth_category
* fault_megathrust_id
* time

### 4.2 Data Characteristics

* Fully structured (tabular)
* Numeric and categorical data
* Time-series capable

---

## 5. RAG Approach (Tabular-Based)

##

### 5.1 Retrieval Strategy

Instead of vector embeddings, the system uses:

* SQL queries for filtering

* Aggregation (AVG, COUNT, MAX, MIN)

* Conditional selection (WHERE clauses)

---

### 5.2 LLM-Assisted Query Understanding (Hybrid RAG)

Sistem menggunakan pendekatan **LLM-assisted retrieval**, di mana LLM tidak langsung menjawab pertanyaan, tetapi digunakan untuk memahami intent pengguna dan membantu menentukan data yang perlu diambil dari database.

#### Flow Proses:

1. User mengirim pertanyaan (natural language)

2. LLM melakukan parsing dan menghasilkan struktur query (JSON)

3. Backend melakukan validasi terhadap output LLM

4. Backend membangun SQL query berdasarkan hasil parsing

5. Database mengeksekusi query dan mengembalikan data

6. Data digunakan sebagai context untuk LLM

7. LLM menghasilkan jawaban dalam bahasa natural

#### Contoh Output LLM (Parsing):

```json

{

  "intent": "average",

  "metric": "magnitude",

  "filters": {

    "province": "Jawa Barat",

    "year": 2024

  }

}5. RAG Approach (Tabular-Based)

### 5.1 Retrieval Strategy

Instead of vector embeddings, the system uses:

* SQL queries for filtering
* Aggregation (AVG, COUNT, MAX, MIN)
* Conditional selection (WHERE clauses)

### 5.2 Augmentation

Retrieved data is formatted into structured context:

Example:

* Average magnitude in West Java (2024): 4.3
* Total earthquakes: 1200 events

### 5.3 Generation

The LLM generates natural language responses based on:

* Retrieved statistics
* User question
* Prompt template

---

## 6. Backend Requirements

### 6.1 Framework

* Python (FastAPI)

### 6.2 Responsibilities

* Handle API requests
* Query database
* Construct prompts
* Call LLM API
* Return generated responses

### 6.3 API Endpoints

POST /chat

* Input: user query
* Output: generated response

GET /history

* Retrieve chat history

---

## 7. Database Requirements

### 7.1 Database System (masih dalam csv data/data_gempa_processed.csv)

* PostgreSQL (via Supabase)

### 7.2 Tables

#### earthquakes

* id (primary key)
* province
* date
* magnitude
* depth
* year
* etc.

#### chat_history

* id
* user_id
* query
* response
* timestamp

---

## 8. Frontend Requirements

### 8.1 Framework

* Next.js

### 8.2 UI Components

* Chat window
* Sidebar (chat history)
* Input field
* Search bar
* Information page

---

## 9. LLM Integration

### 9.1 Model Options

* Gemini API
* OpenAI API

### 9.2 Prompt Engineering

Two modes:

#### Global Analysis

* Trends over time
* Regional comparisons

#### Specific Query

* Filtered data insights

---

## 10. Non-Functional Requirements

### 10.1 Performance

* Query response < 5 seconds
* Efficient SQL indexing

### 10.2 Scalability

* Support multiple users

### 10.3 Security

* API key protection
* Secure database access

  - Error handling jika query tidak valid

  - Fallback jika LLM gagal generate query

---

## 11. Key Design Decisions

* No vector database used
* Tabular query-based RAG
* Focus on structured data reasoning

**12. Risks & Limitations**

- Query salah dari LLM (hallucinated code)

- Error pada Pandas execution

- Ambiguous query dari user

- Data tidak lengkap

---

## 13. Future Improvements

* Hybrid RAG (vector + SQL)
* Visualization (charts, maps)
* Real-time earthquake data integration

---

## 14. Conclusion

This system leverages structured earthquake data with a SQL-based RAG approach to provide accurate and explainable responses without relying on vector embeddings.
