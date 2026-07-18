import React, { useState, useEffect } from "react";
import { LlmSettings } from "../../types";
import { Cpu, Globe, Key, Save } from "lucide-react";

interface Props {
  initialSettings: LlmSettings;
  onSave: (settings: LlmSettings) => Promise<boolean>;
}

export function LlmConfig({ initialSettings, onSave }: Props) {
  const [provider, setProvider] = useState<LlmSettings["provider"]>(initialSettings.provider || "simulated");
  const [apiKey, setApiKey] = useState(initialSettings.apiKey || "");
  const [baseUrl, setBaseUrl] = useState(initialSettings.baseUrl || "");
  const [modelName, setModelName] = useState(initialSettings.modelName || "");
  
  useEffect(() => {
    setProvider(initialSettings.provider || "simulated");
    setApiKey(initialSettings.apiKey || "");
    setBaseUrl(initialSettings.baseUrl || "");
    setModelName(initialSettings.modelName || "");
  }, [initialSettings]);
  
  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState({ text: "", isError: false });

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setStatusMessage({ text: "", isError: false });
    try {
      const payload: LlmSettings = { provider, apiKey, baseUrl, modelName };
      const success = await onSave(payload);
      if (success) {
        setStatusMessage({ text: "Konfigurasi model LLM AI berhasil disimpan ke database.", isError: false });
      } else {
        setStatusMessage({ text: "Gagal menyimpan konfigurasi LLM.", isError: true });
      }
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Gagal menyimpan konfigurasi LLM.", isError: true });
    } finally {
      setIsSaving(false);
    }
  };

  return (
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

      <form onSubmit={handleSave} className="space-y-5 text-xs">
        <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/40 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                <option value="semburat">Semburat API Gateway (Sync & Async Polling)</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-slate-400 font-mono flex items-center gap-1">
                <Key className="h-3.5 w-3.5 text-amber-400" />
                API SECRET KEY
              </label>
              <input
                type="password"
                placeholder={
                  provider === "custom" || provider === "semburat"
                    ? "Opsional untuk model lokal / gateway..."
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
                    : provider === "semburat"
                    ? "Contoh: http://semburat.online"
                    : "Kosong (menggunakan default internal)..."
                }
                disabled={provider === "simulated"}
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-slate-200 outline-none font-mono disabled:opacity-40"
              />
            </div>
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
                    : provider === "semburat"
                    ? "claude-3-5-sonnet-20241022"
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
            className="flex-1 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold py-3 px-4 rounded-xl flex items-center justify-center gap-1.5 active:scale-95 disabled:opacity-50 transition cursor-pointer shadow-lg shadow-indigo-600/10 font-sans"
          >
            <Save className="h-4 w-4" />
            {isSaving ? "Menyimpan..." : "Simpan Konfigurasi LLM"}
          </button>
        </div>
      </form>
    </div>
  );
}
