import React, { useState } from "react";
import { Terminal, Bot, CheckCircle, Trash2, RefreshCw, X, ShieldAlert } from "lucide-react";
import { BotStatusData } from "./types";
import { apiBot } from "../../api/client";

interface Props {
  botStatus: BotStatusData;
  fetchBotSettings: () => void;
  setBotStatus: React.Dispatch<React.SetStateAction<BotStatusData>>;
  selectedTrade: any;
  setSelectedTrade: (trade: any) => void;
}

export function BotLogsTable({
  botStatus,
  fetchBotSettings,
  setBotStatus,
  selectedTrade,
  setSelectedTrade
}: Props) {
  const [confirmCloseId, setConfirmCloseId] = useState<string | null>(null);
  const [isClosingTrade, setIsClosingTrade] = useState(false);

  const handleClearLogs = async () => {
    try {
      const response = await fetch("/api/ai-bot/logs/clear", { method: "POST" });
      if (response.ok) {
        const data = await response.json();
        setBotStatus((prev) => ({ ...prev, logs: data.logs || [] }));
      } else {
        const errData = await response.json();
        alert("Gagal membersihkan log: " + errData.message || "Server error.");
      }
    } catch (e) {
      console.error("Gagal membersihkan log aktivitas bot:", e);
      alert("Network error. Cek koneksi.");
    }
  };

  const handleClosePosition = async (tradeId: string) => {
    setIsClosingTrade(true);
    try {
      const res = await fetch("/api/trade/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tradeId })
      });
      if (res.ok) {
        alert("Posisi berhasil ditutup manual.");
        setSelectedTrade(null);
        setConfirmCloseId(null);
        fetchBotSettings(); // Refresh status
      } else {
        const data = await res.json();
        alert("Gagal menutup posisi: " + (data.message || "Unknown error"));
      }
    } catch (e) {
      console.error("Error closing position:", e);
      alert("Network error saat menutup posisi.");
    } finally {
      setIsClosingTrade(false);
    }
  };

  return (
    <>
      <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl flex flex-col h-[715px]">
        <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Terminal className="h-5 w-5 text-indigo-400" />
            <h3 className="font-sans font-bold text-base text-white">Konsol Aktivitas AI Bot</h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleClearLogs}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-950/20 hover:bg-rose-950/40 border border-rose-900/30 hover:border-rose-800 text-rose-400 hover:text-rose-300 transition text-[10px] font-mono cursor-pointer active:scale-95"
              title="Bersihkan Konsol"
            >
              <Trash2 className="h-3 w-3" />
              <span>CLEAR CONSOLE</span>
            </button>
            <button 
              type="button"
              onClick={fetchBotSettings}
              className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white transition cursor-pointer active:scale-90"
              title="Refresh Log"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Live Terminal screen */}
        <div className="flex-1 bg-black/70 rounded-xl p-4 border border-slate-900 font-mono text-[10px] leading-relaxed overflow-y-auto space-y-3 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
          {!botStatus.logs || botStatus.logs.length === 0 ? (
            <div className="text-slate-500 h-full flex flex-col justify-center items-center text-center py-12">
              <Bot className="h-10 w-10 text-slate-800 mb-2 animate-bounce" />
              <p>Menunggu aktivitas bot...</p>
              <p className="text-[9px] text-slate-600 mt-1">Aktifkan Strategy Automation di atas untuk memicu transaksi pertama.</p>
            </div>
          ) : (
            botStatus.logs.map((log) => {
              let actionColor = "text-slate-400";
              let actionLabel = "INFO";
              if (log.action === "BUY") {
                actionColor = "text-emerald-400 font-bold bg-emerald-500/10 px-1 py-0.5 rounded";
                actionLabel = "BUY / LONG";
              } else if (log.action === "SELL") {
                actionColor = "text-rose-400 font-bold bg-rose-500/10 px-1 py-0.5 rounded";
                actionLabel = "SELL / SHORT";
              } else if (log.action === "CLOSE") {
                actionColor = "text-amber-400 font-bold bg-amber-500/10 px-1 py-0.5 rounded";
                actionLabel = "CLOSE";
              } else if (log.action === "WARNING") {
                actionColor = "text-red-500 font-bold bg-red-500/10 px-1 py-0.5 rounded";
                actionLabel = "WARNING";
              } else if (log.action === "HOLD") {
                actionColor = "text-slate-500 font-semibold bg-slate-800/20 px-1 py-0.5 rounded";
                actionLabel = "HOLD";
              }

              return (
                <div key={log.id} className="border-b border-slate-900/45 pb-2.5 space-y-1.5">
                  <div className="flex justify-between items-center gap-2 text-[9px] text-slate-500">
                    <span>{new Date(log.timestamp).toLocaleTimeString("id-ID")} | {log.symbol}</span>
                    <span className={`${actionColor} ml-2 shrink-0`}>{actionLabel} (C:{log.confidence}%)</span>
                  </div>
                  <p className="text-slate-300 break-words leading-normal">{log.message}</p>
                </div>
              );
            })
          )}
        </div>

        {/* Quick Stats Summary Footer */}
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex justify-between items-center text-[10px] font-mono text-slate-500">
          <span className="flex items-center gap-1.5">
            <CheckCircle className="h-3.5 w-3.5 text-indigo-400" />
            Auto Risk Monitoring: Aktif | Logs: {botStatus.logs?.length ?? 0}
          </span>
          <span>Terakhir Update: {new Date().toLocaleTimeString("id-ID")}</span>
        </div>
      </div>

      {/* Detail Posisi Modal */}
      {selectedTrade && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-fadeIn" onClick={() => { setSelectedTrade(null); setConfirmCloseId(null); }}>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full overflow-hidden shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center px-6 py-4 border-b border-slate-800/80 bg-slate-950/40">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-indigo-400" />
                <h3 className="font-mono text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Detail Posisi Aktif
                </h3>
              </div>
              <button 
                onClick={() => setSelectedTrade(null)}
                className="text-slate-400 hover:text-white transition cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 font-mono text-xs">
              <div className="flex justify-between items-center border-b border-slate-850 pb-3">
                <span className="text-slate-400">Target Koin:</span>
                <span className="font-bold text-white text-sm">
                  {(selectedTrade.symbol || selectedTrade.targetAsset || "").replace("USDT", "")} / USDT
                </span>
              </div>

              <div className="flex justify-between items-center border-b border-slate-850 pb-3">
                <span className="text-slate-400">Arah Posisi:</span>
                <span className={`font-bold px-2 py-0.5 rounded text-[10px] ${
                  selectedTrade.type === "BUY" ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"
                }`}>
                  {selectedTrade.type === "BUY" ? "LONG (BUY)" : "SHORT (SELL)"}
                </span>
              </div>

              <div className="flex justify-between items-center border-b border-slate-850 pb-3">
                <span className="text-slate-400">Daya Ungkit (Leverage):</span>
                <span className="text-slate-200 font-bold">{selectedTrade.leverage}x</span>
              </div>

              <div className="flex justify-between items-center border-b border-slate-850 pb-3">
                <span className="text-slate-400">Ukuran Posisi:</span>
                <span className="text-slate-200 font-bold">
                  {selectedTrade.size.toFixed(4)} {(selectedTrade.symbol || selectedTrade.targetAsset || "").replace("USDT", "")}
                </span>
              </div>

              <div className="flex justify-between items-center border-b border-slate-850 pb-3">
                <span className="text-slate-400">Harga Masuk (Entry):</span>
                <span className="text-slate-200 font-bold">${selectedTrade.entryPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
              </div>

              <div className="flex justify-between items-center border-b border-slate-850 pb-3">
                <span className="text-slate-400">Harga Saat Ini:</span>
                <span className="text-slate-200 font-bold">
                  ${(botStatus.currentPrices?.[selectedTrade.symbol] || selectedTrade.entryPrice).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>

              {/* Unrealized PnL */}
              {(() => {
                const livePrice = botStatus.currentPrices?.[selectedTrade.symbol] || selectedTrade.entryPrice;
                const priceDiff = selectedTrade.type === "BUY" ? livePrice - selectedTrade.entryPrice : selectedTrade.entryPrice - livePrice;
                const rawReturn = priceDiff / selectedTrade.entryPrice;
                const fee = selectedTrade.size * selectedTrade.entryPrice * 0.001;
                const grossPnl = rawReturn * (selectedTrade.size * selectedTrade.entryPrice);
                const netPnl = grossPnl - fee;
                const marginUsed = (selectedTrade.size * selectedTrade.entryPrice) / selectedTrade.leverage;
                const pnlPct = (netPnl / marginUsed) * 100;
                
                return (
                  <div className="flex justify-between items-center bg-slate-950/40 p-3 rounded-xl border border-slate-850">
                    <span className="text-slate-400">Unrealized PnL (Net):</span>
                    <div className="text-right">
                      <span className={`font-bold text-sm ${netPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {netPnl >= 0 ? "+" : ""}${netPnl.toFixed(2)}
                      </span>
                      <span className={`block text-[10px] font-semibold ${pnlPct >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                        ({pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(2)}%)
                      </span>
                    </div>
                  </div>
                );
              })()}

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="bg-slate-950/20 border border-slate-850 p-2.5 rounded-xl">
                  <span className="text-slate-500 text-[10px] block">Take Profit (TP)</span>
                  <span className="text-emerald-400 font-bold text-xs">
                    {selectedTrade.tp ? `$${selectedTrade.tp.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "Tidak Diatur"}
                  </span>
                </div>
                <div className="bg-slate-950/20 border border-slate-850 p-2.5 rounded-xl">
                  <span className="text-slate-500 text-[10px] block">Stop Loss (SL)</span>
                  <span className="text-rose-400 font-bold text-xs">
                    {selectedTrade.sl ? `$${selectedTrade.sl.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "Tidak Diatur"}
                  </span>
                </div>
              </div>

              <div className="flex justify-between items-center text-[10px] text-slate-500 pt-2">
                <span>Waktu Transaksi:</span>
                <span>{new Date(selectedTrade.timestamp).toLocaleString("id-ID")}</span>
              </div>
            </div>

            <div className="flex gap-3 px-6 py-4 bg-slate-950/40 border-t border-slate-800/80">
              {confirmCloseId === selectedTrade.id ? (
                <>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleClosePosition(selectedTrade.id); }}
                    disabled={isClosingTrade}
                    className="flex-1 bg-red-700 hover:bg-red-800 text-white font-bold py-2.5 rounded-xl active:scale-[0.98] transition cursor-pointer disabled:opacity-50 text-[11px] font-mono text-center animate-pulse"
                  >
                    {isClosingTrade ? "⏳ Menutup Posisi..." : "⚠️ KONFIRMASI: Ya, Tutup Sekarang!"}
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setConfirmCloseId(null); }}
                    disabled={isClosingTrade}
                    className="px-4 py-2.5 border border-slate-700 hover:bg-slate-800 text-slate-300 hover:text-white font-semibold rounded-xl text-[11px] font-mono transition cursor-pointer"
                  >
                    Tidak
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={(e) => { e.stopPropagation(); setConfirmCloseId(selectedTrade.id); }}
                    disabled={isClosingTrade}
                    className="flex-1 bg-rose-600 hover:bg-rose-700 text-white font-bold py-2.5 rounded-xl active:scale-[0.98] transition cursor-pointer disabled:opacity-50 text-[11px] font-mono text-center"
                  >
                    Tutup Posisi Sekarang
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setSelectedTrade(null); setConfirmCloseId(null); }}
                    className="px-4 py-2.5 border border-slate-800 hover:bg-slate-800 text-slate-300 hover:text-white font-semibold rounded-xl text-[11px] font-mono transition cursor-pointer"
                  >
                    Batal
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
