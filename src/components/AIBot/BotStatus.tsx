import React, { useState } from "react";
import { Bot, Activity, Timer, Gauge, ShieldAlert } from "lucide-react";
import { AiBotSettings, BotStatusData } from "./types";
import { Activity as PulseIcon } from "lucide-react";

interface Props {
  botStatus: BotStatusData;
  settings: AiBotSettings;
  uptime: string;
  isSaving: boolean;
  isTriggering: boolean;
  onToggleBot: () => void;
  onTriggerStep: () => void;
  setSelectedTrade: (trade: any) => void;
}

export function BotStatus({
  botStatus,
  settings,
  uptime,
  isSaving,
  isTriggering,
  onToggleBot,
  onTriggerStep,
  setSelectedTrade
}: Props) {
  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-6">
      <div className="flex flex-col lg:flex-row justify-between lg:items-center gap-6 border-b border-slate-800 pb-5">
        <div className="flex items-start gap-4">
          <div className={`p-3 rounded-2xl border ${botStatus.automationEnabled ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/25 animate-pulse" : "bg-slate-800 text-slate-400 border-slate-700"}`}>
            <Bot className="h-7 w-7" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="font-sans font-black text-lg text-white">Strategy Automation Control Room</h2>
              <div className={`h-2.5 w-2.5 rounded-full ${botStatus.automationEnabled ? "bg-emerald-500 animate-ping" : "bg-slate-600"}`}></div>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-xl">
              Monitor status transaksi aktif, tingkat keyakinan keputusan LLM, dan pergerakan proteksi risiko stop-loss/take-profit secara langsung dari robot AI.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Strategy Automation Toggle Switch */}
          <div className="flex items-center gap-3 bg-slate-950 border border-slate-850 px-4 py-2 rounded-xl">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider font-bold">Strategy Automation</span>
            <button
              onClick={onToggleBot}
              disabled={isSaving}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${botStatus.automationEnabled ? 'bg-emerald-500' : 'bg-slate-700'}`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${botStatus.automationEnabled ? 'translate-x-5' : 'translate-x-0'}`}
              />
            </button>
          </div>

          <button
            onClick={onTriggerStep}
            disabled={isTriggering}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-800 hover:border-slate-700 bg-slate-950 text-slate-300 hover:text-white text-xs font-bold font-mono active:scale-95 transition cursor-pointer disabled:opacity-50"
          >
            <Activity className={`h-4 w-4 ${isTriggering ? "animate-spin text-indigo-400" : ""}`} />
            Trigger Step
          </button>

          {/* Live Uptime Timer */}
          {botStatus.automationEnabled && (
            <div className="flex items-center gap-2 bg-slate-950 border border-emerald-500/20 px-4 py-2 rounded-xl">
              <Timer className="h-4 w-4 text-emerald-400 animate-pulse" />
              <div className="text-xs font-mono">
                <span className="text-slate-400">Uptime:</span>{" "}
                <span className="font-bold tabular-nums text-emerald-400">
                  {uptime}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Real-Time Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Stat 1: LLM Decision Confidence Gauge */}
        <div className="bg-slate-950/40 border border-slate-850 rounded-2xl p-4.5 flex flex-col justify-between space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-mono font-bold text-indigo-400 uppercase tracking-wider">LLM Confidence Level</span>
            <Gauge className="h-4.5 w-4.5 text-indigo-400" />
          </div>
          
          <div className="space-y-1">
            <div className="flex justify-between items-baseline">
              <span className="text-3xl font-mono font-bold text-white">{botStatus.currentConfidence}%</span>
              <span className="text-[10px] text-slate-500 font-mono">Min Target: {settings.minConfidence}%</span>
            </div>
            <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-1000 ${botStatus.currentConfidence >= settings.minConfidence ? "bg-indigo-500" : "bg-amber-500"}`}
                style={{ width: `${botStatus.currentConfidence}%` }}
              ></div>
            </div>
          </div>

          <p className="text-[10px] text-slate-500 leading-normal">
            {botStatus.currentConfidence >= settings.minConfidence 
              ? "✓ Tingkat keyakinan aman untuk melakukan eksekusi posisi baru." 
              : "⚠ Di bawah batas minimal keyakinan. Robot akan menahan order (HOLD)."}
          </p>
        </div>

        {/* Stat 2: Active Bot Positions Monitor */}
        <div className="bg-slate-950/40 border border-slate-850 rounded-2xl p-4.5 flex flex-col justify-between space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-wider">Active Bot Trades</span>
            <PulseIcon className="h-4.5 w-4.5 text-emerald-400" />
          </div>

          {botStatus.activeTrades.length === 0 ? (
            <div className="py-2 text-slate-500 font-mono text-[10px] space-y-1">
              <p className="font-bold text-slate-400">Tidak Ada Posisi Terbuka</p>
              <p className="text-[9px]">Robot sedang mengamati pasar.</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[100px] overflow-y-auto pr-1">
              {botStatus.activeTrades.map((t) => (
                <div 
                  key={t.id} 
                  onClick={() => setSelectedTrade(t)}
                  title="Klik untuk detail posisi"
                  className="flex justify-between items-center bg-slate-950/80 border border-slate-900 hover:border-slate-700 p-2 rounded-lg text-[10px] font-mono cursor-pointer transition duration-200"
                >
                  <div>
                    <div className="flex items-center gap-1">
                      <span className={`font-bold ${t.type === "BUY" ? "text-emerald-400" : "text-rose-400"}`}>
                        {t.type === "BUY" ? "LONG" : "SHORT"}
                      </span>
                      <span className="text-white font-bold">{(t.symbol || t.targetAsset || "").replace("USDT", "")}</span>
                      <span className="text-slate-500">{t.leverage}x</span>
                    </div>
                    <p className="text-slate-500 text-[9px]">Entry: ${t.entryPrice.toLocaleString()}</p>
                  </div>

                  <div className="text-right flex flex-col items-end">
                    <span className="text-slate-300 font-bold">Size: {t.size.toFixed(3)}</span>
                    <p className="text-[9px] text-emerald-400 font-bold flex items-center gap-0.5 justify-end">
                      <ShieldAlert className="h-2.5 w-2.5 text-indigo-400 inline" /> SLActive
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          <p className="text-[10px] text-slate-500 leading-normal">
            Keamanan modal dijamin oleh trigger stop-loss otomatis di backend secara instan.
          </p>
        </div>

        {/* Stat 3: Auto-Trading Activity Signal Summary */}
        <div className="bg-slate-950/40 border border-slate-850 rounded-2xl p-4.5 flex flex-col justify-between space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-mono font-bold text-amber-400 uppercase tracking-wider">Risk Management Settings</span>
            <ShieldAlert className="h-4.5 w-4.5 text-amber-400" />
          </div>

          <div className="grid grid-cols-3 gap-1.5 text-center font-mono text-[10px]">
            <div className="bg-slate-950 p-1.5 rounded-xl border border-slate-900">
              <p className="text-slate-500 text-[8px]">TP (%)</p>
              <p className="text-white font-bold">{settings.takeProfitPct}%</p>
            </div>
            <div className="bg-slate-950 p-1.5 rounded-xl border border-slate-900">
              <p className="text-slate-500 text-[8px]">SL (%)</p>
              <p className="text-white font-bold">{settings.stopLossPct}%</p>
            </div>
            <div className="bg-slate-950 p-1.5 rounded-xl border border-slate-900">
              <p className="text-slate-500 text-[8px]">TS (%)</p>
              <p className="text-white font-bold">{settings.trailingStopPct}%</p>
            </div>
          </div>

          <p className="text-[10px] text-slate-500 leading-normal">
            Metrik risiko dikendalikan secara real-time berdasarkan level risiko: <span className="text-white font-bold font-mono">{settings.riskLevel}</span>
          </p>
        </div>
      </div>
    </div>
  );
}
