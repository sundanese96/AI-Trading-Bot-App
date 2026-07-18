import React, { useState, useEffect } from "react";
import { ShieldCheck, Save } from "lucide-react";
import { apiConfig } from "../../api/client";

export function BinanceConfig() {
  const [binanceApiKey, setBinanceApiKey] = useState("");
  const [binanceApiSecret, setBinanceApiSecret] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [maxDailyLoss, setMaxDailyLoss] = useState(5.0);
  const [maxTradesPerDay, setMaxTradesPerDay] = useState(5);
  
  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState({ text: "", isError: false });

  useEffect(() => {
    async function loadConfig() {
      try {
        const config = await apiConfig.getAIConfig();
        if (config) {
          setBinanceApiKey(config.binanceApiKey || "");
          setBinanceApiSecret(config.binanceApiSecret || "");
          setDryRun(config.dryRun !== false); // default true
          setMaxDailyLoss(config.maxDailyLoss || 5.0);
          setMaxTradesPerDay(config.maxTradesPerDay || 5);
        }
      } catch (e) {
        console.error("Gagal memuat konfigurasi Binance:", e);
      }
    }
    loadConfig();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setStatusMessage({ text: "", isError: false });
    try {
      await apiConfig.saveBinanceConfig({
        binanceApiKey,
        binanceApiSecret,
        dryRun,
        maxDailyLoss,
        maxTradesPerDay,
      });
      setStatusMessage({ text: "Koneksi broker & parameter risiko Binance berhasil disimpan ke database.", isError: false });
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Gagal menyimpan konfigurasi Binance.", isError: true });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
            <ShieldCheck className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <h3 className="font-sans font-bold text-lg text-white">Koneksi Broker & Parameter Risiko (Binance)</h3>
            <p className="text-xs text-slate-500 font-mono">Hubungkan API Key Binance Futures untuk live trading dan atur limit risiko harian.</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-5 text-xs">
        <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/40 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-slate-400 font-mono">BINANCE API KEY</label>
              <input
                type="password"
                placeholder="Masukkan API Key Binance..."
                value={binanceApiKey}
                onChange={(e) => setBinanceApiKey(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-400 font-mono">BINANCE API SECRET</label>
              <input
                type="password"
                placeholder="Masukkan API Secret Binance..."
                value={binanceApiSecret}
                onChange={(e) => setBinanceApiSecret(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono"
              />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-slate-400 font-mono">MODE EKSEKUSI</label>
              <select
                value={dryRun ? "true" : "false"}
                onChange={(e) => setDryRun(e.target.value === "true")}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono"
              >
                <option value="true">Simulation / Paper Trading</option>
                <option value="false">Live Binance Futures Account</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-slate-400 font-mono">BATAS RUGI HARIAN ($)</label>
              <input
                type="number"
                step="0.01"
                value={maxDailyLoss}
                onChange={(e) => setMaxDailyLoss(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-400 font-mono">MAX TRADES PER HARI</label>
              <input
                type="number"
                value={maxTradesPerDay}
                onChange={(e) => setMaxTradesPerDay(parseInt(e.target.value) || 0)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono"
              />
            </div>
          </div>
        </div>

        {statusMessage.text && (
          <div className={`p-3.5 rounded-xl text-xs font-sans border leading-relaxed ${
            statusMessage.isError
              ? "bg-red-950/20 border-red-900/30 text-red-400"
              : "bg-emerald-950/20 border-emerald-900/30 text-emerald-400"
          }`}>
            {statusMessage.text}
          </div>
        )}

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={isSaving}
            className="flex-1 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold py-3 px-4 rounded-xl flex items-center justify-center gap-1.5 active:scale-95 disabled:opacity-50 transition cursor-pointer shadow-lg shadow-amber-600/10 font-sans"
          >
            <Save className="h-4 w-4" />
            {isSaving ? "Menyimpan..." : "Simpan Koneksi Broker"}
          </button>
        </div>
      </form>
    </div>
  );
}
