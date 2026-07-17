import React, { useState } from "react";
import { NotificationSettings, NotificationLog, LlmSettings } from "../types";
import { Send, Bell, Save, ShieldCheck, Mail, CheckCircle, AlertTriangle, Cpu, Globe, Key, HelpCircle } from "lucide-react";

interface SettingsPanelProps {
  settings: NotificationSettings;
  logs: NotificationLog[];
  onSaveSettings: (settings: NotificationSettings) => Promise<boolean>;
  onTriggerTest: () => Promise<boolean>;
  llmSettings: LlmSettings;
  onSaveLlmSettings: (llmSettings: LlmSettings) => Promise<boolean>;
}

export function SettingsPanel({
  settings: initialSettings,
  logs,
  onSaveSettings,
  onTriggerTest,
  llmSettings,
  onSaveLlmSettings,
}: SettingsPanelProps) {
  // Notification Channel States
  const [telegramToken, setTelegramToken] = useState(initialSettings.telegramToken || "");
  const [telegramChatId, setTelegramChatId] = useState(initialSettings.telegramChatId || "");
  const [emailAddress, setEmailAddress] = useState(initialSettings.emailAddress || "");

  const [tradeExecuted, setTradeExecuted] = useState(initialSettings.tradeExecuted);
  const [riskTriggered, setRiskTriggered] = useState(initialSettings.riskTriggered);
  const [highSentimentAlert, setHighSentimentAlert] = useState(initialSettings.highSentimentAlert);

  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [statusMessage, setStatusMessage] = useState({ text: "", isError: false });

  // LLM Config States
  const [provider, setProvider] = useState<LlmSettings["provider"]>(llmSettings.provider || "simulated");
  const [apiKey, setApiKey] = useState(llmSettings.apiKey || "");
  const [baseUrl, setBaseUrl] = useState(llmSettings.baseUrl || "");
  const [modelName, setModelName] = useState(llmSettings.modelName || "");
  const [isSavingLlm, setIsSavingLlm] = useState(false);
  const [llmStatusMessage, setLlmStatusMessage] = useState({ text: "", isError: false });

  // Binance & Risk Control States
  const [binanceApiKey, setBinanceApiKey] = useState("");
  const [binanceApiSecret, setBinanceApiSecret] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [maxDailyLoss, setMaxDailyLoss] = useState(5.0);
  const [maxTradesPerDay, setMaxTradesPerDay] = useState(5);
  const [isSavingBinance, setIsSavingBinance] = useState(false);
  const [binanceStatusMessage, setBinanceStatusMessage] = useState({ text: "", isError: false });

  // Fetch Binance & AI Config on mount
  React.useEffect(() => {
    async function loadBinanceConfig() {
      try {
        const res = await fetch("/api/ai/config");
        if (res.ok) {
          const config = await res.json();
          if (config) {
            setBinanceApiKey(config.binanceApiKey || "");
            setBinanceApiSecret(config.binanceApiSecret || "");
            setDryRun(config.dryRun !== false); // default to true
            setMaxDailyLoss(config.maxDailyLoss || 5.0);
            setMaxTradesPerDay(config.maxTradesPerDay || 5);
          }
        }
      } catch (e) {
        console.error("Gagal memuat konfigurasi Binance:", e);
      }
    }
    loadBinanceConfig();
  }, []);

  // Save Notifications
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setStatusMessage({ text: "", isError: false });

    try {
      const payload: NotificationSettings = {
        telegramToken,
        telegramChatId,
        emailAddress,
        tradeExecuted,
        riskTriggered,
        highSentimentAlert,
      };
      const success = await onSaveSettings(payload);
      if (success) {
        setStatusMessage({ text: "Pengaturan notifikasi berhasil disimpan ke database.", isError: false });
      } else {
        setStatusMessage({ text: "Gagal menyimpan pengaturan.", isError: true });
      }
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Gagal menyimpan pengaturan.", isError: true });
    } finally {
      setIsSaving(false);
    }
  };

  // Test Notifications
  const handleTestNotification = async () => {
    setIsTesting(true);
    setStatusMessage({ text: "", isError: false });
    try {
      const success = await onTriggerTest();
      if (success) {
        setStatusMessage({ text: "Peringatan tes berhasil dipicu! Silakan periksa log aktivitas di bawah.", isError: false });
      } else {
        setStatusMessage({ text: "Tes gagal. Pastikan konfigurasi valid.", isError: true });
      }
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Gagal mengirim tes.", isError: true });
    } finally {
      setIsTesting(false);
    }
  };

  // Save LLM Config
  const handleSaveLlmConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingLlm(true);
    setLlmStatusMessage({ text: "", isError: false });

    try {
      const payload: LlmSettings = {
        provider,
        apiKey,
        baseUrl,
        modelName,
      };
      const success = await onSaveLlmSettings(payload);
      if (success) {
        setLlmStatusMessage({ text: "Konfigurasi model LLM AI berhasil disimpan ke database.", isError: false });
      } else {
        setLlmStatusMessage({ text: "Gagal menyimpan konfigurasi LLM.", isError: true });
      }
    } catch (err: any) {
      setLlmStatusMessage({ text: err.message || "Gagal menyimpan konfigurasi LLM.", isError: true });
    } finally {
      setIsSavingLlm(false);
    }
  };

  // Save Binance Config
  const handleSaveBinanceConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingBinance(true);
    setBinanceStatusMessage({ text: "", isError: false });

    try {
      const response = await fetch("/api/ai/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider,
          customUrl: baseUrl,
          customKey: apiKey,
          customModel: modelName,
          binanceApiKey,
          binanceApiSecret,
          dryRun,
          maxDailyLoss,
          maxTradesPerDay,
        }),
      });

      const resData = await response.json();
      if (response.ok) {
        setBinanceStatusMessage({ text: "Koneksi broker & parameter risiko Binance berhasil disimpan ke database.", isError: false });
      } else {
        setBinanceStatusMessage({ text: resData.message || "Gagal menyimpan konfigurasi Binance.", isError: true });
      }
    } catch (err: any) {
      setBinanceStatusMessage({ text: err.message || "Gagal menyimpan konfigurasi Binance.", isError: true });
    } finally {
      setIsSavingBinance(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Configuration Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Double-Panel Column */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Card 1: Notification Settings */}
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-slate-800 rounded-lg border border-slate-750">
                  <Bell className="h-5 w-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-sans font-bold text-lg text-white">Saluran Notifikasi Otomatis</h3>
                  <p className="text-xs text-slate-500 font-mono">Hubungkan Telegram Bot API & alamat email untuk notifikasi peristiwa instan.</p>
                </div>
              </div>
            </div>

            <form onSubmit={handleSave} className="space-y-5 text-xs">
              {/* Telegram Config */}
              <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/40 space-y-3.5">
                <div className="flex items-center gap-1.5 text-slate-300 font-bold font-mono text-[11px] border-b border-slate-800 pb-2">
                  <Send className="h-4 w-4 text-sky-400" />
                  SALURAN TELEGRAM BOT API
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-slate-400 font-mono">TELEGRAM BOT TOKEN</label>
                    <input
                      type="password"
                      placeholder="Contoh: 123456:ABC-DEF..."
                      value={telegramToken}
                      onChange={(e) => setTelegramToken(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-slate-400 font-mono">TELEGRAM CHAT ID</label>
                    <input
                      type="text"
                      placeholder="Contoh: -10012345678"
                      value={telegramChatId}
                      onChange={(e) => setTelegramChatId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono"
                    />
                  </div>
                </div>
                <p className="text-[10px] text-slate-500 leading-relaxed font-mono">
                  * Catatan: Jika token dikosongkan, server akan otomatis mengalihkan notifikasi ke mode simulasi (Logged local).
                </p>
              </div>

              {/* Email Config */}
              <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/40 space-y-3.5">
                <div className="flex items-center gap-1.5 text-slate-300 font-bold font-mono text-[11px] border-b border-slate-800 pb-2">
                  <Mail className="h-4 w-4 text-emerald-400" />
                  SALURAN NOTIFIKASI EMAIL
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 font-mono">ALAMAT EMAIL PENERIMA</label>
                  <input
                    type="email"
                    placeholder="Contoh: investor@perusahaan.com"
                    value={emailAddress}
                    onChange={(e) => setEmailAddress(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono"
                  />
                </div>
              </div>

              {/* Alerts Checklist */}
              <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/40 space-y-3">
                <div className="text-slate-300 font-bold font-mono text-[11px] border-b border-slate-800 pb-2 flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-indigo-400" />
                  PERISTIWA PEMICU ALARM (ALERTS EVENT)
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <label className="flex items-center gap-2.5 bg-slate-950 border border-slate-850 p-3 rounded-xl cursor-pointer hover:border-slate-800 select-none">
                    <input
                      type="checkbox"
                      checked={tradeExecuted}
                      onChange={(e) => setTradeExecuted(e.target.checked)}
                      className="h-4 w-4 rounded accent-indigo-600"
                    />
                    <div>
                      <p className="font-sans font-bold text-slate-200 text-xs">Transaksi Sukses</p>
                      <p className="text-[9px] text-slate-500 font-mono">Saat order tereksekusi</p>
                    </div>
                  </label>

                  <label className="flex items-center gap-2.5 bg-slate-950 border border-slate-850 p-3 rounded-xl cursor-pointer hover:border-slate-800 select-none">
                    <input
                      type="checkbox"
                      checked={riskTriggered}
                      onChange={(e) => setRiskTriggered(e.target.checked)}
                      className="h-4 w-4 rounded accent-indigo-600"
                    />
                    <div>
                      <p className="font-sans font-bold text-slate-200 text-xs">Pemicu Proteksi SL/TP</p>
                      <p className="text-[9px] text-slate-500 font-mono">Manajemen risiko otomatis</p>
                    </div>
                  </label>

                  <label className="flex items-center gap-2.5 bg-slate-950 border border-slate-850 p-3 rounded-xl cursor-pointer hover:border-slate-800 select-none">
                    <input
                      type="checkbox"
                      checked={highSentimentAlert}
                      onChange={(e) => setHighSentimentAlert(e.target.checked)}
                      className="h-4 w-4 rounded accent-indigo-600"
                    />
                    <div>
                      <p className="font-sans font-bold text-slate-200 text-xs">Sentimen Ekstrim</p>
                      <p className="text-[9px] text-slate-500 font-mono">Berita volatilitas tinggi</p>
                    </div>
                  </label>
                </div>
              </div>

              {/* Status messages */}
              {statusMessage.text && (
                <div className={`p-3.5 rounded-xl text-xs font-sans border leading-relaxed ${
                  statusMessage.isError
                    ? "bg-red-950/20 border-red-900/30 text-red-400"
                    : "bg-emerald-950/20 border-emerald-900/30 text-emerald-400"
                }`}>
                  {statusMessage.text}
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-4">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 px-4 rounded-xl flex items-center justify-center gap-1.5 active:scale-95 disabled:opacity-50 transition cursor-pointer shadow-lg shadow-indigo-600/10 font-sans"
                >
                  <Save className="h-4 w-4" />
                  {isSaving ? "Menyimpan..." : "Simpan Pengaturan Notifikasi"}
                </button>

                <button
                  type="button"
                  onClick={handleTestNotification}
                  disabled={isTesting}
                  className="bg-slate-850 hover:bg-slate-800 text-slate-300 font-bold py-3 px-5 rounded-xl border border-slate-750 flex items-center justify-center gap-1.5 active:scale-95 disabled:opacity-50 transition cursor-pointer font-sans"
                >
                  <Send className="h-4 w-4" />
                  {isTesting ? "Menguji..." : "Kirim Alarm Tes"}
                </button>
              </div>
            </form>
          </div>

          {/* Card 2: Multi-Provider LLM Configuration */}
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                  <Cpu className="h-5 w-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-sans font-bold text-lg text-white">Integrasi Model LLM (Kecerdasan Buatan)</h3>
                  <p className="text-xs text-slate-500 font-mono">Ganti Gemini dengan API Key OpenAI, DeepSeek, Anthropic, atau model lokal (Ollama / Llama.cpp).</p>
                </div>
              </div>
            </div>

            <form onSubmit={handleSaveLlmConfig} className="space-y-5 text-xs">
              <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/40 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* LLM Provider Selector */}
                  <div className="space-y-1">
                    <label className="text-slate-400 font-mono flex items-center gap-1">
                      <Globe className="h-3.5 w-3.5 text-indigo-400" />
                      PENYEDIA API (PROVIDER)
                    </label>
                    <select
                      value={provider}
                      onChange={(e) => setProvider(e.target.value as LlmSettings["provider"])}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono"
                    >
                      <option value="simulated">Simulation / Offline Default</option>
                      <option value="openai">OpenAI (GPT Models)</option>
                      <option value="deepseek">DeepSeek AI (V3 / R1)</option>
                      <option value="anthropic">Anthropic (Claude Models)</option>
                      <option value="custom">Custom Endpoint (Ollama / Llama.cpp / Local PC)</option>
                    </select>
                  </div>

                  {/* Secret API key */}
                  <div className="space-y-1">
                    <label className="text-slate-400 font-mono flex items-center gap-1">
                      <Key className="h-3.5 w-3.5 text-amber-400" />
                      API SECRET KEY
                    </label>
                    <input
                      type="password"
                      placeholder={
                        provider === "custom"
                          ? "Opsional untuk model lokal..."
                          : provider === "simulated"
                          ? "Tidak diperlukan untuk mode simulasi..."
                          : "Masukkan API Key anda (sk-...)"
                      }
                      disabled={provider === "simulated"}
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono disabled:opacity-40"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Custom Base URL */}
                  <div className="space-y-1">
                    <label className="text-slate-400 font-mono">CUSTOM BASE URL</label>
                    <input
                      type="text"
                      placeholder={
                        provider === "openai"
                          ? "https://api.openai.com/v1"
                          : provider === "deepseek"
                          ? "https://api.deepseek.com"
                          : provider === "anthropic"
                          ? "https://api.anthropic.com"
                          : provider === "custom"
                          ? "Contoh: http://localhost:11434/v1"
                          : "Kosong (menggunakan default internal)..."
                      }
                      disabled={provider === "simulated"}
                      value={baseUrl}
                      onChange={(e) => setBaseUrl(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono disabled:opacity-40"
                    />
                  </div>

                  {/* Custom Model Name */}
                  <div className="space-y-1">
                    <label className="text-slate-400 font-mono">NAMA TARGET MODEL</label>
                    <input
                      type="text"
                      placeholder={
                        provider === "openai"
                          ? "gpt-4o-mini"
                          : provider === "deepseek"
                          ? "deepseek-chat"
                          : provider === "anthropic"
                          ? "claude-3-5-haiku-latest"
                          : provider === "custom"
                          ? "llama3"
                          : "Simulation Engine"
                      }
                      disabled={provider === "simulated"}
                      value={modelName}
                      onChange={(e) => setModelName(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono disabled:opacity-40"
                    />
                  </div>
                </div>

                <p className="text-[10px] text-slate-500 leading-relaxed font-mono">
                  💡 * Tip: Jika koneksi server gagal (e.g. PC mati atau kuota habis), sistem akan otomatis mengaktifkan mode simulasi cerdas sehingga proses trading dan analisis berita tetap berjalan lancar tanpa mengalami crash!
                </p>
              </div>

              {/* Status messages */}
              {llmStatusMessage.text && (
                <div className={`p-3.5 rounded-xl text-xs font-sans border leading-relaxed ${
                  llmStatusMessage.isError
                    ? "bg-red-950/20 border-red-900/30 text-red-400"
                    : "bg-emerald-950/20 border-emerald-900/30 text-emerald-400"
                }`}>
                  {llmStatusMessage.text}
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-4">
                <button
                  type="submit"
                  disabled={isSavingLlm}
                  className="flex-1 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold py-3 px-4 rounded-xl flex items-center justify-center gap-1.5 active:scale-95 disabled:opacity-50 transition cursor-pointer shadow-lg shadow-indigo-600/10 font-sans"
                >
                  <Save className="h-4 w-4" />
                  {isSavingLlm ? "Menyimpan..." : "Simpan Konfigurasi LLM"}
                </button>
              </div>
            </form>
          </div>

          {/* Card 3: Binance API & Risk Controls */}
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

            <form onSubmit={handleSaveBinanceConfig} className="space-y-5 text-xs">
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

              {binanceStatusMessage.text && (
                <div className={`p-3.5 rounded-xl text-xs font-sans border leading-relaxed ${
                  binanceStatusMessage.isError
                    ? "bg-red-950/20 border-red-900/30 text-red-400"
                    : "bg-emerald-950/20 border-emerald-900/30 text-emerald-400"
                }`}>
                  {binanceStatusMessage.text}
                </div>
              )}

              <div className="flex gap-4">
                <button
                  type="submit"
                  disabled={isSavingBinance}
                  className="flex-1 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold py-3 px-4 rounded-xl flex items-center justify-center gap-1.5 active:scale-95 disabled:opacity-50 transition cursor-pointer shadow-lg shadow-amber-600/10 font-sans"
                >
                  <Save className="h-4 w-4" />
                  {isSavingBinance ? "Menyimpan..." : "Simpan Koneksi Broker"}
                </button>
              </div>
            </form>
          </div>

        </div>

        {/* Right Info Guidelines */}
        <div className="space-y-6">
          
          {/* Guide 1: Telegram / Email */}
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl space-y-4">
            <h4 className="font-sans font-bold text-white text-base">Panduan Integrasi Bot</h4>
            <div className="space-y-3 text-xs text-slate-400 leading-relaxed">
              <p>
                Aplikasi trading simulasi ini terhubung dengan API Telegram untuk mengirim notifikasi PNL instan saat stop-loss atau take-profit terpicu.
              </p>
              <div className="space-y-2 bg-slate-950/40 p-3 rounded-xl border border-slate-800/40 font-mono text-[10px]">
                <p className="text-white font-bold">Langkah Pembuatan Bot:</p>
                <ol className="list-decimal list-inside space-y-1 text-slate-400">
                  <li>Cari <span className="text-indigo-400">@BotFather</span> di Telegram.</li>
                  <li>Ketik <span className="text-indigo-400">/newbot</span> untuk membuat bot baru.</li>
                  <li>Salin token HTTP API yang diberikan.</li>
                  <li>Cari <span className="text-indigo-400">@userinfobot</span> untuk mendapatkan Chat ID akun Anda.</li>
                  <li>Masukkan token & Chat ID di panel kiri.</li>
                </ol>
              </div>
            </div>
          </div>

          {/* Guide 2: Local LLM (Ollama) */}
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl space-y-4">
            <h4 className="font-sans font-bold text-white text-base flex items-center gap-2">
              <HelpCircle className="h-4 w-4 text-indigo-400" />
              Panduan Model Lokal
            </h4>
            <div className="space-y-3 text-xs text-slate-400 leading-relaxed">
              <p>
                Untuk menjalankan model LLM secara gratis di PC lokal menggunakan Ollama:
              </p>
              <div className="space-y-2 bg-slate-950/40 p-3 rounded-xl border border-slate-800/40 font-mono text-[10px]">
                <p className="text-white font-bold">Konfigurasi Ollama:</p>
                <ol className="list-decimal list-inside space-y-1.5 text-slate-400">
                  <li>Unduh Ollama di <span className="text-indigo-400">ollama.com</span>.</li>
                  <li>Buka terminal, jalankan model favorit:
                    <div className="bg-slate-950 text-indigo-300 p-1.5 rounded my-1 select-all">ollama run llama3</div>
                  </li>
                  <li>Pilih provider <span className="text-indigo-400">Custom Endpoint</span> di form kiri.</li>
                  <li>Isi Base URL: <span className="text-indigo-400">http://localhost:11434/v1</span></li>
                  <li>Isi Target Model: <span className="text-indigo-400">llama3</span></li>
                  <li>Kosongkan kolom API Secret Key.</li>
                </ol>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Logs Table Section */}
      <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/60 rounded-2xl p-6 shadow-2xl">
        <h4 className="font-sans font-bold text-white text-base mb-4">Log Pengiriman Aktivitas Notifikasi ({logs.length})</h4>
        {logs.length === 0 ? (
          <p className="text-xs text-slate-500 font-mono">Belum ada aktivitas pengiriman notifikasi dari server.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300 border-collapse">
              <thead>
                <tr className="border-b border-slate-800/80 text-slate-400 uppercase text-[10px] font-mono">
                  <th className="py-3 px-4">Waktu</th>
                  <th className="py-3 px-4">Saluran</th>
                  <th className="py-3 px-4">Penerima</th>
                  <th className="py-3 px-4">Ringkasan Pesan</th>
                  <th className="py-3 px-4">Status Dispatch</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/30 font-mono">
                {logs.map((log) => {
                  const isSuccess = log.status === "SUCCESS";
                  const isSimulated = log.status === "SIMULATED";
                  return (
                    <tr key={log.id} className="hover:bg-slate-800/20 transition">
                      <td className="py-3.5 px-4 text-slate-500">
                        {new Date(log.timestamp).toLocaleTimeString("id-ID")}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded font-bold text-[9px] ${
                          log.type === "TELEGRAM" ? "text-sky-400 bg-sky-500/10" : "text-emerald-400 bg-emerald-500/10"
                        }`}>
                          {log.type}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 max-w-[120px] truncate" title={log.recipient}>
                        {log.recipient}
                      </td>
                      <td className="py-3.5 px-4 max-w-sm truncate text-slate-400" title={log.message}>
                        {log.message}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 w-fit ${
                          isSuccess
                            ? "bg-emerald-500/10 text-emerald-400"
                            : isSimulated
                            ? "bg-slate-800 text-slate-400"
                            : "bg-red-500/10 text-red-400"
                        }`}>
                          {isSuccess && <CheckCircle className="h-3 w-3" />}
                          {!isSuccess && !isSimulated && <AlertTriangle className="h-3 w-3" />}
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
