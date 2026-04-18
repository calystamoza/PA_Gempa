import streamlit as st
import time
import logging

import numpy as np
from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder


# ============================
# LOGGING
# ============================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GempaExpert")


# ============================
# GEMPA EXPERT CLASS
# ============================
class GempaExpert:
    def __init__(self, persist_directory: str, groq_api_key: str):
        st.info("Memuat model embeddings...", icon="⚙️")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

        st.info("Memuat database Chroma...", icon="📦")
        self.vector_db = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings
        )

        st.info("Memuat cross-encoder reranker...", icon="📊")
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        self._prepare_bm25()

        st.info("Menghubungkan ke Groq LLM...", icon="🤖")
        self.client = Groq(api_key=groq_api_key)
        self.model_name = "llama-3.3-70b-versatile"

    def _prepare_bm25(self):
        data = self.vector_db.get()
        if not data["documents"]:
            raise ValueError("ChromaDB kosong!")

        self.all_docs = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(data["documents"], data["metadatas"])
        ]

        self.bm25 = BM25Retriever.from_documents(self.all_docs)
        self.bm25.k = 20

    def answer_question(self, question: str, top_k: int = 100):
        vect = self.vector_db.similarity_search(question, k=1000)
        bm25 = self.bm25.invoke(question)[:1000]

        combined = {d.page_content: d for d in (vect + bm25)}.values()
        docs = list(combined)

        pairs = [[question, doc.page_content] for doc in docs]
        scores = self.reranker.predict(pairs)

        for i, doc in enumerate(docs):
            doc.metadata["rerank_score"] = float(scores[i])

        sorted_docs = sorted(docs, key=lambda d: d.metadata["rerank_score"], reverse=True)
        return sorted_docs[:top_k]

    def generate_answer(self, question: str):
        start = time.time()
        docs = self.answer_question(question, top_k=20)

        context = "\n\n".join(
            f"- Data {i+1}: {doc.page_content}" for i, doc in enumerate(docs)
        )

        prompt = f"""
Anda adalah sistem pakar seismologi.

KONTEKS:
{context}

PERTANYAAN:
{question}

JAWABAN:
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )

            output = response.choices[0].message.content
            dur = time.time() - start
            return output, dur, docs

        except Exception as e:
            return f"Error: {e}", 0, []


# ============================
# STREAMLIT UI
# ============================
st.set_page_config(page_title="Analisis Gempa RAG", layout="wide")

st.title("🌋 Sistem Pakar Analisis Gempa (RAG + LLM)")
st.write("Tanyakan analisis terkait gempa berdasarkan database.")

# Sidebar
st.sidebar.header("Konfigurasi")
db_path = st.sidebar.text_input("Path ChromaDB", "./chroma_gempa_db")
api_key = st.sidebar.text_input("Groq API Key", type="password")

load_model = st.sidebar.button("Inisialisasi Sistem")

if load_model and api_key:
    expert = GempaExpert(db_path, api_key)
    st.session_state["expert"] = expert
    st.success("Sistem siap digunakan!")

# Input pertanyaan
query = st.text_input("Masukkan pertanyaan gempa:")
submit = st.button("Analisis")

if submit:
    if "expert" not in st.session_state:
        st.error("Sistem belum diinisialisasi!")
    else:
        with st.spinner("Mengolah pertanyaan..."):
            answer, dur, retrieved_docs = st.session_state["expert"].generate_answer(query)

        st.subheader("📌 Jawaban Analisis")
        st.write(answer)

        st.caption(f"⏱️ Waktu proses: {dur:.2f} detik")

        # Debug Retrieval Section
        with st.expander("🔍 Lihat dokumen hasil retrieval"):
            for i, doc in enumerate(retrieved_docs):
                st.write(f"### Dokumen {i+1} — Skor {doc.metadata['rerank_score']:.4f}")
                st.write(doc.page_content)
