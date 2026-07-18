import React, { useState, useEffect } from "react";
import { NotificationSettings } from "../../types";
import { Bell, Send, Mail, ShieldCheck, Save } from "lucide-react";

interface Props {
  initialSettings: NotificationSettings;
  onSave: (settings: NotificationSettings) => Promise<boolean>;
  onTest: () => Promise<boolean>;
}

export function NotificationConfig({ initialSettings, onSave, onTest }: Props) {
  const [telegramToken, setTelegramToken] = useState(initialSettings.telegramToken || "");
  const [telegramChatId, setTelegramChatId] = useState(initialSettings.telegramChatId || "");
  const [emailAddress, setEmailAddress] = useState(initialSettings.emailAddress || "");
  const [tradeExecuted, setTradeExecuted] = useState(initialSettings.tradeExecuted);
  const [riskTriggered, setRiskTriggered] = useState(initialSettings.riskTriggered);
  const [highSentimentAlert, setHighSentimentAlert] = useState(initialSettings.highSentimentAlert);

  useEffect(() => {
    setTelegramToken(initialSettings.telegramToken || "");
    setTelegramChatId(initialSettings.telegramChatId || "");
    setEmailAddress(initialSettings.emailAddress || "");
    setTradeExecuted(initialSettings.tradeExecuted);
    setRiskTriggered(initialSettings.riskTriggered);
    setHighSentimentAlert(initialSettings.highSentimentAlert);
  }, [initialSettings]);

  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [statusMessage, setStatusMessage] = useState({ text: "", isError: false });

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setStatusMessage({ text: "", isError: false });
    try {
      const payload = {
        telegramToken,
        telegramChatId,
        emailAddress,
        tradeExecuted,
        riskTriggered,
        highSentimentAlert,
      };
      const success = await onSave(payload);
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

  const handleTest = async () => {
    setIsTesting(true);
    setStatusMessage({ text: "", isError: false });
    try {
      const success = await onTest();
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

  return (
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
            onClick={handleTest}
            disabled={isTesting}
            className="bg-slate-850 hover:bg-slate-800 text-slate-300 font-bold py-3 px-5 rounded-xl border border-slate-750 flex items-center justify-center gap-1.5 active:scale-95 disabled:opacity-50 transition cursor-pointer font-sans"
          >
            <Send className="h-4 w-4" />
            {isTesting ? "Menguji..." : "Kirim Alarm Tes"}
          </button>
        </div>
      </form>
    </div>
  );
}
