import React, { useState, useMemo } from "react";
import { Candlestick } from "../types";

interface CandleChartProps {
  candles: Candlestick[];
  symbol: string;
  interval: string;
}

export function CandleChart({ candles, symbol, interval }: CandleChartProps) {
  const [hoveredCandle, setHoveredCandle] = useState<Candlestick | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Calculate Simple Moving Averages (10 and 20 periods)
  const ma10 = useMemo(() => {
    return candles.map((_, idx) => {
      if (idx < 9) return null;
      const sum = candles.slice(idx - 9, idx + 1).reduce((acc, c) => acc + c.close, 0);
      return sum / 10;
    });
  }, [candles]);

  const ma20 = useMemo(() => {
    return candles.map((_, idx) => {
      if (idx < 19) return null;
      const sum = candles.slice(idx - 19, idx + 1).reduce((acc, c) => acc + c.close, 0);
      return sum / 20;
    });
  }, [candles]);

  // Calculate price boundaries for scaling the SVG
  const { minPrice, maxPrice, maxVolume } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    let maxVol = 0;

    if (candles && candles.length > 0) {
      candles.forEach((c) => {
        if (c.low < min) min = c.low;
        if (c.high > max) max = c.high;
        if (c.volume > maxVol) maxVol = c.volume;
      });
    }

    const pad = (max - min) * 0.05 || 1;
    return {
      minPrice: min === Infinity ? 0 : min - pad,
      maxPrice: max === -Infinity ? 100 : max + pad,
      maxVolume: maxVol || 1,
    };
  }, [candles]);

  // SVG Drawing dimensions
  const height = 300;
  const volumeHeight = 60;
  const width = 800;
  const paddingRight = 65;
  const paddingTop = 20;
  const paddingBottom = 30;

  const chartHeight = height - paddingTop - paddingBottom;
  const chartWidth = width - paddingRight;

const getX = (index: number) => {
  if (candles.length <= 1) return 10;
  return (index / (candles.length - 1)) * (chartWidth - 20) + 10;
};

  const getY = (price: number) => {
    return chartHeight - ((price - minPrice) / (maxPrice - minPrice)) * chartHeight + paddingTop;
  };

  const getVolY = (vol: number) => {
    const scale = vol / maxVolume;
    return height - scale * volumeHeight - 10;
  };

  // Grid prices (Y-axis labels)
  const yLabels = useMemo(() => {
    const diff = maxPrice - minPrice;
    return [
      minPrice + diff * 0.2,
      minPrice + diff * 0.5,
      minPrice + diff * 0.8,
    ];
  }, [minPrice, maxPrice]);

  if (!candles || candles.length === 0) {
    return (
      <div className="h-96 w-full flex items-center justify-center bg-slate-900 border border-slate-800 rounded-xl">
        <div className="text-center text-slate-400">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500 mx-auto mb-4"></div>
          <p>Mengambil data candle realtime dari Binance...</p>
        </div>
      </div>
    );
  }

  const activeCandle = hoveredCandle || candles[candles.length - 1];

  return (
    <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-5 shadow-2xl relative overflow-hidden group">
      {/* HUD Header */}
      <div className="flex flex-wrap justify-between items-center mb-4 gap-3">
        <div className="flex items-center gap-3">
          <span className="font-sans font-bold text-xl tracking-tight text-white bg-slate-800 px-3 py-1 rounded-lg border border-slate-700">
            {symbol.replace("USDT", "/USDT")}
          </span>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20 animate-pulse">
            LIVE FEED
          </span>
          <span className="text-xs text-slate-400 font-mono">Interval: {interval}</span>
        </div>

        {/* OHLCV metrics */}
        {activeCandle && (
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs font-mono bg-slate-950/80 p-2 rounded-lg border border-slate-800/50">
            <span className="text-slate-400">O: <span className={activeCandle.close >= activeCandle.open ? "text-emerald-400" : "text-red-400"}>${activeCandle.open.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span></span>
            <span className="text-slate-400">H: <span className="text-emerald-400">${activeCandle.high.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span></span>
            <span className="text-slate-400">L: <span className="text-red-400">${activeCandle.low.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span></span>
            <span className="text-slate-400">C: <span className={activeCandle.close >= activeCandle.open ? "text-emerald-400" : "text-red-400"}>${activeCandle.close.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span></span>
            <span className="text-slate-500 hidden sm:inline">Vol: <span className="text-slate-300">{activeCandle.volume.toLocaleString("en-US", { maximumFractionDigits: 2 })}</span></span>
          </div>
        )}
      </div>

      {/* Candlestick SVG Rendering */}
      <div className="relative w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto select-none overflow-visible"
          onMouseLeave={() => {
            setHoveredCandle(null);
            setHoveredIndex(null);
          }}
        >
          {/* Grid lines and price axis labels */}
          {yLabels.map((price, i) => (
            <g key={i}>
              <line
                x1="0"
                y1={getY(price)}
                x2={chartWidth}
                y2={getY(price)}
                stroke="#334155"
                strokeWidth="0.5"
                strokeDasharray="4 4"
              />
              <text
                x={chartWidth + 8}
                y={getY(price) + 4}
                fill="#64748b"
                className="text-[10px] font-mono"
              >
                ${price.toLocaleString("en-US", { maximumFractionDigits: 1 })}
              </text>
            </g>
          ))}

          {/* Time axis label grid lines */}
          {candles.map((c, idx) => {
            if (idx % Math.floor(candles.length / 5) === 0) {
              const date = new Date(c.time);
              const dateStr = interval.includes("d")
                ? date.toLocaleDateString("id-ID", { month: "short", day: "numeric" })
                : date.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
              return (
                <g key={idx}>
                  <line
                    x1={getX(idx)}
                    y1="10"
                    x2={getX(idx)}
                    y2={height - 25}
                    stroke="#1e293b"
                    strokeWidth="0.5"
                  />
                  <text
                    x={getX(idx) - 20}
                    y={height - 8}
                    fill="#475569"
                    className="text-[9px] font-mono"
                  >
                    {dateStr}
                  </text>
                </g>
              );
            }
            return null;
          })}

          {/* Render Volume Bars */}
          {candles.map((c, idx) => {
            const barWidth = Math.max(1, (chartWidth / candles.length) * 0.6);
            const x = getX(idx) - barWidth / 2;
            const y = getVolY(c.volume);
            const barHeight = height - 10 - y;
            const isBullish = c.close >= c.open;

            return (
              <rect
                key={`vol-${idx}`}
                x={x}
                y={y}
                width={barWidth}
                height={Math.max(1, barHeight)}
                fill={isBullish ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)"}
                stroke={isBullish ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}
                strokeWidth="0.5"
              />
            );
          })}

          {/* Technical Indicator Line: MA 10 */}
          <path
            d={candles
              .map((_, idx) => {
                const val = ma10[idx];
                return val ? `${idx === 9 ? "M" : "L"} ${getX(idx)} ${getY(val)}` : "";
              })
              .join(" ")}
            fill="none"
            stroke="#f59e0b"
            strokeWidth="1.5"
            strokeLinecap="round"
            opacity="0.85"
          />

          {/* Technical Indicator Line: MA 20 */}
          <path
            d={candles
              .map((_, idx) => {
                const val = ma20[idx];
                return val ? `${idx === 19 ? "M" : "L"} ${getX(idx)} ${getY(val)}` : "";
              })
              .join(" ")}
            fill="none"
            stroke="#06b6d4"
            strokeWidth="1.5"
            strokeLinecap="round"
            opacity="0.85"
          />

          {/* Candlesticks (Wicks & Bodies) */}
          {candles.map((c, idx) => {
            const x = getX(idx);
            const highY = getY(c.high);
            const lowY = getY(c.low);
            const openY = getY(c.open);
            const closeY = getY(c.close);

            const isBullish = c.close >= c.open;
            const bodyColor = isBullish ? "#10b981" : "#ef4444";
            const shadowColor = isBullish ? "rgba(16,185,129,0.4)" : "rgba(239,68,68,0.4)";

            const top = Math.min(openY, closeY);
            const bodyHeight = Math.max(1.5, Math.abs(openY - closeY));
            const barWidth = Math.max(2.5, (chartWidth / candles.length) * 0.7);

            return (
              <g key={`candle-${idx}`}>
                {/* Wick shadow */}
                <line
                  x1={x}
                  y1={highY}
                  x2={x}
                  y2={lowY}
                  stroke={bodyColor}
                  strokeWidth="1.2"
                  strokeLinecap="round"
                />

                {/* Candle body rect */}
                <rect
                  x={x - barWidth / 2}
                  y={top}
                  width={barWidth}
                  height={bodyHeight}
                  fill={bodyColor}
                  stroke={bodyColor}
                  strokeWidth="0.5"
                  rx="0.5"
                  style={{ filter: hoveredIndex === idx ? `drop-shadow(0px 0px 4px ${shadowColor})` : "none" }}
                />

                {/* Hover tracking columns */}
                <rect
                  x={x - (chartWidth / candles.length) / 2}
                  y="0"
                  width={chartWidth / candles.length}
                  height={height - 25}
                  fill="transparent"
                  className="cursor-crosshair"
                  onMouseEnter={() => {
                    setHoveredCandle(c);
                    setHoveredIndex(idx);
                  }}
                />
              </g>
            );
          })}

          {/* Hover Crosshair guides */}
          {hoveredIndex !== null && (
            <g>
              <line
                x1={getX(hoveredIndex)}
                y1="10"
                x2={getX(hoveredIndex)}
                y2={height - 25}
                stroke="#64748b"
                strokeWidth="0.8"
                strokeDasharray="3 3"
              />
              <line
                x1="0"
                y1={getY(candles[hoveredIndex].close)}
                x2={chartWidth}
                y2={getY(candles[hoveredIndex].close)}
                stroke="#64748b"
                strokeWidth="0.8"
                strokeDasharray="3 3"
              />
              <circle
                cx={getX(hoveredIndex)}
                cy={getY(candles[hoveredIndex].close)}
                r="4"
                fill="#38bdf8"
                stroke="#ffffff"
                strokeWidth="1.5"
              />
            </g>
          )}
        </svg>
      </div>

      {/* Legend Indicators */}
      <div className="flex gap-4 items-center mt-3 text-[10px] font-mono text-slate-500">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-[#f59e0b] inline-block"></span>
          <span>MA(10): ${candles.length > 10 && ma10[candles.length - 1] ? ma10[candles.length - 1]?.toFixed(2) : "Calculating..."}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-[#06b6d4] inline-block"></span>
          <span>MA(20): ${candles.length > 20 && ma20[candles.length - 1] ? ma20[candles.length - 1]?.toFixed(2) : "Calculating..."}</span>
        </div>
      </div>
    </div>
  );
}
