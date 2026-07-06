"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // Jika sudah login, redirect langsung
  useEffect(() => {
    const stored = localStorage.getItem("gempabot_user");
    if (stored) {
      try {
        const user = JSON.parse(stored);
        if (user?.role === "admin") router.replace("/admin");
        else router.replace("/");
      } catch {
        localStorage.removeItem("gempabot_user");
      }
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Username dan password wajib diisi");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const user = await login(username.trim(), password);
      localStorage.setItem("gempabot_user", JSON.stringify(user));
      if (user.role === "admin") router.push("/admin");
      else router.push("/");
    } catch (err: any) {
      setError(err.message || "Login gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-bg-glow" />

      <div className="login-card">
        {/* Logo */}
        <div className="login-logo">
          <span className="login-logo-icon">🌋</span>
          <h1 className="login-title">GempaBot</h1>
          <p className="login-subtitle">Asisten Data Gempa Indonesia</p>
        </div>

        {/* Form */}
        <form className="login-form" onSubmit={handleSubmit} noValidate>
          <div className="login-field">
            <label className="login-label" htmlFor="username">
              Username
            </label>
            <div className="login-input-wrap">
              <span className="login-input-icon">👤</span>
              <input
                id="username"
                className="login-input"
                type="text"
                placeholder="Masukkan username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                disabled={loading}
              />
            </div>
          </div>

          <div className="login-field">
            <label className="login-label" htmlFor="password">
              Password
            </label>
            <div className="login-input-wrap">
              <span className="login-input-icon">🔒</span>
              <input
                id="password"
                className="login-input"
                type={showPassword ? "text" : "password"}
                placeholder="Masukkan password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                disabled={loading}
              />
              <button
                type="button"
                className="login-eye-btn"
                onClick={() => setShowPassword((v) => !v)}
                tabIndex={-1}
                aria-label="Toggle password visibility"
              >
                {showPassword ? "🙈" : "👁️"}
              </button>
            </div>
          </div>

          {error && (
            <div className="login-error" role="alert">
              ⚠️ {error}
            </div>
          )}

          <button
            id="login-submit-btn"
            className="login-btn"
            type="submit"
            disabled={loading}
          >
            {loading ? (
              <span className="login-spinner" />
            ) : (
              "Masuk"
            )}
          </button>
        </form>

        <p className="login-footer-note">
          Sistem informasi gempa bumi berbasis RAG
        </p>
      </div>
    </div>
  );
}
