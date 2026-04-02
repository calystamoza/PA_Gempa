import streamlit as st
import time
import json
import logging
from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
from collections import Counter

# API KEY & SETUP
api_key = "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"

class GempaExpert:
    def __init__(self, persist_directory: str):
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.vector_db = Chroma(persist_directory=persist_directory, embedding_function=self.embeddings)
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self._prepare_bm25()
        self.client = Groq(api_key=api_key)
        self.model_name = "llama-3.3-70b-versatile"

    def _prepare_bm25(self):
        data = self.vector_db.get()
        if not data["documents"]: raise ValueError("Database kosong!")
        self.all_docs = [Document(page_content=t, metadata=m) for t, m in zip(data["documents"], data["metadatas"])]
        self.bm25 = BM25Retriever.from_documents(self.all_docs)
        self.bm25.k = 300 # Meningkatkan jangkauan pencarian kata kunci

    def interpret_question(self, question: str):
        # AI sekarang dilatih untuk mengenali apakah user minta detail atau statistik
        prompt = f"""Tugas: Ekstrak JSON dari pertanyaan: "{question}"
        JSON format: {{"lokasi": null, "tahun": null, "is_statistis": boolean}}
        is_statistis=true jika tanya tren, pola, jumlah, rata-rata, atau perbandingan banyak data.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name, 
                messages=[{"role": "user", "content": prompt}], 
                temperature=0,
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
        except:
            return {"lokasi": None, "tahun": None, "is_statistis": False}

    def search_with_metadata(self, lokasi=None, tahun=None, top_k=2000):
        where = {}
        if lokasi: where["provinsi"] = {"$contains": lokasi.title()}
        if tahun: where["tahun"] = int(tahun) if str(tahun).isdigit() else str(tahun)
        try:
            results = self.vector_db.get(where=where)
            docs = [Document(page_content=txt, metadata=meta) for txt, meta in zip(results["documents"], results["metadatas"])]
            return docs[:top_k]
        except: return []

    def answer_question(self, question: str, intent: dict, candidates=None):
        # Jika candidates sudah ada (dari metadata), gunakan itu. Jika tidak, cari hybrid.
        if not candidates:
            vect = self.vector_db.similarity_search(question, k=400)
            bm25_docs = self.bm25.invoke(question)
            candidates = list({d.page_content: d for d in (vect + bm25_docs)}.values())
        
        if not candidates: return []
        
        # Reranking untuk mencari "DOKUMEN TUNGGAL" yang paling pas
        pairs = [[question, d.page_content] for d in candidates]
        scores = self.reranker.predict(pairs)
        for i, d in enumerate(candidates): d.metadata["score"] = float(scores[i])
        return sorted(candidates, key=lambda x: x.metadata["score"], reverse=True)[:50]

    def generate_answer(self, question: str):
        start = time.time()
        intent = self.interpret_question(question)
        
        # 1. SELALU TARIK DATA METADATA (Cepat dan Akurat untuk Lokasi/Tahun)
        all_relevant = self.search_with_metadata(intent.get("lokasi"), intent.get("tahun"))
        
        if intent.get("is_statistis") and all_relevant:
            # MODE TREN/POLA: Python menghitung angka, Llama menjelaskan
            total = len(all_relevant)
            mags = [d.metadata.get('magnitude', 0) for d in all_relevant]
            avg_mag = sum(mags)/total if total > 0 else 0
            max_mag = max(mags) if mags else 0
            
            # Buat ringkasan statistik untuk dikirim ke LLM
            stats_info = f"STATISTIK: Total {total} gempa, Mag Rata-rata: {avg_mag:.2f}, Mag Terbesar: {max_mag}."
            
            # Berikan sampel 100 baris data agar LLM bisa lihat pola waktu/hari
            samples = [f"{d.metadata.get('date')} | Mag: {d.metadata.get('magnitude')} | {d.metadata.get('province')}" for d in all_relevant[:100]]
            context = f"{stats_info}\n\nSAMPEL DATA:\n" + "\n".join(samples)
            docs_to_display = all_relevant[:20]
        else:
            # MODE DETAIL: Gunakan Reranker untuk mencari jawaban spesifik
            # Kita rerank hasil metadata tadi + hybrid search
            top_docs = self.answer_question(question, intent, candidates=all_relevant if all_relevant else None)
            context = "DETAIL DATA KEJADIAN:\n" + "\n".join([f"- {d.page_content}" for d in top_docs])
            docs_to_display = top_docs

        # 3. PROMPT KERAS (Wajib Pakai Data)
        prompt = f"""JAWAB PERTANYAAN HANYA BERDASARKAN DATA. 
        Jika data statistik ada, jelaskan trennya. Jika data detail ada, ceritakan kejadiannya.
        anda adalah ahli seismograf
        KONTEKS DATA:
        {context}
        
        PERTANYAAN: {question}"""

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "system", "content": "Anda asisten seismologi yang HANYA bicara berdasarkan data konteks."},
                      {"role": "user", "content": prompt}],
            temperature=0 
        )
        return response.choices[0].message.content, docs_to_display

# (Bagian UI Streamlit sama seperti sebelumnya)

# ============================
# STREAMLIT UI (CHATBOT MODE)
# ============================
st.title("🌋 ChatBot Gempa")
st.markdown("Asisten cerdas analisis sejarah dan data gempa bumi.")



with st.sidebar:
    st.header("Pengaturan")
    db_path = st.text_input("Path ChromaDB", "./chroma_gempa_db")
    if st.button("Hubungkan Database"):
        with st.spinner("Memuat model & menyiapkan database..."):
            st.session_state["expert"] = GempaExpert(db_path)
            st.session_state["messages"] = []
            st.success("Sistem Aktif!")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Tanyakan tren, jumlah, atau detail gempa..."):
    if "expert" not in st.session_state:
        st.error("Silakan hubungkan database di sidebar terlebih dahulu.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Menganalisis ribuan record data..."):
                full_response, source_docs = st.session_state["expert"].generate_answer(prompt)
            
            message_placeholder.markdown(full_response)
            
            with st.expander("Lihat Referensi Data"):
                for d in source_docs[:20]:
                    st.caption(f"Metadata: {d.metadata}")
                    st.write(d.page_content)
                    st.divider()

        st.session_state.messages.append({"role": "assistant", "content": full_response})