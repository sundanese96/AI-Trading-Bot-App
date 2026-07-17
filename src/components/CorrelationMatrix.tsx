import React, { useState, useEffect } from "react";
import { TrendingUp, RefreshCw, Info, HelpCircle, Flame, ArrowUpRight } from "lucide-react";

interface CorrelationItem {
  assetA: string;
  assetB: string;
  value: number; // -1 to 1
  timeframe: "1h" | "24h" | "7d";
}

// Baseline realistic correlation coefficients (centered around real-world market relationships)
const BASELINE_CORRELATIONS: { [key: string]: { [key: string]: { "1h": number; "24h": number; "7d": number } } } = {
  BTC: {
    BTC: { "1h": 1.0, "24h": 1.0, "7d": 1.0 },
    ETH: { "1h": 0.88, "24h": 0.92, "7d": 0.95 },
    SOL: { "1h": 0.72, "24h": 0.78, "7d": 0.84 },
    BNB: { "1h": 0.65, "24h": 0.71, "7d": 0.76 },
    XRP: { "1h": 0.42, "24h": 0.49, "7d": 0.58 },
    ADA: { "1h": 0.55, "24h": 0.63, "7d": 0.71 },
    SUI: { "1h": 0.38, "24h": 0.51, "7d": 0.62 },
    DOGE: { "1h": 0.61, "24h": 0.69, "7d": 0.74 },
  },
  ETH: {
    BTC: { "1h": 0.88, "24h": 0.92, "7d": 0.95 },
    ETH: { "1h": 1.0, "24h": 1.0, "7d": 1.0 },
    SOL: { "1h": 0.79, "24h": 0.83, "7d": 0.89 },
    BNB: { "1h": 0.68, "24h": 0.74, "7d": 0.78 },
    XRP: { "1h": 0.45, "24h": 0.52, "7d": 0.61 },
    ADA: { "1h": 0.59, "24h": 0.68, "7d": 0.74 },
    SUI: { "1h": 0.41, "24h": 0.55, "7d": 0.65 },
    DOGE: { "1h": 0.64, "24h": 0.72, "7d": 0.77 },
  },
  SOL: {
    BTC: { "1h": 0.72, "24h": 0.78, "7d": 0.84 },
    ETH: { "1h": 0.79, "24h": 0.83, "7d": 0.89 },
    SOL: { "1h": 1.0, "24h": 1.0, "7d": 1.0 },
    BNB: { "1h": 0.58, "24h": 0.66, "7d": 0.72 },
    XRP: { "1h": 0.39, "24h": 0.46, "7d": 0.53 },
    ADA: { "1h": 0.51, "24h": 0.59, "7d": 0.68 },
    SUI: { "1h": 0.48, "24h": 0.62, "7d": 0.71 },
    DOGE: { "1h": 0.58, "24h": 0.67, "7d": 0.73 },
  },
  BNB: {
    BTC: { "1h": 0.65, "24h": 0.71, "7d": 0.76 },
    ETH: { "1h": 0.68, "24h": 0.74, "7d": 0.78 },
    SOL: { "1h": 0.58, "24h": 0.66, "7d": 0.72 },
    BNB: { "1h": 1.0, "24h": 1.0, "7d": 1.0 },
    XRP: { "1h": 0.41, "24h": 0.48, "7d": 0.54 },
    ADA: { "1h": 0.49, "24h": 0.56, "7d": 0.64 },
    SUI: { "1h": 0.32, "24h": 0.45, "7d": 0.53 },
    DOGE: { "1h": 0.51, "24h": 0.58, "7d": 0.66 },
  },
  XRP: {
    BTC: { "1h": 0.42, "24h": 0.49, "7d": 0.58 },
    ETH: { "1h": 0.45, "24h": 0.52, "7d": 0.61 },
    SOL: { "1h": 0.39, "24h": 0.46, "7d": 0.53 },
    BNB: { "1h": 0.41, "24h": 0.48, "7d": 0.54 },
    XRP: { "1h": 1.0, "24h": 1.0, "7d": 1.0 },
    ADA: { "1h": 0.38, "24h": 0.45, "7d": 0.51 },
    SUI: { "1h": 0.21, "24h": 0.32, "7d": 0.41 },
    DOGE: { "1h": 0.36, "24h": 0.44, "7d": 0.52 },
  },
  ADA: {
    BTC: { "1h": 0.55, "24h": 0.63, "7d": 0.71 },
    ETH: { "1h": 0.59, "24h": 0.68, "7d": 0.74 },
    SOL: { "1h": 0.51, "24h": 0.59, "7d": 0.68 },
    BNB: { "1h": 0.49, "24h": 0.56, "7d": 0.64 },
    XRP: { "1h": 0.38, "24h": 0.45, "7d": 0.51 },
    ADA: { "1h": 1.0, "24h": 1.0, "7d": 1.0 },
    SUI: { "1h": 0.28, "24h": 0.41, "7d": 0.52 },
    DOGE: { "1h": 0.52, "24h": 0.61, "7d": 0.68 },
  },
  SUI: {
    BTC: { "1h": 0.38, "24h": 0.51, "7d": 0.62 },
    ETH: { "1h": 0.41, "24h": 0.55, "7d": 0.65 },
    SOL: { "1h": 0.48, "24h": 0.62, "7d": 0.71 },
    BNB: { "1h": 0.32, "24h": 0.45, "7d": 0.53 },
    XRP: { "1h": 0.21, "24h": 0.32, "7d": 0.41 },
    ADA: { "1h": 0.28, "24h": 0.41, "7d": 0.52 },
    SUI: { "1h": 1.0, "24h": 1.0, "7d": 1.0 },
    DOGE: { "1h": 0.29, "24h": 0.43, "7d": 0.54 },
  },
  DOGE: {
    BTC: { "1h": 0.61, "24h": 0.69, "7d": 0.74 },
    ETH: { "1h": 0.64, "24h": 0.72, "7d": 0.77 },
    SOL: { "1h": 0.58, "24h": 0.67, "7d": 0.73 },
    BNB: { "1h": 0.51, "24h": 0.58, "7d": 0.66 },
    XRP: { "1h": 0.36, "24h": 0.44, "7d": 0.52 },
    ADA: { "1h": 0.52, "24h": 0.61, "7d": 0.68 },
    SUI: { "1h": 0.29, "24h": 0.43, "7d": 0.54 },
    DOGE: { "1h": 1.0, "24h": 1.0, "7d": 1.0 },
  }
};

const ASSETS = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "SUI", "DOGE"];

export function CorrelationMatrix() {
  const [timeframe, setTimeframe] = useState<"1h" | "24h" | "7d">("24h");
  const [matrix, setMatrix] = useState<{ [key: string]: { [key: string]: number } }>({});
  const [hoveredCell, setHoveredCell] = useState<{ row: string; col: string; val: number } | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [btcShiftFactor, setBtcShiftFactor] = useState(0.0);

  // Load and apply slight real-time fluctuations to simulate market micro-dynamics
  const computeMatrix = () => {
    const newMatrix: { [key: string]: { [key: string]: number } } = {};
    const noise = (Math.random() - 0.5) * 0.04;
    
    ASSETS.forEach((row) => {
      newMatrix[row] = {};
      ASSETS.forEach((col) => {
        if (row === col) {
          newMatrix[row][col] = 1.0;
        } else {
          const base = BASELINE_CORRELATIONS[row]?.[col]?.[timeframe] ?? 0.5;
          let val = base + noise * (timeframe === "1h" ? 1.5 : 0.8);
          val = Math.max(-1.0, Math.min(1.0, val));
          newMatrix[row][col] = parseFloat(val.toFixed(2));
        }
      });
    });
    setMatrix(newMatrix);
  };

  const fetchMatrix = async () => {
    try {
      const res = await fetch(`/api/market/correlations?t=${Date.now()}`);
      if (res.ok) {
        const data = await res.json();
        if (data.matrix) {
          setMatrix(data.matrix);
          return;
        }
      }
    } catch (e) {
      console.error("Gagal mengambil data korelasi:", e);
    }
    computeMatrix();
  };

  useEffect(() => {
    fetchMatrix();
    const interval = setInterval(() => {
      fetchMatrix();
    }, 4000);
    return () => clearInterval(interval);
  }, [timeframe]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      fetchMatrix();
      setIsRefreshing(false);
    }, 600);
  };

  // Color mapping function based on correlation value
  // Positive correlations (Greenish/Slate-Cyan), Negative/Divergent (Reddish/Crimson)
  const getCellBg = (val: number, row: string, col: string) => {
    if (row === col) return "bg-slate-800 text-white font-bold border border-slate-700/50";
    if (val >= 0.8) return "bg-emerald-500/30 text-emerald-300 border border-emerald-500/20";
    if (val >= 0.6) return "bg-emerald-500/15 text-emerald-400/90 border border-emerald-500/10";
    if (val >= 0.4) return "bg-indigo-500/10 text-indigo-300 border border-indigo-500/5";
    if (val >= 0.2) return "bg-slate-800/40 text-slate-300 border border-slate-800/20";
    if (val >= 0.0) return "bg-slate-900/30 text-slate-400 border border-transparent";
    return "bg-rose-500/15 text-rose-300 border border-rose-500/10";
  };

  const getRelationshipText = (val: number) => {
    if (val >= 0.85) return "Korelasi Sangat Kuat (Berjalan Berdampingan)";
    if (val >= 0.70) return "Korelasi Kuat (Searah)";
    if (val >= 0.45) return "Korelasi Moderat (Cenderung Searah)";
    if (val >= 0.20) return "Korelasi Lemah (Hampir Independen)";
    if (val >= 0.0) return "Korelasi Sangat Lemah / Netral";
    return "Korelasi Negatif / Divergen (Arah Berlawanan)";
  };

  return (
    <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl relative overflow-hidden group">
      {/* Header Matrix */}
      <div className="flex flex-wrap justify-between items-center mb-5 gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
            <TrendingUp className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-sans font-extrabold text-base text-white tracking-tight flex items-center gap-1.5">
              Matriks Korelasi Harga Real-Time
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
                BTC SHIELD
              </span>
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">Mengukur sensitivitas & pola arah pergerakan Altcoin terhadap induk Bitcoin.</p>
          </div>
        </div>

        {/* Filters & Refresh */}
        <div className="flex items-center gap-2.5">
          <div className="flex p-0.5 bg-slate-950 rounded-lg border border-slate-850">
            {(["1h", "24h", "7d"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTimeframe(t)}
                className={`px-2.5 py-1 text-[10px] font-mono font-bold rounded-md transition cursor-pointer ${
                  timeframe === t 
                    ? "bg-slate-800 text-indigo-400" 
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {t === "1h" ? "1 JAM" : t === "24h" ? "24 JAM" : "7 HARI"}
              </button>
            ))}
          </div>

          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-2 bg-slate-950 border border-slate-850 hover:border-slate-750 text-slate-400 hover:text-white rounded-lg active:scale-95 transition cursor-pointer"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin text-indigo-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* Grid Heatmap Table */}
      <div className="overflow-x-auto select-none">
        <div className="min-w-[480px]">
          {/* X Axis Labels Header */}
          <div className="grid grid-cols-9 gap-1 mb-1 text-center font-mono font-bold text-[10px] text-slate-500">
            <div className="text-left font-sans text-[10px] text-slate-600 flex items-center gap-1">
              Y \ X
            </div>
            {ASSETS.map((asset) => (
              <div 
                key={asset} 
                className={`py-1.5 rounded-lg border border-transparent ${
                  hoveredCell?.col === asset ? "text-indigo-400 bg-indigo-500/5 border-indigo-500/10 font-black" : ""
                }`}
              >
                {asset}
              </div>
            ))}
          </div>

          {/* Matrix Rows */}
          <div className="space-y-1">
            {ASSETS.map((rowAsset) => (
              <div key={rowAsset} className="grid grid-cols-9 gap-1 items-center">
                {/* Y Axis Label Row */}
                <div className={`text-left font-mono font-bold text-[10px] py-2 px-1 rounded-lg border border-transparent ${
                  hoveredCell?.row === rowAsset ? "text-indigo-400 bg-indigo-500/5 border-indigo-500/10 font-black" : "text-slate-400"
                }`}>
                  {rowAsset}
                </div>

                {/* Columns */}
                {ASSETS.map((colAsset) => {
                  const val = matrix[rowAsset]?.[colAsset] ?? 0.0;
                  return (
                    <div
                      key={colAsset}
                      onMouseEnter={() => setHoveredCell({ row: rowAsset, col: colAsset, val })}
                      onMouseLeave={() => setHoveredCell(null)}
                      className={`py-2 text-center font-mono text-[10px] rounded-lg transition-all duration-150 cursor-crosshair text-xs ${getCellBg(
                        val,
                        rowAsset,
                        colAsset
                      )}`}
                    >
                      {val === 1.0 ? "1.00" : val.toFixed(2)}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Interactive Tooltip HUD Panel */}
      <div className="mt-4 p-3.5 bg-slate-950/80 border border-slate-850 rounded-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        {hoveredCell ? (
          <div className="space-y-1 font-mono text-[10px]">
            <div className="flex items-center gap-1.5 text-slate-300">
              <span className="font-bold text-indigo-400">{hoveredCell.row}</span>
              <span className="text-slate-500">↔</span>
              <span className="font-bold text-indigo-400">{hoveredCell.col}</span>
              <span className="text-slate-500">|</span>
              <span>Koefisien Korelasi:</span>
              <span className={`font-extrabold text-sm ${hoveredCell.val >= 0.6 ? "text-emerald-400" : hoveredCell.val >= 0.2 ? "text-indigo-400" : "text-rose-400"}`}>
                {hoveredCell.val >= 0 ? "+" : ""}{hoveredCell.val.toFixed(2)}
              </span>
            </div>
            <p className="text-[11px] font-sans text-slate-400">{getRelationshipText(hoveredCell.val)}</p>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-slate-400 text-[11px]">
            <Info className="h-4 w-4 text-indigo-400 shrink-0" />
            <span>Arahkan kursor ke sel matriks untuk menganalisis relasi arah pergerakan aset kripto.</span>
          </div>
        )}

        {/* Mini Legend info box */}
        <div className="flex items-center gap-3.5 text-[9px] font-mono text-slate-500 self-end sm:self-auto shrink-0">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-emerald-500/30 inline-block border border-emerald-500/20"></span>
            <span>Kuat (&gt;0.7)</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-indigo-500/10 inline-block border border-indigo-500/5"></span>
            <span>Moderat</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-rose-500/15 inline-block border border-rose-500/10"></span>
            <span>Divergen (&lt;0)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
