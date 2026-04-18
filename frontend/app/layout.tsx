import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "GempaBot — Chatbot Data Gempa Indonesia",
  description:
    "Chatbot cerdas berbasis RAG untuk analisis data gempa bumi Indonesia. Tanyakan statistik, tren, dan distribusi gempa secara natural.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
