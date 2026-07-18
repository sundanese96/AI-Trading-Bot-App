import React, { useState } from "react";
import { NotificationSettings, NotificationLog, LlmSettings } from "../../types";
import { ApiDocsModal } from "./ApiDocsModal";
import { NotificationConfig } from "./NotificationConfig";
import { LlmConfig } from "./LlmConfig";
import { BinanceConfig } from "./BinanceConfig";
import { NotificationLogTable } from "./NotificationLogTable";
import { HelpCircle, BookOpen } from "lucide-react";
import { apiConfig } from "../../api/client";

interface SettingsPanelProps {
  settings: NotificationSettings;
  logs: NotificationLog[];
  onSaveSettings: (settings: NotificationSettings) => Promise<boolean>;
  onTriggerTest: () => Promise<boolean>;
  llmSettings: LlmSettings;
  onSaveLlmSettings: (llmSettings: LlmSettings) => Promise<boolean>;
}

export function SettingsPanel({
  settings,
  logs,
  onSaveSettings,
  onTriggerTest,
  llmSettings,
  onSaveLlmSettings,
}: SettingsPanelProps) {
  const [isApiDocsOpen, setIsApiDocsOpen] = useState(false);
  
  // Wrap the API calls so components receive a Promise<boolean> and the main state is updated if we need it.
  const handleSaveSettings = async (payload: NotificationSettings) => {
    try {
      const res = await apiConfig.saveNotificationSettings(payload);
      if (res) onSaveSettings(payload); // update parent state
      return res;
    } catch {
      return false;
    }
  };

  const handleTestNotification = async () => {
    try {
      const res = await apiConfig.testNotification();
      if (res) onTriggerTest(); // refresh parent state if needed
      return res;
    } catch {
      return false;
    }
  };

  const handleSaveLlmSettings = async (payload: LlmSettings) => {
    try {
      const res = await apiConfig.saveLlmSettings(payload);
      if (res) onSaveLlmSettings(payload); // update parent state
      return res;
    } catch {
      return false;
    }
  };

  return (
    <div className="space-y-6">
      {/* Configuration Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Double-Panel Column */}
        <div className="lg:col-span-2 space-y-6">
          <NotificationConfig 
            initialSettings={settings}
            onSave={handleSaveSettings}
            onTest={handleTestNotification}
          />
          <LlmConfig 
            initialSettings={llmSettings}
            onSave={handleSaveLlmSettings}
          />
          <BinanceConfig />
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

          {/* Guide 2: Local LLM (Ollama) & 9Router */}
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl space-y-4">
            <h4 className="font-sans font-bold text-white text-base flex items-center gap-2">
              <HelpCircle className="h-4 w-4 text-indigo-400" />
              Panduan Model Lokal & 9Router
            </h4>
            <div className="space-y-3 text-xs text-slate-400 leading-relaxed">
              <p>
                Untuk menjalankan model LLM secara gratis di PC lokal menggunakan Ollama atau eksternal via 9Router Tunnel:
              </p>
              <div className="space-y-2 bg-slate-950/40 p-3 rounded-xl border border-slate-800/40 font-mono text-[10px]">
                <p className="text-white font-bold">Opsi A: Konfigurasi Ollama</p>
                <ol className="list-decimal list-inside space-y-1.5 text-slate-400">
                  <li>Unduh Ollama di <span className="text-indigo-400">ollama.com</span>.</li>
                  <li>Jalankan model di terminal:
                    <div className="bg-slate-950 text-indigo-300 p-1.5 rounded my-1 select-all">ollama run llama3</div>
                  </li>
                  <li>Pilih provider <span className="text-indigo-400">Custom Endpoint</span> di form kiri.</li>
                  <li>Isi Base URL: <span className="text-indigo-400">http://localhost:11434/v1</span></li>
                  <li>Isi Target Model: <span className="text-indigo-400">llama3</span></li>
                  <li>Kosongkan kolom API Secret Key.</li>
                </ol>
              </div>

              <div className="space-y-2 bg-slate-950/40 p-3 rounded-xl border border-slate-800/40 font-mono text-[10px]">
                <p className="text-white font-bold">Opsi B: Konfigurasi 9Router (Tunnel)</p>
                <ol className="list-decimal list-inside space-y-1.5 text-slate-400">
                  <li>Pilih provider <span className="text-indigo-400">Custom Endpoint</span> di form kiri.</li>
                  <li>Isi Base URL: <span className="text-indigo-400">https://rstxjf2.abc-tunnel.us/v1</span></li>
                  <li>Isi Target Model: <span className="text-indigo-400">ag/gemini-3-flash-agent</span></li>
                  <li>Isi API Secret Key: <span className="text-indigo-400">sk-1b1...9274</span></li>
                </ol>
              </div>
            </div>
          </div>

          {/* Guide 3: API Gateway (Semburat) */}
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl space-y-4 flex flex-col justify-between items-start">
            <div>
              <h4 className="font-sans font-bold text-white text-base flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-emerald-400" />
                Panduan Semburat API Gateway
              </h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Pelajari integrasi *middleware* cerdas untuk meneruskan LLM secara lokal (Sync) maupun menggunakan Cloudflare Timeout Bypass (Async).
              </p>
            </div>
            <button 
              onClick={() => setIsApiDocsOpen(true)}
              className="mt-4 flex items-center gap-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 px-4 py-2 rounded-lg font-bold transition-colors w-full justify-center text-sm"
            >
              <BookOpen className="w-4 h-4" />
              Buka Dokumentasi Lengkap
            </button>
          </div>

        </div>
      </div>

      <NotificationLogTable logs={logs} />
      
      <ApiDocsModal 
        isOpen={isApiDocsOpen} 
        onClose={() => setIsApiDocsOpen(false)} 
      />
    </div>
  );
}
