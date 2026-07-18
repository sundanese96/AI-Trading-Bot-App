import React, { useState } from "react";
import { Sliders, Activity, SlidersHorizontal, Cpu, Terminal, ShieldAlert, Save } from "lucide-react";
import { AiBotSettings, PRESETS, getPresetName } from "./types";
import { apiBot } from "../../api/client";

interface Props {
  settings: AiBotSettings;
  setSettings: React.Dispatch<React.SetStateAction<AiBotSettings>>;
}

export function BotSettingsForm({ settings, setSettings }: Props) {
  const [isSaving, setIsSaving] = useState(false);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await apiBot.saveSettings(settings);
      alert("Pengaturan strategi & parameter risiko berhasil disimpan dan diterapkan pada Engine AI.");
    } catch (e: any) {
      alert(e.message || "Gagal menyimpan konfigurasi.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl">
      <h3 className="font-sans font-bold text-base text-white mb-6 flex items-center gap-2 border-b border-slate-800 pb-3">
        <Sliders className="h-5 w-5 text-indigo-400" />
        Parameter Konfigurasi Profit & Risiko
      </h3>

      <form onSubmit={handleSaveSettings} className="space-y-6 text-xs text-slate-300">
        {/* Preset Configuration Selector */}
        <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-850/80 space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-mono text-slate-200 font-bold flex items-center gap-1.5">
              <Sliders className="h-4 w-4 text-indigo-400" />
              PRESET OTOMATIS STRATEGI & RISIKO
            </span>
            <span className="text-[10px] text-slate-500 font-mono">Pilih preset untuk konfigurasi cepat</span>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
            {[
              { id: "safe", label: "🛡️ Safe Preset", desc: "Aman, Leverage rendah, Konfirmasi tinggi" },
              { id: "medium", label: "⚖️ Medium Preset", desc: "Seimbang, Risiko moderat, Profit stabil" },
              { id: "high_risk", label: "🔥 High Risk Preset", desc: "Agresif, Leverage tinggi, Target besar" },
              { id: "custom", label: "⚙️ Custom Settings", desc: "Sesuaikan parameter secara manual", disabled: true }
            ].map((p) => {
              const activePreset = getPresetName(settings);
              const isSelected = activePreset === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => {
                    if (p.id !== "custom") {
                      const presetData = PRESETS[p.id as keyof typeof PRESETS];
                      setSettings((prev) => ({
                        ...prev,
                        ...presetData
                      }));
                    }
                  }}
                  disabled={p.disabled && !isSelected}
                  className={`text-left p-3 rounded-xl border transition-all flex flex-col justify-between ${
                    isSelected
                      ? "bg-indigo-500/10 border-indigo-500 text-white shadow-lg shadow-indigo-500/5"
                      : p.disabled
                      ? "bg-slate-900/30 border-slate-850/40 text-slate-500 cursor-not-allowed"
                      : "bg-slate-950 border-slate-850 text-slate-400 hover:text-slate-200 hover:border-slate-700 cursor-pointer"
                  }`}
                >
                  <span className="font-sans font-bold text-xs">{p.label}</span>
                  <span className="text-[9px] text-slate-500 mt-1 leading-tight">{p.desc}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Target & Model Binding Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-slate-400 font-mono">KOIN TARGET AKTIF</label>
            <select
              value={settings.symbol}
              onChange={(e) => setSettings((prev) => ({ ...prev, symbol: e.target.value }))}
              className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono font-bold text-white"
            >
              {["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SUIUSDT", "DOGEUSDT"].map((c) => (
                <option key={c} value={c}>{c.replace("USDT", "")} / USDT</option>
              ))}
            </select>
            <p className="text-[10px] text-slate-500">Mata uang kripto yang akan diperdagangkan otonom.</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-400 font-mono">STRATEGI TRADING</label>
            <select
              value={settings.strategy}
              onChange={(e) => setSettings((prev) => ({ ...prev, strategy: e.target.value as any }))}
              className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-sans font-bold text-white text-xs"
            >
              <option value="CONSERVATIVE">🛡️ CONSERVATIVE (Hati-Hati | Veto Gate: Aktif)</option>
              <option value="SCALPING">⚡ SCALPING (Cepat | Veto Gate: BYPASS)</option>
              <option value="SWING">📈 SWING (Tren Jangka Panjang | Veto Gate: Aktif)</option>
              <option value="AGGRESSIVE">🔥 AGGRESSIVE (Agresif & Sensitif | Veto Gate: BYPASS)</option>
              <option value="MARTINGALE">🔄 MARTINGALE (Averaging Down | Veto Gate: Aktif)</option>
              <option value="HEDGING">🔒 HEDGING (Posisi Dua Arah | Veto Gate: BYPASS)</option>
            </select>
            <p className="text-[10px] text-slate-500">Menentukan regulasi manajemen risiko otomatis sistem.</p>
          </div>
        </div>

        {/* ML Model Configuration */}
        <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-850 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-850 pb-2">
            <span className="font-mono text-slate-200 font-bold flex items-center gap-1.5">
              <Activity className="h-4 w-4 text-emerald-400" />
              PENGATURAN MODEL ML (MACHINE LEARNING)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-slate-400 font-mono text-[10px]">TARGET MODEL AKTIF</label>
              <select
                value={settings.modelType}
                onChange={(e) => setSettings((prev) => ({ ...prev, modelType: e.target.value }))}
                className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-3 py-2.5 outline-none font-sans font-bold text-white text-sm"
              >
                <option value="xgboost">XGBoost (Rekomendasi Utama)</option>
                <option value="lightgbm">LightGBM (Cepat & Ringan)</option>
                <option value="catboost">CatBoost (Akurasi Tinggi GPU)</option>
              </select>
              <p className="text-[9px] text-slate-500 mt-1">Pilih mesin kecerdasan buatan utama.</p>
            </div>

            <div className="space-y-1.5">
              <label className="text-slate-400 font-mono text-[10px]">TIMEFRAME ANALISIS</label>
              <select
                value={settings.timeframeMinutes}
                onChange={(e) => setSettings((prev) => ({ ...prev, timeframeMinutes: Number(e.target.value) }))}
                className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-3 py-2.5 outline-none font-sans font-bold text-white text-sm"
              >
                <option value={5}>5 Menit (Scalping Agresif)</option>
                <option value={15}>15 Menit (Day Trading Standar)</option>
                <option value={60}>60 Menit (Swing Jangka Panjang)</option>
              </select>
              <p className="text-[9px] text-slate-500 mt-1">Resolusi waktu data candle yang diproses.</p>
            </div>
          </div>
        </div>

        {/* Collaborative Weight Sliders */}
        <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-850 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-850 pb-2">
            <span className="font-mono text-slate-200 font-bold flex items-center gap-1.5">
              <SlidersHorizontal className="h-4 w-4 text-indigo-400" />
              BOBOT PENGAMBILAN KEPUTUSAN
            </span>
            <span className="font-mono text-[10px] text-slate-500">Total: 100%</span>
          </div>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-400 font-mono flex items-center gap-1"><Cpu className="h-3 w-3" /> ANALISIS SENTIMEN LLM (GEMINI)</span>
                <span className="font-bold text-white">{Math.round(settings.llmWeight * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.llmWeight}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  setSettings((prev) => ({
                    ...prev,
                    llmWeight: val,
                    mlWeight: parseFloat((1 - val).toFixed(2))
                  }));
                }}
                className="w-full h-1.5 bg-slate-900 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-400 font-mono flex items-center gap-1"><Terminal className="h-3 w-3" /> PREDIKSI MODEL ML (PYTHON/JS)</span>
                <span className="font-bold text-white">{Math.round(settings.mlWeight * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.mlWeight}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  setSettings((prev) => ({
                    ...prev,
                    mlWeight: val,
                    llmWeight: parseFloat((1 - val).toFixed(2))
                  }));
                }}
                className="w-full h-1.5 bg-slate-900 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* Leverage, Confidence, and Interval Settings */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <label className="text-slate-400 font-mono">BATAS MINIMAL KEYAKINAN (%)</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="100"
                value={settings.minConfidence}
                onChange={(e) => setSettings((prev) => ({ ...prev, minConfidence: parseInt(e.target.value) || 65 }))}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
              />
              <span className="text-slate-500 font-mono">%</span>
            </div>
            <p className="text-[10px] text-slate-500">Robot hanya akan membuka posisi jika nilai keyakinan di atas batas ini.</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-400 font-mono">LEVERAGE (DAYA UNGKIT)</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="125"
                value={settings.leverage}
                onChange={(e) => setSettings((prev) => ({ ...prev, leverage: parseInt(e.target.value) || 10 }))}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
              />
              <span className="text-slate-400 font-mono">x</span>
            </div>
            <p className="text-[10px] text-slate-500">Pengali margin untuk meningkatkan daya beli transaksi (maks 125x).</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-400 font-mono">INTERVAL DETIK EVALUASI</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="10"
                max="3600"
                value={settings.runIntervalSeconds || 10}
                onChange={(e) => setSettings((prev) => ({ ...prev, runIntervalSeconds: parseInt(e.target.value) || 10 }))}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
              />
              <span className="text-slate-400 font-mono">s</span>
            </div>
            <p className="text-[10px] text-slate-500">Membatasi seberapa sering robot memicu panggilan model AI/LLM.</p>
          </div>
        </div>

        {/* Risk Shield Parameters */}
        <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-850 space-y-4">
          <span className="font-mono text-slate-200 font-bold flex items-center gap-1.5 border-b border-slate-850 pb-2">
            <ShieldAlert className="h-4 w-4 text-rose-400" />
            SHIELD PROTEKSI OTOMATIS (MANAJEMEN PROFIT & RESIKO)
          </span>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-slate-400 font-mono">TAKE PROFIT (%)</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  step="0.1"
                  min="0.5"
                  value={settings.takeProfitPct}
                  onChange={(e) => setSettings((prev) => ({ ...prev, takeProfitPct: parseFloat(e.target.value) || 3.0 }))}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
                />
                <span className="text-slate-500 font-mono">%</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-slate-400 font-mono">STOP LOSS (%)</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  step="0.1"
                  min="0.2"
                  value={settings.stopLossPct}
                  onChange={(e) => setSettings((prev) => ({ ...prev, stopLossPct: parseFloat(e.target.value) || 1.5 }))}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
                />
                <span className="text-slate-500 font-mono">%</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-slate-400 font-mono">TRAILING STOP (%)</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={settings.trailingStopPct}
                  onChange={(e) => setSettings((prev) => ({ ...prev, trailingStopPct: parseFloat(e.target.value) || 0.5 }))}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
                />
                <span className="text-slate-500 font-mono">%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Strategic Advanced Parameter Settings */}
        <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-850 space-y-4">
          <span className="font-mono text-slate-200 font-bold flex items-center gap-1.5 border-b border-slate-850 pb-2">
            <SlidersHorizontal className="h-4 w-4 text-indigo-400" />
            PARAMETER STRATEGI TAMBAHAN (LANJUTAN)
          </span>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Sentiment Threshold */}
            <div className="space-y-1.5">
              <label className="text-slate-400 font-mono">AMBANG BATAS SENTIMEN (NEWS)</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0.0"
                  max="0.8"
                  step="0.05"
                  value={settings.sentimentThreshold ?? 0.15}
                  onChange={(e) => setSettings((prev) => ({ ...prev, sentimentThreshold: parseFloat(e.target.value) }))}
                  className="w-full h-1.5 bg-slate-900 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
                <span className="text-white font-mono font-bold shrink-0">{(settings.sentimentThreshold ?? 0.15).toFixed(2)}</span>
              </div>
              <p className="text-[10px] text-slate-500">
                Abaikan sentimen berita global jika skor absolutnya berada di bawah nilai batas ini.
              </p>
            </div>

            {/* Risk Level Selector */}
            <div className="space-y-1.5">
              <label className="text-slate-400 font-mono">LEVEL RISIKO SISTEM</label>
              <select
                value={settings.riskLevel ?? "MEDIUM"}
                onChange={(e) => setSettings((prev) => ({ ...prev, riskLevel: e.target.value as any }))}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 outline-none font-sans font-bold text-white text-xs"
              >
                <option value="LOW">🟢 LOW RISK (Leverage Kecil & SL Sangat Ketat)</option>
                <option value="MEDIUM">🟡 MEDIUM RISK (Imbang Antara Profit & Proteksi)</option>
                <option value="HIGH">🔴 HIGH RISK (Leverage Tinggi & Target Lebar)</option>
              </select>
              <p className="text-[10px] text-slate-500">
                Membatasi leverage dan stop-loss otomatis secara global saat eksekusi posisi.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-t border-slate-850/50 pt-3">
            {/* Take Profit Multiplier */}
            <div className="space-y-1.5">
              <label className="text-slate-400 font-mono">PENGALI (MULTIPLIER) TAKE PROFIT</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  step="0.1"
                  min="0.5"
                  max="5.0"
                  value={settings.tpMultiplier ?? 1.0}
                  onChange={(e) => setSettings((prev) => ({ ...prev, tpMultiplier: parseFloat(e.target.value) || 1.0 }))}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 outline-none font-mono text-white"
                />
                <span className="text-slate-500 font-mono">x</span>
              </div>
              <p className="text-[10px] text-slate-500">
                Faktor pengali pengukur target persentase Take Profit bawaan strategi.
              </p>
            </div>

            {/* Stop Loss Multiplier */}
            <div className="space-y-1.5">
              <label className="text-slate-400 font-mono">PENGALI (MULTIPLIER) STOP LOSS</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  step="0.1"
                  min="0.2"
                  max="3.0"
                  value={settings.slMultiplier ?? 1.0}
                  onChange={(e) => setSettings((prev) => ({ ...prev, slMultiplier: parseFloat(e.target.value) || 1.0 }))}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 outline-none font-mono text-white"
                />
                <span className="text-slate-500 font-mono">x</span>
              </div>
              <p className="text-[10px] text-slate-500">
                Faktor pengali pengukur toleransi risiko persentase Stop Loss bawaan strategi.
              </p>
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={isSaving}
          className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 px-4 rounded-xl flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50 transition cursor-pointer font-sans shadow-lg shadow-indigo-600/10"
        >
          <Save className="h-4.5 w-4.5" />
          {isSaving ? "Menyimpan Konfigurasi AI..." : "Terapkan & Simpan Parameter (Deploy)"}
        </button>
      </form>
    </div>
  );
}
