import React, { useState, useEffect, useRef } from "react";
import { MLModel, LlmSettings } from "../types";
import { 
  Play, 
  Pause, 
  Bot, 
  Settings, 
  Activity, 
  TrendingUp, 
  ShieldAlert, 
  Gauge, 
  Sliders, 
  SlidersHorizontal,
  RefreshCw, 
  CheckCircle, 
  AlertTriangle, 
  BookOpen, 
  Code,
  Terminal,
  Cpu,
  Save,
  Activity as PulseIcon,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  Trash2,
  Timer,
  X
} from "lucide-react";

interface AiBotSettings {
  enabled: boolean;
  symbol: string;
  strategy: "SCALPING" | "SWING" | "CONSERVATIVE" | "AGGRESSIVE" | "MARTINGALE" | "HEDGING";
  leverage: number;
  llmWeight: number;
  mlWeight: number;
  minConfidence: number;
  stopLossPct: number;
  takeProfitPct: number;
  trailingStopPct: number;
  allocationPerTrade: number;
  mlModelId: string;
  sentimentThreshold: number;
  riskLevel: "LOW" | "MEDIUM" | "HIGH";
  tpMultiplier: number;
  slMultiplier: number;
  runIntervalSeconds?: number;
  isCustom?: boolean;
  modelType?: string;
  timeframeMinutes?: number;
}

const PRESETS = {
  safe: {
    strategy: "CONSERVATIVE" as const,
    leverage: 2,
    llmWeight: 0.7,
    mlWeight: 0.3,
    minConfidence: 75,
    takeProfitPct: 1.5,
    stopLossPct: 0.8,
    trailingStopPct: 0.2,
    sentimentThreshold: 0.20,
    riskLevel: "LOW" as const,
    tpMultiplier: 1.0,
    slMultiplier: 1.0,
  },
  medium: {
    strategy: "CONSERVATIVE" as const,
    leverage: 10,
    llmWeight: 0.5,
    mlWeight: 0.5,
    minConfidence: 65,
    takeProfitPct: 3.0,
    stopLossPct: 1.5,
    trailingStopPct: 0.5,
    sentimentThreshold: 0.15,
    riskLevel: "MEDIUM" as const,
    tpMultiplier: 1.0,
    slMultiplier: 1.0,
  },
  high_risk: {
    strategy: "AGGRESSIVE" as const,
    leverage: 25,
    llmWeight: 0.3,
    mlWeight: 0.7,
    minConfidence: 55,
    takeProfitPct: 6.0,
    stopLossPct: 3.0,
    trailingStopPct: 1.0,
    sentimentThreshold: 0.10,
    riskLevel: "HIGH" as const,
    tpMultiplier: 1.2,
    slMultiplier: 0.8,
  }
};

const getPresetName = (s: AiBotSettings) => {
  for (const [name, p] of Object.entries(PRESETS)) {
    if (
      s.strategy === p.strategy &&
      Number(s.leverage) === p.leverage &&
      Math.abs(Number(s.llmWeight) - p.llmWeight) < 0.01 &&
      Math.abs(Number(s.mlWeight) - p.mlWeight) < 0.01 &&
      Number(s.minConfidence) === p.minConfidence &&
      Number(s.takeProfitPct) === p.takeProfitPct &&
      Number(s.stopLossPct) === p.stopLossPct &&
      Number(s.trailingStopPct) === p.trailingStopPct &&
      Math.abs((Number(s.sentimentThreshold) ?? 0.15) - p.sentimentThreshold) < 0.01 &&
      (s.riskLevel ?? "MEDIUM") === p.riskLevel &&
      Number(s.tpMultiplier ?? 1.0) === p.tpMultiplier &&
      Number(s.slMultiplier ?? 1.0) === p.slMultiplier
    ) {
      return name;
    }
  }
  return "custom";
};

interface AiBotLog {
  id: string;
  timestamp: number;
  action: "BUY" | "SELL" | "CLOSE" | "HOLD" | "INFO" | "WARNING";
  symbol: string;
  price: number;
  confidence: number;
  message: string;
}

interface BotStatusData {
  automationEnabled: boolean;
  activeTrades: any[];
  currentConfidence: number;
  logs: AiBotLog[];
  symbol: string;
  currentPrices?: { [symbol: string]: number };
}

interface AIBotPanelProps {
  savedModels: MLModel[];
  llmSettings: LlmSettings;
  active?: boolean;
}

export function AIBotPanel({ savedModels, llmSettings, active }: AIBotPanelProps) {
const [settings, setSettings] = useState<AiBotSettings>({
    enabled: false,
    symbol: "BTCUSDT",
    strategy: "CONSERVATIVE",
    leverage: 10,
    llmWeight: 0.5,
    mlWeight: 0.5,
    minConfidence: 65,
    stopLossPct: 1.5,
    takeProfitPct: 3.0,
    trailingStopPct: 0.5,
    allocationPerTrade: 1000,
    mlModelId: "",
    sentimentThreshold: 0.15,
    riskLevel: "MEDIUM",
    tpMultiplier: 1.0,
    slMultiplier: 1.0,
    runIntervalSeconds: 60,
    modelType: "xgboost",
    timeframeMinutes: 15,
  });

  const [botStatus, setBotStatus] = useState<BotStatusData>({
    automationEnabled: false,
    activeTrades: [],
    currentConfidence: 75,
    logs: [],
    symbol: "BTCUSDT"
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTriggering, setIsTriggering] = useState(false);
  const [statusMsg, setStatusMsg] = useState({ text: "", isError: false });
  const [activatedAt, setActivatedAt] = useState<number>(0);
  const [uptime, setUptime] = useState<string>("00:00:00");
  const [selectedTrade, setSelectedTrade] = useState<any | null>(null);
  const [isClosingTrade, setIsClosingTrade] = useState<boolean>(false);

  const handleClosePosition = async (tradeId: string) => {
    if (!window.confirm("Apakah Anda yakin ingin menutup posisi ini secara manual?")) return;
    setIsClosingTrade(true);
    try {
      const response = await fetch("/api/trade/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tradeId })
      });
      if (response.ok) {
        setStatusMsg({ text: "✅ Posisi berhasil ditutup secara manual.", isError: false });
        setSelectedTrade(null);
        fetchBotStatus();
      } else {
        const errData = await response.json();
        throw new Error(errData.message || "Gagal menutup posisi.");
      }
    } catch (e: any) {
      alert("Error: " + e.message);
    } finally {
      setIsClosingTrade(false);
    }
  };

  // Fetch current AI Bot configuration
  const fetchBotSettings = async () => {
    try {
      const response = await fetch(`/api/ai-bot/settings?t=${Date.now()}`);
      if (response.ok) {
        const data = await response.json();
        if (data.settings) {
          setSettings(data.settings);
        }
      }
    } catch (e) {
      console.error("Gagal mengambil data konfigurasi AI Bot:", e);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch real-time AI Bot status (trades, confidence, state) from the status endpoint
  const fetchBotStatus = async () => {
    try {
      const response = await fetch(`/api/ai-bot/status?t=${Date.now()}`);
      if (response.ok) {
        const data = await response.json();
        console.log('[AIBot Debug] fetchBotStatus response logs count:', data.logs?.length, 'automationEnabled:', data.automationEnabled);
        setBotStatus({
          automationEnabled: data.automationEnabled,
          activeTrades: data.activeTrades || [],
          currentConfidence: data.currentConfidence ?? 75,
          logs: data.logs || [],
          symbol: data.symbol || "BTCUSDT",
          currentPrices: data.currentPrices
        });
        setActivatedAt(data.activatedAt || 0);
      }
    } catch (e) {
      console.error("Gagal mengambil data status real-time AI Bot:", e);
    }
  };

  useEffect(() => {
    if (!active) return;
    fetchBotSettings();
    fetchBotStatus();

    // Poll status statistics every 4 seconds, but do NOT poll/overwrite static settings
    const interval = setInterval(() => {
      fetchBotStatus();
    }, 4000);

    return () => clearInterval(interval);
  }, [active]);

  // Uptime timer: ticks every second showing elapsed time since bot was activated
  useEffect(() => {
    if (!active || !botStatus.automationEnabled || !activatedAt) {
      setUptime("00:00:00");
      return;
    }
    const tick = () => {
      const elapsed = Math.max(0, Math.floor((Date.now() - activatedAt) / 1000));
      const hrs = Math.floor(elapsed / 3600);
      const mins = Math.floor((elapsed % 3600) / 60);
      const secs = elapsed % 60;
      setUptime(
        `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`
      );
    };
    tick();
    const timerId = setInterval(tick, 1000);
    return () => clearInterval(timerId);
  }, [active, botStatus.automationEnabled, activatedAt]);

  const handleToggleBot = async () => {
    setIsSaving(true);
    setStatusMsg({ text: "", isError: false });
    const updatedEnabled = !botStatus.automationEnabled;
    try {
      const response = await fetch("/api/ai-bot/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: updatedEnabled })
      });
      if (response.ok) {
        setSettings((prev) => ({ ...prev, enabled: updatedEnabled }));
        setBotStatus((prev) => ({ ...prev, automationEnabled: updatedEnabled }));
        setActivatedAt(updatedEnabled ? Date.now() : 0);
        setStatusMsg({ 
          text: updatedEnabled 
            ? "🤖 AI Trading Bot AKTIF! Sistem kini memonitor pasar secara otonom." 
            : "⏸️ AI Trading Bot berhasil dinonaktifkan.", 
          isError: false 
        });
        fetchBotStatus();
      } else {
        throw new Error("Gagal mengupdate status bot.");
      }
    } catch (err: any) {
      setStatusMsg({ text: err.message || "Gagal mengupdate status bot.", isError: true });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setStatusMsg({ text: "", isError: false });

    const preset = getPresetName(settings);
    const settingsToSave = {
      ...settings,
      isCustom: preset === "custom"
    };

    try {
      const response = await fetch("/api/ai-bot/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settingsToSave)
      });
      if (response.ok) {
        setStatusMsg({ text: "✅ Konfigurasi strategi & manajemen profit AI Bot berhasil disimpan.", isError: false });
        fetchBotStatus();
      } else {
        throw new Error("Gagal menyimpan konfigurasi.");
      }
    } catch (err: any) {
      setStatusMsg({ text: err.message || "Gagal menyimpan konfigurasi.", isError: true });
    } finally {
      setIsSaving(false);
    }
  };

  const handleTriggerBotStep = async () => {
    setIsTriggering(true);
    setStatusMsg({ text: "", isError: false });
    try {
      const response = await fetch("/api/ai-bot/trigger", { method: "POST" });
      if (response.ok) {
        const data = await response.json();
        if (data.success === false) {
          throw new Error(data.message || "Evaluasi manual bot gagal.");
        }
        setStatusMsg({ text: "⚡ AI Bot Evaluator berhasil dieksekusi secara manual. Periksa konsol aktivitas di bawah!", isError: false });
        fetchBotStatus();
      } else {
        const errData = await response.json();
        throw new Error(errData.message || "Evaluasi manual bot gagal.");
      }
    } catch (err: any) {
      setStatusMsg({ text: err.message || "Evaluasi manual bot gagal.", isError: true });
    } finally {
      setIsTriggering(false);
    }
  };

  const handleClearLogs = async () => {
    try {
      const response = await fetch("/api/ai-bot/logs/clear", { method: "POST" });
        setBotStatus((prev) => ({ ...prev, logs: [] }));
    } catch (e) {
      console.error("Gagal membersihkan log aktivitas bot:", e);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400 gap-3">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-500" />
        <p className="text-xs font-mono">Sinkronisasi parameter otak AI Bot...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* 1. Real-Time Status Monitor Dashboard Header */}
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
                onClick={handleToggleBot}
                disabled={isSaving}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${botStatus.automationEnabled ? 'bg-emerald-500' : 'bg-slate-700'}`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${botStatus.automationEnabled ? 'translate-x-5' : 'translate-x-0'}`}
                />
              </button>
            </div>

            <button
              onClick={handleTriggerBotStep}
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
                        <span className="text-white font-bold">{t.symbol.replace("USDT", "")}</span>
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

      {/* Status Feedback Alerts */}
      {statusMsg.text && (
        <div className={`p-4 rounded-xl border text-xs flex items-center gap-3 ${statusMsg.isError ? "bg-red-500/10 text-red-400 border-red-500/20" : "bg-indigo-500/10 text-indigo-400 border-indigo-500/20"}`}>
          {statusMsg.isError ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle className="h-4 w-4" />}
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* Persistent Strategy Warning/Info Banner */}
      {botStatus.automationEnabled && (
        <div className={`p-4 rounded-2xl border text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 transition duration-300 ${
          ["HEDGING", "AGGRESSIVE", "SCALPING"].includes(settings.strategy)
            ? "bg-amber-500/5 text-amber-400 border-amber-500/15" 
            : "bg-emerald-500/5 text-emerald-400 border-emerald-500/15"
        }`}>
          <div className="flex items-start gap-3">
            <span className="text-base mt-0.5">
              {["HEDGING", "AGGRESSIVE", "SCALPING"].includes(settings.strategy) ? "⚠️" : "🛡️"}
            </span>
            <div className="space-y-1">
              <p className="font-bold font-sans">
                Status Strategi Aktif: <span className="font-mono text-white underline decoration-dotted">{settings.strategy}</span>
              </p>
              <p className="text-[11px] text-slate-400 leading-normal">
                {settings.strategy === "HEDGING" && "Mode Lindung Nilai Aktif. Robot akan membuka posisi dua arah untuk memproteksi modal, dan mengabaikan Konfirmator ML (Veto Gate) untuk eksekusi langsung."}
                {settings.strategy === "AGGRESSIVE" && "Mode Agresif Aktif. Sensitivitas sinyal maksimal, leverage tinggi, dan mengabaikan Konfirmator ML (Veto Gate) untuk eksekusi langsung."}
                {settings.strategy === "SCALPING" && "Mode Scalping Aktif. Eksekusi cepat pada pergerakan mikro, take profit cepat, dan mengabaikan Konfirmator ML (Veto Gate) untuk eksekusi langsung."}
                {settings.strategy === "CONSERVATIVE" && "Mode Konservatif Aktif. Robot sangat berhati-hati, mensyaratkan konfirmasi ganda dari Model ML (Veto Gate) sebelum membuka posisi."}
                {settings.strategy === "SWING" && "Mode Swing Aktif. Mencari tren jangka menengah/panjang dengan target profit lebar, mensyaratkan konfirmasi ganda dari Model ML (Veto Gate) sebelum membuka posisi."}
                {settings.strategy === "MARTINGALE" && "Mode Martingale Aktif. Melakukan akumulasi bertingkat untuk rata-rata harga masuk, mensyaratkan konfirmasi ganda dari Model ML (Veto Gate) sebelum membuka posisi."}
              </p>
            </div>
          </div>
          <div className="shrink-0">
            <span className={`px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase ${
              ["HEDGING", "AGGRESSIVE", "SCALPING"].includes(settings.strategy)
                ? "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                : "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
            }`}>
              {["HEDGING", "AGGRESSIVE", "SCALPING"].includes(settings.strategy) ? "Veto Gate: Bypassed ⚡" : "Veto Gate: Enforced 🛡️"}
            </span>
          </div>
        </div>
      )}

      {/* Main Grid: Settings & Live Console */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column - Configuration forms (7cols) */}
        <div className="lg:col-span-7 space-y-6">
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
                    className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-sans font-bold text-white"
                  >
                    <option value="CONSERVATIVE">🛡️ CONSERVATIVE (Hati-Hati, Presisi Tinggi)</option>
                    <option value="SCALPING">⚡ SCALPING (Cepat, Profit Mikro, SL Ketat)</option>
                    <option value="SWING">📈 SWING (Tren Panjang, Target Profit Lebar)</option>
                    <option value="AGGRESSIVE">🔥 AGGRESSIVE (Sensitivitas Tinggi, Leverage Maks)</option>
                    <option value="MARTINGALE">🔄 MARTINGALE (Penggandaan Posisi, Target Rebound Cepat)</option>
                    <option value="HEDGING">🔒 HEDGING (Membuka Posisi Protektif Dua Arah)</option>
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
                      value={settings.runIntervalSeconds}
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
                        min="0.0"
                        value={settings.trailingStopPct}
                        onChange={(e) => setSettings((prev) => ({ ...prev, trailingStopPct: parseFloat(e.target.value) || 0.5 }))}
                        className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
                      />
                      <span className="text-slate-500 font-mono">%</span>
                    </div>
                  </div>
                </div>
                <p className="text-[10px] text-slate-500">
                  Proteksi otonom yang langsung tertanam saat bot membuka posisi. Trailing stop mengunci profit saat harga berbalik arah.
                </p>
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

              {/* LLM Provider Warnings if Simulation fallback is used */}
              {llmSettings.provider === "simulated" && (
                <div className="p-3.5 bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 rounded-xl flex items-start gap-2.5">
                  <AlertTriangle className="h-4.5 w-4.5 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold">Provider LLM Berjalan dalam Mode Simulasi</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      Sistem sedang menggunakan fallback generator sentimen cerdas internal. Untuk mengaktifkan evaluasi LLM real-time yang murni (Gemini/OpenAI), harap konfigurasikan API key Anda di tab **Pengaturan AI & Notif**.
                    </p>
                  </div>
                </div>
              )}

              {/* Submit Buttons */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold cursor-pointer transition active:scale-95 disabled:opacity-50 text-xs shadow-lg shadow-indigo-600/10"
                >
                  <Save className="h-4 w-4" /> Save Configuration
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column - Live bot execution logs / terminal style (5cols) */}
        <div className="lg:col-span-5 space-y-6">
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
        </div>
      </div>

      {/* Detail Posisi Modal */}
      {selectedTrade && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full overflow-hidden shadow-2xl">
            {/* Modal Header */}
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

            {/* Modal Body */}
            <div className="p-6 space-y-4 font-mono text-xs">
              <div className="flex justify-between items-center border-b border-slate-850 pb-3">
                <span className="text-slate-400">Target Koin:</span>
                <span className="font-bold text-white text-sm">
                  {selectedTrade.symbol.replace("USDT", "")} / USDT
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
                  {selectedTrade.size.toFixed(4)} {selectedTrade.symbol.replace("USDT", "")}
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

            {/* Modal Actions */}
            <div className="flex gap-3 px-6 py-4 bg-slate-950/40 border-t border-slate-800/80">
              <button
                onClick={() => handleClosePosition(selectedTrade.id)}
                disabled={isClosingTrade}
                className="flex-1 bg-rose-600 hover:bg-rose-700 text-white font-bold py-2 rounded-xl active:scale-[0.98] transition cursor-pointer disabled:opacity-50 text-[11px] font-mono text-center"
              >
                {isClosingTrade ? "Menutup Posisi..." : "Tutup Posisi Sekarang"}
              </button>
              <button
                onClick={() => setSelectedTrade(null)}
                className="px-4 py-2 border border-slate-800 hover:bg-slate-800 text-slate-300 hover:text-white font-semibold rounded-xl text-[11px] font-mono transition cursor-pointer"
              >
                Batal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
