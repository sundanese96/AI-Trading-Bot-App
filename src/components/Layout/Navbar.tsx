import React, { useState } from "react";
import {
  TrendingUp,
  Newspaper,
  Cpu,
  Bot,
  Sliders,
  Activity,
  HelpCircle,
  Scale,
  LogOut
} from "lucide-react";

export type TabType = "TRADING" | "NEWS" | "BACKTEST" | "ML" | "AI_BOT" | "SETTINGS" | "LIVE" | "DOCS";

interface NavbarProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  onResetPortfolio: () => void;
  onLogout: () => void;
}

export function Navbar({
  activeTab,
  setActiveTab,
  onResetPortfolio,
  onLogout
}: NavbarProps) {
  const [confirmReset, setConfirmReset] = useState(false);
  const [confirmLogout, setConfirmLogout] = useState(false);

  return (
    <nav className="border-b border-slate-900 bg-slate-900/45 backdrop-blur-xl px-6 py-4 flex flex-wrap justify-between items-center gap-4">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 bg-gradient-to-tr from-indigo-600 to-purple-600 rounded-2xl flex items-center justify-center font-sans font-extrabold text-white text-xl tracking-tighter shadow-lg shadow-indigo-600/25">
          KS
        </div>
        <div>
          <h1 className="font-sans font-extrabold text-lg text-white tracking-tight flex items-center gap-1.5">
            KriptoSakti <span className="text-[10px] bg-indigo-500/10 text-indigo-400 font-mono font-bold px-2 py-0.5 rounded border border-indigo-500/20">V3.5</span>
          </h1>
          <p className="text-[10px] text-slate-500 font-mono">Platform Trading Simulasi, Sentimen Gemini & ML Backtest</p>
        </div>
      </div>

      {/* Tab Selection */}
      <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-850">
        <button
          onClick={() => setActiveTab("TRADING")}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition font-sans cursor-pointer ${
            activeTab === "TRADING" ? "bg-slate-900 text-indigo-400 border border-slate-850" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          <TrendingUp className="h-3.5 w-3.5" /> Desk Trading
        </button>
        <button
          onClick={() => setActiveTab("NEWS")}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition font-sans cursor-pointer ${
            activeTab === "NEWS" ? "bg-slate-900 text-indigo-400 border border-slate-850" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          <Newspaper className="h-3.5 w-3.5" /> Sentimen Berita
        </button>
        <button
          onClick={() => setActiveTab("BACKTEST")}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition font-sans cursor-pointer ${
            activeTab === "BACKTEST" ? "bg-slate-900 text-indigo-400 border border-slate-850" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          <Scale className="h-3.5 w-3.5" /> Backtester
        </button>
        <button
          onClick={() => setActiveTab("ML")}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition font-sans cursor-pointer ${
            activeTab === "ML" ? "bg-slate-900 text-indigo-400 border border-slate-850" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          <Cpu className="h-3.5 w-3.5" /> AI & ML Local
        </button>
        <button
          onClick={() => setActiveTab("AI_BOT")}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition font-sans cursor-pointer ${
            activeTab === "AI_BOT" ? "bg-slate-900 text-indigo-400 border border-slate-850" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          <Bot className="h-3.5 w-3.5" /> AI Bot Auto-Trade
        </button>
        <button
          onClick={() => setActiveTab("SETTINGS")}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition font-sans cursor-pointer ${
            activeTab === "SETTINGS" ? "bg-slate-900 text-indigo-400 border border-slate-850" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          <Sliders className="h-3.5 w-3.5" /> Pengaturan AI & Notif
        </button>
        <button
          onClick={() => setActiveTab("LIVE")}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition font-sans cursor-pointer ${
            activeTab === "LIVE" ? "bg-slate-900 text-amber-500 border border-slate-850/80 shadow-md shadow-amber-500/5" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          <Activity className="h-3.5 w-3.5 text-amber-500" /> LIVE TRADING
        </button>
        <button
          onClick={() => setActiveTab("DOCS")}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition font-sans cursor-pointer ${
            activeTab === "DOCS" ? "bg-slate-900 text-indigo-400 border border-slate-850" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          <HelpCircle className="h-3.5 w-3.5" /> Docs / About
        </button>
      </div>

      {/* Reset / Controls */}
      <div className="flex gap-2">
        {confirmReset ? (
          <div className="flex items-center gap-1">
            <button
              onClick={() => {
                onResetPortfolio();
                setConfirmReset(false);
              }}
              className="text-[10px] font-mono bg-red-600 hover:bg-red-700 text-white font-bold px-3 py-1.5 rounded-lg transition active:scale-95 cursor-pointer animate-pulse"
            >
              Yakin Reset?
            </button>
            <button
              onClick={() => setConfirmReset(false)}
              className="text-[10px] font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white px-2 py-1.5 rounded-lg transition cursor-pointer"
            >
              Batal
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmReset(true)}
            className="text-[10px] font-mono bg-red-950/20 border border-red-900/30 hover:border-red-500 hover:text-white text-red-400 px-3 py-1.5 rounded-lg transition active:scale-95 cursor-pointer"
          >
            Reset Demo Wallet
          </button>
        )}

        {confirmLogout ? (
          <div className="flex items-center gap-1">
            <button
              onClick={() => {
                onLogout();
                setConfirmLogout(false);
              }}
              className="flex items-center gap-1.5 text-[10px] font-mono bg-rose-600 hover:bg-rose-700 text-white font-bold px-3 py-1.5 rounded-lg transition active:scale-95 cursor-pointer"
            >
              Yakin Keluar?
            </button>
            <button
              onClick={() => setConfirmLogout(false)}
              className="text-[10px] font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white px-2 py-1.5 rounded-lg transition cursor-pointer"
            >
              Batal
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmLogout(true)}
            className="flex items-center gap-1.5 text-[10px] font-mono bg-slate-900/60 border border-slate-800 hover:border-slate-650 hover:border-slate-500 hover:text-white text-slate-400 px-3 py-1.5 rounded-lg transition active:scale-95 cursor-pointer"
          >
            <LogOut className="h-3 w-3" /> Keluar
          </button>
        )}
      </div>
    </nav>
  );
}
