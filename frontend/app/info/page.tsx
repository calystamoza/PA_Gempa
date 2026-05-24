import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Tentang GempaBot — Sistem Informasi Gempa Indonesia",
  description: "Informasi tentang GempaBot, sistem chatbot berbasis RAG untuk data gempa bumi Indonesia.",
};

export default function InfoPage() {
  return (
    <div className="app-shell">
      <div className="main" style={{ overflowY: "auto" }}>
        <div className="info-page">
          <Link href="/" className="back-btn">
            ← Kembali ke Chat
          </Link>

          <h1>🌋 Tentang GempaBot</h1>
          <p className="subtitle">
            Sistem chatbot cerdas untuk eksplorasi data gempa bumi Indonesia
          </p>

          <div className="info-card">
            <h2>📖 Apa itu GempaBot?</h2>
            <p>
              GempaBot adalah asisten AI berbasis teknologi{" "}
              <strong>Retrieval-Augmented Generation (RAG)</strong> yang
              dirancang untuk membantu pengguna mengeksplorasi data gempa bumi
              Indonesia secara interaktif. Sistem ini menggunakan database
              terstruktur dengan lebih dari 150.000 catatan kejadian gempa dari
              seluruh wilayah Indonesia dalam kurun waktu 2018-2024.
            </p>
          </div>

          <div className="info-card">
            <h2>📊 Data yang Digunakan</h2>
            <ul>
              <li>Lebih dari 150.000 catatan kejadian gempa di Indonesia 2018-2024</li>
              <li>Data yang digunakan merupakan data sekunder yang bersumber dari USGS dan BMKG</li>
              <li>Mencakup data magnitudo, kedalaman, lokasi, dan waktu</li>
              <li>Dikelompokkan berdasarkan provinsi dan kategori kedalaman</li>
              <li>Data mencakup periode beberapa dekade kebelakang</li>
            </ul>
          </div>

          <div className="info-card">
            <h2>⚙️ Cara Kerja Sistem</h2>
            <ul>
              <li>
                <strong>Pemahaman Intent:</strong> Pertanyaan dianalisis oleh
                Groq AI menggunakan llama-3.1-8b-instant untuk memahami maksud pengguna
              </li>
              <li>
                <strong>SQL Generation:</strong> Sistem membangun query SQL
                berdasarkan intent yang terdeteksi
              </li>
              <li>
                <strong>Data Retrieval:</strong> Query dieksekusi ke database
                PostgreSQL untuk mendapatkan data relevan
              </li>
              <li>
                <strong>Response Generation:</strong> Groq AI menghasilkan
                jawaban natural berdasarkan data yang ditemukan
              </li>
            </ul>
          </div>

          <div className="info-card">
            <h2>💬 Contoh Pertanyaan</h2>
            <ul>
              <li>Berapa rata-rata magnitudo gempa di Jawa Barat tahun 2023?</li>
              <li>Wilayah mana yang paling sering mengalami gempa?</li>
              <li>Tunjukkan tren jumlah gempa per tahun di Indonesia</li>
              <li>Gempa terkuat yang pernah terjadi di Sulawesi?</li>
              <li>Berapa jumlah gempa dangkal di NTB tahun 2022?</li>
            </ul>
          </div>

          <div className="disclaimer">
            ⚠️ <strong>Disclaimer:</strong> GempaBot adalah sistem berbasis AI
            yang menganalisis data historis gempa bumi. Sistem ini{" "}
            <strong>bukan</strong> sistem peringatan dini gempa dan{" "}
            <strong>tidak dapat</strong> memprediksi gempa di masa mendatang.
            Untuk informasi resmi dan terkini, selalu merujuk ke{" "}
            <strong>BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)</strong>{" "}
            di bmkg.go.id.
          </div>
        </div>
      </div>
    </div>
  );
}
