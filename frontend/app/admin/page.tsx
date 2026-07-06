"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { insertEarthquake, uploadEarthquakeCSV, registerUser, getNextEarthquakeId } from "@/lib/api";

// ─── Date Parsing Helpers ─────────────────────────────────────────────────────

const MONTH_NAMES = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December",
];

const MONTH_NAME_MAP: Record<string, number> = {
  // English
  january:1, february:2, march:3, april:4, may:5, june:6,
  july:7, august:8, september:9, october:10, november:11, december:12,
  jan:1, feb:2, mar:3, apr:4, jun:6, jul:7, aug:8, sep:9, oct:10, nov:11, dec:12,
  // Indonesian
  januari:1, februari:2, maret:3, mei:5, juni:6, juli:7,
  agustus:8, oktober:10, desember:12,
};

interface ParsedDate { day: number; month: number; year: number; }

function parseDate(raw: string): ParsedDate | null {
  const s = raw.trim();
  if (!s) return null;

  // ISO: 2024-01-15
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (m) return { year: +m[1], month: +m[2], day: +m[3] };

  // d/m/yyyy  or  d-m-yyyy  or  d.m.yyyy
  m = s.match(/^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})$/);
  if (m) return { day: +m[1], month: +m[2], year: +m[3] };

  // "15 Maret 2024"  or  "15 March 2024"
  m = s.match(/^(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})$/);
  if (m) {
    const mn = MONTH_NAME_MAP[m[2].toLowerCase()];
    if (mn) return { day: +m[1], month: mn, year: +m[3] };
  }

  // "Maret 15 2024"  or  "March 15, 2024"
  m = s.match(/^([a-zA-Z]+)\s+(\d{1,2}),?\s+(\d{4})$/);
  if (m) {
    const mn = MONTH_NAME_MAP[m[1].toLowerCase()];
    if (mn) return { day: +m[2], month: mn, year: +m[3] };
  }

  return null;
}

function isValidDate(d: number, mo: number, y: number): boolean {
  if (y < 1900 || y > 2100 || mo < 1 || mo > 12 || d < 1) return false;
  return d <= new Date(y, mo, 0).getDate();
}

function formatDateStore(p: ParsedDate): string {
  // Format: d/m/yyyy (sesuai CSV)
  return `${p.day}/${p.month}/${p.year}`;
}

function formatDateISO(p: ParsedDate): string {
  return `${p.year}-${String(p.month).padStart(2,"0")}-${String(p.day).padStart(2,"0")}`;
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface UserInfo {
  user_id: string;
  username: string;
  role: "admin" | "user";
}

type TabType = "manual" | "csv" | "users";

const EMPTY_FORM = {
  id: "",
  place: "",
  date: "",        // d/m/yyyy — untuk payload
  month: "",       // auto-derive
  month_name: "",  // auto-derive
  year: "",        // auto-derive
  latitude: "",
  longitude: "",
  magnitude: "",
  depth: "",
  depth_category: "",
  time: "",        // YYYY-MM-DD HH:MM:SS — untuk payload
};

export default function AdminPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("manual");

  // Manual form state
  const [form, setForm] = useState(EMPTY_FORM);
  const [dateInput, setDateInput] = useState("");   // raw input dari user
  const [timeInput, setTimeInput] = useState("");   // HH:MM:SS dari user
  const [dateError, setDateError] = useState<string | null>(null);
  const [parsedDate, setParsedDate] = useState<ParsedDate | null>(null);
  const [manualLoading, setManualLoading] = useState(false);
  const [manualStatus, setManualStatus] = useState<{
    type: "success" | "error";
    msg: string;
  } | null>(null);

  // CSV upload state
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvLoading, setCsvLoading] = useState(false);
  const [csvResult, setCsvResult] = useState<{
    message: string;
    success: number;
    failed: number;
    errors: any[];
  } | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // User management state
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "user">("user");
  const [userLoading, setUserLoading] = useState(false);
  const [userStatus, setUserStatus] = useState<{
    type: "success" | "error";
    msg: string;
  } | null>(null);

  // ─── Guard: cek login & role ─────────────────────────────────────────────────

  useEffect(() => {
    const stored = localStorage.getItem("gempabot_user");
    if (!stored) { router.replace("/login"); return; }
    try {
      const u = JSON.parse(stored) as UserInfo;
      if (u.role !== "admin") { router.replace("/"); return; }
      setUser(u);
    } catch {
      localStorage.removeItem("gempabot_user");
      router.replace("/login");
    }
  }, [router]);

  // ─── Auto-fetch next ID saat user tersedia ───────────────────────────────────

  const fetchNextId = useCallback(async (u: UserInfo) => {
    const nextId = await getNextEarthquakeId(u.role);
    if (nextId) setForm((prev) => ({ ...prev, id: nextId }));
  }, []);

  useEffect(() => {
    if (user) fetchNextId(user);
  }, [user, fetchNextId]);

  const handleLogout = () => {
    localStorage.removeItem("gempabot_user");
    router.push("/login");
  };

  // ─── Date change — parse & derive month/year ─────────────────────────────────

  const handleDateChange = (raw: string) => {
    setDateInput(raw);
    setDateError(null);

    if (!raw.trim()) {
      setParsedDate(null);
      setForm((prev) => ({ ...prev, date: "", month: "", month_name: "", year: "", time: "" }));
      setTimeInput("");
      return;
    }

    const parsed = parseDate(raw);
    if (!parsed) {
      setDateError("Format tanggal tidak dikenali. Coba: 15/3/2024, 15-03-2024, 15 Maret 2024, atau 2024-03-15");
      setParsedDate(null);
      return;
    }
    if (!isValidDate(parsed.day, parsed.month, parsed.year)) {
      setDateError(`Tanggal tidak valid: ${parsed.day}/${parsed.month}/${parsed.year}`);
      setParsedDate(null);
      return;
    }

    setParsedDate(parsed);
    const stored = formatDateStore(parsed);
    const isoDate = formatDateISO(parsed);
    const composedTime = timeInput.trim() ? `${isoDate} ${timeInput.trim()}` : "";

    setForm((prev) => ({
      ...prev,
      date: stored,
      month: String(parsed.month),
      month_name: MONTH_NAMES[parsed.month - 1],
      year: String(parsed.year),
      time: composedTime,
    }));
  };

  // ─── Time change — hanya HH:MM:SS, compose dengan tanggal ───────────────────

  const handleTimeChange = (raw: string) => {
    setTimeInput(raw);
    if (parsedDate && raw.trim()) {
      const isoDate = formatDateISO(parsedDate);
      setForm((prev) => ({ ...prev, time: `${isoDate} ${raw.trim()}` }));
    } else {
      setForm((prev) => ({ ...prev, time: "" }));
    }
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  // ─── Depth change — auto-derive category ────────────────────────────────────

  const handleDepthChange = (raw: string) => {
    setForm((prev) => {
      const d = parseFloat(raw);
      let cat = "";
      if (!isNaN(d) && raw.trim() !== "") {
        if (d <= 60) cat = "dangkal";
        else if (d <= 300) cat = "menengah";
        else cat = "dalam";
      }
      return { ...prev, depth: raw, depth_category: cat };
    });
  };

  // ─── Submit ──────────────────────────────────────────────────────────────────

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (dateInput.trim() && !parsedDate) {
      setManualStatus({ type: "error", msg: "Tanggal tidak valid — perbaiki format tanggal terlebih dahulu." });
      return;
    }

    setManualLoading(true);
    setManualStatus(null);
    try {
      const payload = {
        id: form.id.trim(),
        place: form.place || undefined,
        date: form.date || undefined,
        month: form.month ? parseInt(form.month) : undefined,
        month_name: form.month_name || undefined,
        year: form.year ? parseInt(form.year) : undefined,
        latitude: form.latitude ? parseFloat(form.latitude) : undefined,
        longitude: form.longitude ? parseFloat(form.longitude) : undefined,
        magnitude: form.magnitude ? parseFloat(form.magnitude) : undefined,
        depth: form.depth ? parseFloat(form.depth) : undefined,
        depth_category: form.depth_category || undefined,
        time: form.time || undefined,
      };
      await insertEarthquake(payload, "admin");
      setManualStatus({ type: "success", msg: `✅ Data gempa ID "${form.id}" berhasil ditambahkan!` });
      // Reset form & fetch ID baru
      setDateInput("");
      setTimeInput("");
      setParsedDate(null);
      setDateError(null);
      const newId = user ? await getNextEarthquakeId(user.role) : "";
      setForm({ ...EMPTY_FORM, id: newId });
    } catch (err: any) {
      setManualStatus({ type: "error", msg: err.message });
    } finally {
      setManualLoading(false);
    }
  };

  // ─── CSV Upload ─────────────────────────────────────────────────────────────

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file?.name.endsWith(".csv")) setCsvFile(file);
  };

  const handleCsvUpload = async () => {
    if (!csvFile) return;
    setCsvLoading(true);
    setCsvResult(null);
    try {
      const result = await uploadEarthquakeCSV(csvFile, "admin");
      setCsvResult(result);
    } catch (err: any) {
      setCsvResult({
        message: err.message,
        success: 0,
        failed: 0,
        errors: err.errors || [],
      });
    } finally {
      setCsvLoading(false);
    }
  };

  // ─── User Management ────────────────────────────────────────────────────────

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim() || !newPassword.trim()) {
      setUserStatus({ type: "error", msg: "Username dan password wajib diisi" });
      return;
    }
    setUserLoading(true);
    setUserStatus(null);
    try {
      await registerUser(newUsername.trim(), newPassword, newRole, "admin");
      setUserStatus({ type: "success", msg: `User "${newUsername}" berhasil dibuat sebagai ${newRole}!` });
      setNewUsername("");
      setNewPassword("");
      setNewRole("user");
    } catch (err: any) {
      setUserStatus({ type: "error", msg: err.message });
    } finally {
      setUserLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="admin-shell">
      {/* Header */}
      <header className="admin-header">
        <div className="admin-header-left">
          <span className="admin-logo-icon">🌋</span>
          <div>
            <div className="admin-header-title">GempaBot Admin</div>
            <div className="admin-header-sub">Panel Manajemen Data</div>
          </div>
        </div>
        <div className="admin-header-right">
          <div className="admin-user-chip">
            <span className="admin-user-avatar">👑</span>
            <span>{user.username}</span>
            <span className="admin-role-badge">Admin</span>
          </div>
          <button className="admin-logout-btn" onClick={handleLogout} id="admin-logout-btn">
            Keluar
          </button>
        </div>
      </header>

      {/* Tab Nav */}
      <nav className="admin-tabs">
        {(["manual", "csv", "users"] as TabType[]).map((tab) => (
          <button
            key={tab}
            id={`admin-tab-${tab}`}
            className={`admin-tab-btn ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === "manual" && "📝 Input Manual"}
            {tab === "csv" && "📂 Upload CSV"}
            {tab === "users" && "👥 Kelola User"}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="admin-content">

        {/* ── Manual Input ── */}
        {activeTab === "manual" && (
          <div className="admin-panel">
            <div className="admin-panel-header">
              <h2>📝 Tambah Data Gempa Manual</h2>
              <p>ID otomatis digenerate. Tanggal mendukung berbagai format — bulan, tahun, dan waktu lengkap akan otomatis terisi.</p>
            </div>
            <form className="eq-form" onSubmit={handleManualSubmit} id="manual-earthquake-form">
              <div className="eq-form-grid">

                {/* ID — read only, auto-generated */}
                <div className="eq-field full-width">
                  <label className="eq-label">ID Gempa <span className="eq-auto-badge">🤖 Auto</span></label>
                  <div className="eq-readonly-wrap">
                    <input
                      id="eq-id"
                      className="eq-input eq-input-readonly"
                      value={form.id}
                      readOnly
                      tabIndex={-1}
                      placeholder="Memuat ID…"
                    />
                    <span className="eq-readonly-hint">ID ini otomatis berurutan dari data terakhir</span>
                  </div>
                </div>

                {/* Place */}
                <div className="eq-field">
                  <label className="eq-label" htmlFor="eq-place">Lokasi (Provinsi)</label>
                  <input id="eq-place" className="eq-input" name="place" value={form.place} onChange={handleFormChange} placeholder="Contoh: Jawa Barat" />
                </div>

                {/* Date — smart parser */}
                <div className="eq-field">
                  <label className="eq-label" htmlFor="eq-date">
                    Tanggal
                    {parsedDate && (
                      <span className="eq-derived-badge">
                        ✅ {parsedDate.day}/{parsedDate.month}/{parsedDate.year}
                      </span>
                    )}
                  </label>
                  <input
                    id="eq-date"
                    className={`eq-input ${dateError ? "eq-input-error" : parsedDate ? "eq-input-ok" : ""}`}
                    value={dateInput}
                    onChange={(e) => handleDateChange(e.target.value)}
                    placeholder="15/3/2024, 15-03-2024, 15 Maret 2024, 2024-03-15…"
                  />
                  {dateError && <div className="eq-field-error">⚠️ {dateError}</div>}
                  {parsedDate && (
                    <div className="eq-field-ok">
                      📅 Bulan: <strong>{form.month_name}</strong> &nbsp;|&nbsp; Tahun: <strong>{form.year}</strong>
                    </div>
                  )}
                </div>

                {/* Time — only HH:MM:SS */}
                <div className="eq-field">
                  <label className="eq-label" htmlFor="eq-time">
                    Waktu (HH:MM:SS)
                    {!parsedDate && <span className="eq-hint-inline"> — isi tanggal dulu</span>}
                  </label>
                  <input
                    id="eq-time"
                    className="eq-input"
                    value={timeInput}
                    onChange={(e) => handleTimeChange(e.target.value)}
                    placeholder="14:32:00"
                    disabled={!parsedDate}
                  />
                  {form.time && (
                    <div className="eq-field-ok">🕐 Tersimpan: <strong>{form.time}</strong></div>
                  )}
                </div>

                {/* Latitude */}
                <div className="eq-field">
                  <label className="eq-label" htmlFor="eq-lat">Latitude</label>
                  <input id="eq-lat" className="eq-input" name="latitude" type="number" step="any" value={form.latitude} onChange={handleFormChange} placeholder="Contoh: -6.2" />
                </div>

                {/* Longitude */}
                <div className="eq-field">
                  <label className="eq-label" htmlFor="eq-lon">Longitude</label>
                  <input id="eq-lon" className="eq-input" name="longitude" type="number" step="any" value={form.longitude} onChange={handleFormChange} placeholder="Contoh: 106.8" />
                </div>

                {/* Magnitude */}
                <div className="eq-field">
                  <label className="eq-label" htmlFor="eq-magnitude">Magnitudo (Mw)</label>
                  <input id="eq-magnitude" className="eq-input" name="magnitude" type="number" step="any" value={form.magnitude} onChange={handleFormChange} placeholder="Contoh: 5.6" />
                </div>

                {/* Depth — auto-derive category */}
                <div className="eq-field">
                  <label className="eq-label" htmlFor="eq-depth">
                    Kedalaman (km)
                    {form.depth_category && (
                      <span className={`eq-derived-badge eq-depth-${form.depth_category}`}>
                        {form.depth_category === "dangkal" && "🟢 Dangkal (≤60 km)"}
                        {form.depth_category === "menengah" && "🟡 Menengah (60–300 km)"}
                        {form.depth_category === "dalam" && "🔴 Dalam (>300 km)"}
                      </span>
                    )}
                  </label>
                  <input
                    id="eq-depth"
                    className="eq-input"
                    name="depth"
                    type="number"
                    step="any"
                    min={0}
                    value={form.depth}
                    onChange={(e) => handleDepthChange(e.target.value)}
                    placeholder="Contoh: 10"
                  />
                  {form.depth && !form.depth_category && (
                    <div className="eq-field-error">⚠️ Masukkan angka kedalaman yang valid</div>
                  )}
                </div>

              </div>

              {manualStatus && (
                <div className={`admin-status-msg ${manualStatus.type}`}>
                  {manualStatus.type === "success" ? "✅" : "❌"} {manualStatus.msg}
                </div>
              )}

              <button id="manual-submit-btn" className="admin-action-btn" type="submit" disabled={manualLoading || !!dateError}>
                {manualLoading ? <span className="btn-spinner" /> : "💾 Simpan Data Gempa"}
              </button>
            </form>
          </div>
        )}

        {/* ── CSV Upload ── */}
        {activeTab === "csv" && (
          <div className="admin-panel">
            <div className="admin-panel-header">
              <h2>📂 Upload Data Gempa via CSV</h2>
              <p>
                Upload file CSV. Kolom pendukung: <code>id, place, date, time, latitude, longitude, magnitude, depth</code>.
                ID akan otomatis digenerate jika kosong. Format tanggal akan disesuaikan otomatis (termasuk auto-isi bulan, tahun, dan kategori kedalaman).
              </p>
            </div>

            <div
              id="csv-drop-zone"
              className={`csv-dropzone ${dragOver ? "drag-over" : ""} ${csvFile ? "has-file" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                style={{ display: "none" }}
                id="csv-file-input"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) setCsvFile(f);
                }}
              />
              {csvFile ? (
                <div className="csv-file-info">
                  <span className="csv-file-icon">📄</span>
                  <div>
                    <div className="csv-file-name">{csvFile.name}</div>
                    <div className="csv-file-size">{(csvFile.size / 1024).toFixed(1)} KB</div>
                  </div>
                  <button
                    className="csv-remove-btn"
                    onClick={(e) => { e.stopPropagation(); setCsvFile(null); setCsvResult(null); }}
                  >
                    ✕
                  </button>
                </div>
              ) : (
                <>
                  <span className="csv-drop-icon">📂</span>
                  <p className="csv-drop-text">Drag & drop file CSV di sini, atau <span className="csv-drop-link">klik untuk browse</span></p>
                  <p className="csv-drop-hint">Format: .csv — maks 10MB</p>
                </>
              )}
            </div>

            {csvResult && (
              <div className={`csv-result-box ${csvResult.failed === 0 ? "success" : "partial"}`}>
                <div className="csv-result-summary">
                  <span className="csv-result-badge success-badge">✅ {csvResult.success} berhasil</span>
                  {csvResult.failed > 0 && (
                    <span className="csv-result-badge error-badge">❌ {csvResult.failed} gagal</span>
                  )}
                </div>
                <p className="csv-result-msg">{csvResult.message}</p>
                {csvResult.errors.length > 0 && (
                  <div className="csv-errors-list">
                    <div className="csv-errors-title">Detail Error:</div>
                    {csvResult.errors.slice(0, 10).map((err, i) => (
                      <div key={i} className="csv-error-item">
                        Baris {err.row} (ID: {err.data}): {err.error}
                      </div>
                    ))}
                    {csvResult.errors.length > 10 && (
                      <div className="csv-error-item muted">...dan {csvResult.errors.length - 10} error lainnya</div>
                    )}
                  </div>
                )}
              </div>
            )}

            <button
              id="csv-upload-btn"
              className="admin-action-btn"
              onClick={handleCsvUpload}
              disabled={!csvFile || csvLoading}
            >
              {csvLoading ? <span className="btn-spinner" /> : "⬆️ Upload & Import CSV"}
            </button>
          </div>
        )}

        {/* ── User Management ── */}
        {activeTab === "users" && (
          <div className="admin-panel">
            <div className="admin-panel-header">
              <h2>👥 Tambah User Baru</h2>
              <p>Buat akun user baru dengan role <strong>user</strong> (akses chat) atau <strong>admin</strong> (akses panel ini).</p>
            </div>
            <form className="user-form" onSubmit={handleAddUser} id="add-user-form">
              <div className="eq-form-grid">
                <div className="eq-field">
                  <label className="eq-label" htmlFor="new-username">Username <span className="req">*</span></label>
                  <input
                    id="new-username"
                    className="eq-input"
                    type="text"
                    placeholder="Masukkan username"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    disabled={userLoading}
                  />
                </div>

                <div className="eq-field">
                  <label className="eq-label" htmlFor="new-password">Password <span className="req">*</span></label>
                  <input
                    id="new-password"
                    className="eq-input"
                    type="password"
                    placeholder="Masukkan password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    disabled={userLoading}
                  />
                </div>

                <div className="eq-field">
                  <label className="eq-label" htmlFor="new-role">Role</label>
                  <select
                    id="new-role"
                    className="eq-input eq-select"
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value as "admin" | "user")}
                    disabled={userLoading}
                  >
                    <option value="user">User (Chat only)</option>
                    <option value="admin">Admin (Full access)</option>
                  </select>
                </div>
              </div>

              {userStatus && (
                <div className={`admin-status-msg ${userStatus.type}`}>
                  {userStatus.type === "success" ? "✅" : "❌"} {userStatus.msg}
                </div>
              )}

              <button id="add-user-btn" className="admin-action-btn" type="submit" disabled={userLoading}>
                {userLoading ? <span className="btn-spinner" /> : "➕ Buat User"}
              </button>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
