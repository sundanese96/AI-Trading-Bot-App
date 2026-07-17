# 🚀 KriptoSakti: Advanced AI Crypto Simulator & ML Trading Bot

KriptoSakti adalah simulator perdagangan kripto real-time berkinerja tinggi yang mengintegrasikan analisis sentimen AI (Gemini) dan model prediksi Machine Learning lokal untuk mensimulasikan bot perdagangan otomatis.

---

## ✨ Fitur Utama

1. **Live Crypto Price Ticker (Modular & Sticky)**
   - Menampilkan harga terupdate dari aset kripto utama (BTC, ETH, SOL, XRP), emas (XAU), serta indeks DXY secara langsung di bawah header.
   - Posisi tetap menempel di atas layar (*sticky*) saat menggulir halaman, dilengkapi dengan animasi kedip (*price flash*) hijau/merah saat terjadi fluktuasi harga.
   - Navigasi interaktif: klik pada koin untuk langsung membuka tab trading aset tersebut.

2. **Desk Trading Terminal**
   - Chart interaktif Candlestick (data langsung dari Binance API).
   - Tiket eksekusi order (Margin/Spot) dengan opsi *Leverage*, *Stop Loss*, *Take Profit*, dan *Trailing Stop*.
   - Manajemen posisi aktif secara real-time.

3. **Sentimen Berita & RAG Pipeline**
   - Scraper berita otomatis dari media crypto terpercaya.
   - Klasifikasi sentimen berita dan penaksiran level keyakinan menggunakan LLM (Gemini).

4. **AI Auto-Trade Control Room**
   - Robot trading otomatis berbasis sentimen makro dan keyakinan LLM.
   - Pengaturan level keyakinan minimal, manajemen alokasi portofolio, dan parameter risiko dinamis.
   - Konsol aktivitas bot yang menampilkan log analisis *step-by-step* secara langsung.

5. **ML & AI Model Local Training**
   - Pelatihan model klasifikasi Machine Learning (XGBoost, CatBoost, LightGBM) langsung dari UI.
   - Pelacakan metrik akurasi (*Shapley values*, *regime classification*, *whale movement validation*).

---

## 🛠️ Tech Stack

* **Frontend**: React, TypeScript, Tailwind CSS v4, Lucide Icons, Recharts.
* **Backend**: Python FastAPI, XGBoost, CatBoost, LightGBM, Pandas, Scikit-learn, HTTPX.
* **Database**: JSON-based state database manager.

---

## 🚀 Cara Menjalankan Aplikasi Secara Lokal

### Prasyarat
* Node.js (v18 ke atas)
* Python 3.10 / 3.11

### 1. Setup Backend
Masuk ke direktori `backend`, instal dependensi, lalu jalankan server FastAPI:
```bash
# Instal dependensi Python
pip install -r backend/requirements.txt

# Jalankan server
python backend/main.py
```
*Server backend akan berjalan secara default di port `3000`.*

### 2. Setup Frontend
Di direktori utama proyek, instal dependensi NPM dan jalankan Vite dev server:
```bash
# Instal dependensi npm
npm install

# Jalankan Vite Development Server
npm run dev
```
*Buka browser Anda dan akses halaman di `http://localhost:5173` (atau port yang tertera pada konsol Anda).*

---

## 📂 Struktur Proyek Utama

```bash
├── backend/                  # Kode backend Python FastAPI
│   ├── models/               # Model ML yang telah dilatih (XGBoost, LightGBM, CatBoost)
│   ├── services/             # Logika bisnis (market simulation, news scraping, ML training)
│   ├── database.py           # Manajemen basis data simulasi
│   └── sentix_adapter.py     # Router adapter API untuk kecocokan state UI
├── src/                      # Source code Frontend React
│   ├── components/           # Komponen modular UI (CryptoTicker, CandleChart, AIBotPanel, dll)
│   ├── App.tsx               # Aplikasi utama & penataan tata letak
│   └── main.tsx              # Titik masuk React
├── package.json              # Konfigurasi dependensi Node.js
└── vite.config.ts            # Konfigurasi proxy server Vite
```
