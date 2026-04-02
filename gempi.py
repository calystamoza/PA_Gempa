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


import streamlit as st
import time
import logging
import json

import numpy as np
from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

# ============================
# API KEY GROQ
# ============================
api_key = "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"

# ============================
# LOGGING
# ============================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GempaExpert")

# ============================
# GEMPA EXPERT CLASS
# ============================
class GempaExpert:
    def __init__(self, persist_directory: str):
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
        self.client = Groq(api_key=api_key)
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

    # ============================
    # Layer 1: Interpretasi Pertanyaan
    # ============================
    def interpret_question(self, question: str):
        prompt = f"""
Ekstrak informasi penting dari pertanyaan berikut:
- lokasi (provinsi/kota)
- tahun (4 digit)
- kata kunci penting

Anda adalah sistem ekstraksi informasi.
Tugas Anda hanya mengembalikan JSON valid.

Jika informasi tidak disebut, isi null. dan masukkan maksud user ke kata kunci

Format output ketat:
{{
  "lokasi": null atau string,
  "tahun": null atau string,
  "kata_kunci": []
}}

Pertanyaan:
"{question}"
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            raw = response.choices[0].message.content.strip()
            json_start = raw.find("{")
            json_end = raw.rfind("}") + 1
            clean_json = raw[json_start:json_end]
            parsed = json.loads(clean_json)
            return parsed
        except Exception as e:
            return {"lokasi": None, "tahun": None, "kata_kunci": [], "error": str(e)}

    # ============================
    # Layer 2: Metadata Retrieval
    # ============================
    def search_with_metadata(self, lokasi=None, tahun=None, top_k=500):
        where = {}
        if lokasi:
            where["provinsi"] = {"$contains": lokasi.upper()}
        if tahun:
            where["tahun"] = tahun
        try:
            results = self.vector_db.get(where=where)
            docs = [
                Document(page_content=txt, metadata=meta)
                for txt, meta in zip(results["documents"], results["metadatas"])
            ]
            return docs[:top_k]
        except Exception:
            return []

    # ============================
    # Hybrid Retrieval + Reranker
    # ============================
    def answer_question(self, question: str, top_k: int = 100):
        intent = self.interpret_question(question)
        vect = self.vector_db.similarity_search(question, k=800)
        if intent["lokasi"]:
            vect += self.vector_db.similarity_search(intent["lokasi"], k=200)
        if intent["tahun"]:
            vect += self.vector_db.similarity_search(intent["tahun"], k=200)
        for kw in intent["kata_kunci"]:
            vect += self.vector_db.similarity_search(kw, k=300)
        bm25 = self.bm25.invoke(question)[:300]
        combined = {d.page_content: d for d in (vect + bm25)}.values()
        docs = list(combined)
        pairs = [[question, doc.page_content] for doc in docs]
        scores = self.reranker.predict(pairs)
        for i, doc in enumerate(docs):
            doc.metadata["rerank_score"] = float(scores[i])
        sorted_docs = sorted(docs, key=lambda d: d.metadata["rerank_score"], reverse=True)
        return sorted_docs[:top_k], intent

    # ============================
    # Jawaban Final
    # ============================
    def generate_answer(self, question: str):
        start = time.time()
        intent = self.interpret_question(question)
        lokasi = intent.get("lokasi")
        tahun = intent.get("tahun")
        metadata_docs = self.search_with_metadata(lokasi, tahun, top_k=200)
        if len(metadata_docs) < 3:
            docs, intent = self.answer_question(question, top_k=20)
        else:
            docs = metadata_docs[:20]
        context = "\n\n".join(
            f"- Data {i+1}: {doc.page_content}"
            for i, doc in enumerate(docs)
        )
        prompt = f"""
Anda adalah sistem pakar seismologi.
Gunakan KONTEKS di bawah ini untuk menjawab.

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
            return output, dur, docs, intent
        except Exception as e:
            return f"Error: {e}", 0, [], intent

# ============================
# STREAMLIT CHATBOT UI
# ============================
st.set_page_config(page_title="Analisis Gempa Chatbot", layout="wide")
st.title("🌋 Chatbot Sistem Pakar Gempa (RAG Dua Lapisan + LLM)")

st.sidebar.header("Konfigurasi")
db_path = st.sidebar.text_input("Path ChromaDB", "./chroma_gempa_db")
load_model = st.sidebar.button("Inisialisasi Sistem")

# Inisialisasi expert
if load_model:
    expert = GempaExpert(db_path)
    st.session_state["expert"] = expert
    st.session_state["chat_history"] = []
    st.success("Sistem siap digunakan!")

# Input user
user_input = st.text_input("Ketik pertanyaan gempa:")
submit = st.button("Kirim")

# Handle chat
if submit:
    if "expert" not in st.session_state:
        st.error("Sistem belum diinisialisasi!")
    else:
        expert = st.session_state["expert"]
        with st.spinner("Mengolah pertanyaan..."):
            answer, dur, retrieved_docs, intent = expert.generate_answer(user_input)
        # Append to chat history
        st.session_state["chat_history"].append({"user": user_input, "bot": answer})

# Render chat
if "chat_history" in st.session_state:
    for chat in st.session_state["chat_history"]:
        st.markdown(f"**Anda:** {chat['user']}")
        st.markdown(f"**GempaExpert:** {chat['bot']}")
        st.markdown("---")
