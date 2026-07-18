import React, { useState, useEffect, useRef } from "react";
import { MLModel, LlmSettings } from "../../types";
import { RefreshCw, AlertTriangle, CheckCircle } from "lucide-react";
import { BotSettingsForm } from "./BotSettingsForm";
import { BotStatus } from "./BotStatus";
import { BotLogsTable } from "./BotLogsTable";
import { AiBotSettings, BotStatusData } from "./types";
import { apiBot } from "../../api/client";

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
    llmWeight: 0.7,
    mlWeight: 0.3,
    minConfidence: 65,
    stopLossPct: 1.5,
    takeProfitPct: 3.0,
    trailingStopPct: 0.5,
    allocationPerTrade: 10,
    mlModelId: savedModels[0]?.id || "",
    sentimentThreshold: 0.15,
    riskLevel: "MEDIUM",
    tpMultiplier: 1.0,
    slMultiplier: 1.0,
    runIntervalSeconds: 10,
    modelType: "xgboost",
    timeframeMinutes: 15,
  });

  const [botStatus, setBotStatus] = useState<BotStatusData>({
    automationEnabled: false,
    activeTrades: [],
    currentConfidence: 0,
    logs: [],
    symbol: "BTCUSDT",
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTriggering, setIsTriggering] = useState(false);
  const [statusMsg, setStatusMsg] = useState({ text: "", isError: false });
  const [uptime, setUptime] = useState("00:00:00");
  const [selectedTrade, setSelectedTrade] = useState<any | null>(null);
  
  const uptimeTimer = useRef<number | null>(null);
  const startTime = useRef<number | null>(null);

  const fetchInitialSettings = async () => {
    try {
      const dataSettings = await apiBot.getSettings();
      if (dataSettings) {
        setSettings(prev => ({ ...prev, ...dataSettings }));
      }
      await pollBotStatus();
    } catch (e) {
      console.error("Gagal memuat pengaturan awal AI Bot:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const pollBotStatus = async () => {
    try {
      const dataStatus = await apiBot.getStatus();
      if (dataStatus) {
        setBotStatus(dataStatus);
        
        // Auto Sync UI local state toggle with backend state
        if (dataStatus.automationEnabled) {
          if (!startTime.current || (dataStatus.activatedAt && startTime.current !== dataStatus.activatedAt)) {
            startTime.current = dataStatus.activatedAt || Date.now();
            startUptimeTimer();
          }
        } else {
          stopUptimeTimer();
        }
      }
    } catch (e) {
      console.error("Gagal memuat status AI Bot:", e);
    }
  };

  useEffect(() => {
    fetchInitialSettings();
  }, []);

  // Poll status periodically if active
  useEffect(() => {
    if (!active) return;
    const interval = setInterval(() => {
      pollBotStatus();
    }, (settings.runIntervalSeconds || 10) * 1000);
    return () => clearInterval(interval);
  }, [active, settings.runIntervalSeconds]);

  const startUptimeTimer = () => {
    if (uptimeTimer.current) clearInterval(uptimeTimer.current);
    uptimeTimer.current = window.setInterval(() => {
      if (!startTime.current) return;
      const diff = Math.floor((Date.now() - startTime.current) / 1000);
      const h = Math.floor(diff / 3600).toString().padStart(2, "0");
      const m = Math.floor((diff % 3600) / 60).toString().padStart(2, "0");
      const s = (diff % 60).toString().padStart(2, "0");
      setUptime(`${h}:${m}:${s}`);
    }, 1000);
  };

  const stopUptimeTimer = () => {
    if (uptimeTimer.current) {
      clearInterval(uptimeTimer.current);
      uptimeTimer.current = null;
    }
    startTime.current = null;
    setUptime("00:00:00");
  };

  useEffect(() => {
    return () => stopUptimeTimer();
  }, []);

  const handleToggleBot = async () => {
    setIsSaving(true);
    setStatusMsg({ text: "", isError: false });
    const newState = !botStatus.automationEnabled;
    try {
      const updatedSettings = { ...settings, enabled: newState };
      await apiBot.saveSettings(updatedSettings);
      
      setBotStatus(prev => ({ ...prev, automationEnabled: newState }));
      setSettings(updatedSettings);
      
      if (newState) {
        startTime.current = Date.now();
        startUptimeTimer();
        setStatusMsg({ text: "Strategy Automation diaktifkan. AI sedang mengamati market.", isError: false });
      } else {
        stopUptimeTimer();
        setStatusMsg({ text: "Strategy Automation dihentikan sementara.", isError: false });
      }
    } catch (e: any) {
      setStatusMsg({ text: "Gagal mengubah status: " + (e.message || "Network error"), isError: true });
    } finally {
      setIsSaving(false);
    }
  };

  const handleTriggerBotStep = async () => {
    setIsTriggering(true);
    try {
      const data = await apiBot.triggerSimulation();
      if (data.status === "SIMULATED") {
        alert("Simulasi step dijalankan: " + data.message);
      }
      fetchBotSettings();
    } catch (e: any) {
      alert("Gagal memicu bot step: " + (e.message || "Network error"));
    } finally {
      setIsTriggering(false);
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
      <BotStatus 
        botStatus={botStatus}
        settings={settings}
        uptime={uptime}
        isSaving={isSaving}
        isTriggering={isTriggering}
        onToggleBot={handleToggleBot}
        onTriggerStep={handleTriggerBotStep}
        setSelectedTrade={setSelectedTrade}
      />

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
        <div className="lg:col-span-7 space-y-6">
          <BotSettingsForm 
            settings={settings}
            setSettings={setSettings}
          />

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
        </div>

        <div className="lg:col-span-5 space-y-6">
          <BotLogsTable 
            botStatus={botStatus}
            fetchBotSettings={pollBotStatus}
            setBotStatus={setBotStatus}
            selectedTrade={selectedTrade}
            setSelectedTrade={setSelectedTrade}
          />
        </div>
      </div>
    </div>
  );
}
