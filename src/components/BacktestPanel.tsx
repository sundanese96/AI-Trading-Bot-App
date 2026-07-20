import React, { useState } from "react";
import { BacktestParams, BacktestResult } from "../types";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip as ChartTooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { Play, TrendingUp, BarChart4, Award, ShieldAlert, FileSpreadsheet } from "lucide-react";

interface BacktestPanelProps {
  onRunBacktest: (params: BacktestParams) => Promise<BacktestResult>;
}

export function BacktestPanel({ onRunBacktest }: BacktestPanelProps) {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [strategy, setStrategy] = useState<BacktestParams["strategy"]>("SMA_CROSS");
  const [interval, setIntervalVal] = useState<"1h" | "1d">("1d");
  const [startingBalance, setStartingBalance] = useState(10000);
  const [leverage, setLeverage] = useState(10);
  const [stopLossPct, setStopLossPct] = useState(2);
  const [takeProfitPct, setTakeProfitPct] = useState(6);

  // Strategy specific state
  const [smaShort, setSmaShort] = useState(10);
  const [smaLong, setSmaLong] = useState(30);
  const [rsiOversold, setRsiOversold] = useState(30);
  const [rsiOverbought, setRsiOverbought] = useState(70);

  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const handleExecute = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage("");
    try {
      const params: BacktestParams = {
        symbol,
        strategy,
        interval,
        startingBalance,
        leverage,
        stopLossPct,
        takeProfitPct,
        smaShort,
        smaLong,
        rsiOversold,
        rsiOverbought,
      };
      const report = await onRunBacktest(params);
      setResult(report);
    } catch (err: any) {
      setErrorMessage(err.message || "Gagal memproses backtesting.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Configuration Box & Strategy Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Form Parameter Config */}
        <div className="lg:col-span-1 bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl">
          <h3 className="font-sans font-bold text-lg text-white mb-4 flex items-center gap-2">
            <BarChart4 className="h-5 w-5 text-indigo-400" />
            Parameter Backtester
          </h3>

          <form onSubmit={handleExecute} className="space-y-6 text-xs text-slate-300">
            {/* Target & Strategy Grid */}
            <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-850 space-y-4">
              <span className="font-mono text-slate-200 font-bold flex items-center gap-1.5 border-b border-slate-850 pb-2">
                <BarChart4 className="h-4 w-4 text-indigo-400" />
                TARGET & STRATEGI SIMULASI
              </span>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-slate-400 font-mono text-[10px]">ASET KRIPTO</label>
                  <select
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono font-bold text-white"
                  >
                    <option value="BTCUSDT">BTC/USDT</option>
                    <option value="ETHUSDT">ETH/USDT</option>
                    <option value="SOLUSDT">SOL/USDT</option>
                    <option value="BNBUSDT">BNB/USDT</option>
                    <option value="XRPUSDT">XRP/USDT</option>
                    <option value="ADAUSDT">ADA/USDT</option>
                    <option value="DOGEUSDT">DOGE/USDT</option>
                    <option value="DOTUSDT">DOT/USDT</option>
                    <option value="SHIBUSDT">SHIB/USDT</option>
                    <option value="LTCUSDT">LTC/USDT</option>
                    <option value="LINKUSDT">LINK/USDT</option>
                    <option value="NEARUSDT">NEAR/USDT</option>
                    <option value="SUIUSDT">SUI/USDT</option>
                  </select>
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-slate-400 font-mono text-[10px]">STRATEGI FORMULA</label>
                  <select
                    value={strategy}
                    onChange={(e) => setStrategy(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-sans font-bold text-white text-xs"
                  >
                    <option disabled className="text-slate-500 bg-slate-900">--- Indikator Teknikal Murni ---</option>
                    <option value="SMA_CROSS">SMA Crossover (Golden/Death Cross)</option>
                    <option value="RSI_REVERSAL">RSI Reversal (Oversold/Overbought)</option>
                    <option value="MACD_CROSS">MACD Line/Signal Crossover</option>
                    <option value="BOLLINGER_REVERSION">Bollinger Bands Mean Reversion</option>
                    <option disabled className="text-slate-500 bg-slate-900 mt-2">--- AI Bot Equivalents ---</option>
                    <option value="CONSERVATIVE">🛡️ CONSERVATIVE (Hati-Hati)</option>
                    <option value="SCALPING">⚡ SCALPING (Cepat)</option>
                    <option value="SWING">📈 SWING (Tren Jangka Panjang)</option>
                    <option value="AGGRESSIVE">🔥 AGGRESSIVE (Agresif & Sensitif)</option>
                    <option value="MARTINGALE">🔄 MARTINGALE (Averaging Down)</option>
                    <option value="HEDGING">🔒 HEDGING (Posisi Dua Arah)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Financial & Risk Parameters */}
            <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-850 space-y-4">
              <span className="font-mono text-slate-200 font-bold flex items-center gap-1.5 border-b border-slate-850 pb-2">
                <ShieldAlert className="h-4 w-4 text-rose-400" />
                MANAJEMEN KEUANGAN & RISIKO
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-slate-400 font-mono text-[10px]">SALDO AWAL (USD)</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={startingBalance}
                      onChange={(e) => setStartingBalance(Math.max(100, parseInt(e.target.value) || 0))}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
                    />
                    <span className="text-slate-500 font-mono text-xs">USDT</span>
                  </div>
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-slate-400 font-mono text-[10px]">LEVERAGE (DAYA UNGKIT)</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="1"
                      max="125"
                      value={leverage}
                      onChange={(e) => setLeverage(parseInt(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
                    />
                    <span className="text-slate-400 font-mono text-xs">x</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-slate-400 font-mono text-[10px]">STOP LOSS (%)</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      step="0.1"
                      value={stopLossPct}
                      onChange={(e) => setStopLossPct(Math.max(0, parseFloat(e.target.value) || 0))}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
                    />
                    <span className="text-slate-500 font-mono text-xs">%</span>
                  </div>
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-slate-400 font-mono text-[10px]">TAKE PROFIT (%)</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      step="0.1"
                      value={takeProfitPct}
                      onChange={(e) => setTakeProfitPct(Math.max(0, parseFloat(e.target.value) || 0))}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 outline-none font-mono text-white"
                    />
                    <span className="text-slate-500 font-mono text-xs">%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Technical Strategy Parameters */}
            <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-850 space-y-4">
              <span className="font-mono text-slate-200 font-bold flex items-center gap-1.5 border-b border-slate-850 pb-2">
                <TrendingUp className="h-4 w-4 text-emerald-400" />
                PARAMETER INDIKATOR TEKNIKAL
              </span>

              <div className="space-y-1.5">
                <label className="text-slate-400 font-mono text-[10px]">TIMEFRAME INTERVAL</label>
                <select
                  value={interval}
                  onChange={(e) => setIntervalVal(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-3 py-2.5 outline-none font-sans font-bold text-white text-sm"
                >
                  <option value="1h">1 Jam (Hourly - Standar Day Trading)</option>
                  <option value="1d">1 Hari (Daily - Standar Swing Trading)</option>
                </select>
              </div>

              {strategy === "SMA_CROSS" && (
                <div className="grid grid-cols-2 gap-4 border-t border-slate-850/50 pt-3">
                  <div className="space-y-1.5">
                    <label className="text-amber-500 font-mono text-[10px]">SMA SHORT PERIOD</label>
                    <input
                      type="number"
                      value={smaShort}
                      onChange={(e) => setSmaShort(Math.max(2, parseInt(e.target.value) || 10))}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 rounded-xl px-3 py-2.5 text-white outline-none font-mono"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-amber-500 font-mono text-[10px]">SMA LONG PERIOD</label>
                    <input
                      type="number"
                      value={smaLong}
                      onChange={(e) => setSmaLong(Math.max(5, parseInt(e.target.value) || 30))}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 rounded-xl px-3 py-2.5 text-white outline-none font-mono"
                    />
                  </div>
                </div>
              )}

              {strategy === "RSI_REVERSAL" && (
                <div className="grid grid-cols-2 gap-4 border-t border-slate-850/50 pt-3">
                  <div className="space-y-1.5">
                    <label className="text-cyan-400 font-mono text-[10px]">RSI OVERSOLD</label>
                    <input
                      type="number"
                      value={rsiOversold}
                      onChange={(e) => setRsiOversold(Math.max(5, parseInt(e.target.value) || 30))}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2.5 text-white outline-none font-mono"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-cyan-400 font-mono text-[10px]">RSI OVERBOUGHT</label>
                    <input
                      type="number"
                      value={rsiOverbought}
                      onChange={(e) => setRsiOverbought(Math.max(50, parseInt(e.target.value) || 70))}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2.5 text-white outline-none font-mono"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Error Message */}
            {errorMessage && (
              <div className="p-3 bg-red-950/20 border border-red-900/30 rounded-xl text-red-400 text-[11px] leading-relaxed flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 shrink-0" />
                {errorMessage}
              </div>
            )}

            {/* Execute Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 px-4 rounded-xl flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50 transition cursor-pointer font-sans shadow-lg shadow-indigo-600/10"
            >
              <Play className={`h-4.5 w-4.5 ${isLoading ? "animate-pulse" : ""}`} />
              {isLoading ? "Mengunduh & Backtesting..." : "Jalankan Backtest Simulasi"}
            </button>
          </form>
        </div>

        {/* Right Dashboard Area (Displays results of the backtest) */}
        <div className="lg:col-span-2 space-y-6">
          {!result ? (
            <div className="h-full bg-slate-900/30 border border-slate-850 rounded-2xl p-8 flex flex-col justify-center items-center text-center">
              <BarChart4 className="h-14 w-14 text-slate-700 mb-3" />
              <h4 className="font-sans font-bold text-slate-400 text-lg">Siap Melakukan Simulasi</h4>
              <p className="text-slate-500 max-w-sm mt-1 text-sm leading-relaxed">
                Tentukan parameter perdagangan Anda di sebelah kiri, lalu jalankan strategi backtesting untuk mengukur profitabilitas formula perdagangan pada data Binance historis asli.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Performance Grid Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {/* Metric 1: Final Balance */}
                <div className="bg-slate-900/60 border border-slate-800/80 p-4 rounded-2xl">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Saldo Akhir</p>
                  <p className="text-xl font-mono font-bold text-white mt-1">
                    ${result.finalBalance.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </p>
                  <p className={`text-[10px] font-mono mt-1 font-bold ${result.totalProfitUSD >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {result.totalProfitUSD >= 0 ? "▲" : "▼"} {result.totalProfitPct.toFixed(2)}%
                  </p>
                </div>

                {/* Metric 2: Win Rate */}
                <div className="bg-slate-900/60 border border-slate-800/80 p-4 rounded-2xl">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Akurasi Win Rate</p>
                  <p className="text-xl font-mono font-bold text-white mt-1">{result.winRate}%</p>
                  <p className="text-[10px] font-mono text-slate-400 mt-1">
                    {result.winningTrades} Menang / {result.totalTrades} Transaksi
                  </p>
                </div>

                {/* Metric 3: Max Drawdown */}
                <div className="bg-slate-900/60 border border-slate-800/80 p-4 rounded-2xl">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Max Drawdown</p>
                  <p className="text-xl font-mono font-bold text-amber-500 mt-1">{result.maxDrawdown}%</p>
                  <p className="text-[10px] font-mono text-slate-400 mt-1">Toleransi Risiko Puncak</p>
                </div>

                {/* Metric 4: Profit Factor */}
                <div className="bg-slate-900/60 border border-slate-800/80 p-4 rounded-2xl">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Profit Factor</p>
                  <p className="text-xl font-mono font-bold text-white mt-1">{result.profitFactor}</p>
                  <p className="text-[10px] font-mono text-slate-400 mt-1">
                    {result.profitFactor >= 1.5 ? "Sangat Efisien" : "Kinerja Rata-rata"}
                  </p>
                </div>
              </div>

              {/* Balance Equity Curve Recharts Graph */}
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-2xl space-y-4">
                <div className="flex justify-between items-center">
                  <h4 className="font-sans font-bold text-white text-base">Grafik Pertumbuhan Equity Portofolio</h4>
                  <span className="text-[10px] font-mono text-slate-400 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-850">
                    Sumbu X: Garis Waktu Candlestick historis
                  </span>
                </div>

                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={result.equityCurve}>
                      <defs>
                        <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="time" stroke="#475569" fontSize={9} tickLine={false} />
                      <YAxis
                        stroke="#475569"
                        fontSize={9}
                        tickLine={false}
                        domain={["auto", "auto"]}
                        tickFormatter={(v) => `$${v.toLocaleString()}`}
                      />
                      <ChartTooltip
                        contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", borderRadius: "8px" }}
                        labelStyle={{ color: "#94a3b8", fontFamily: "monospace", fontSize: 10 }}
                        itemStyle={{ color: "#ffffff", fontFamily: "monospace", fontSize: 11 }}
                        formatter={(val) => [`$${parseFloat(val as string).toLocaleString()}`, "Saldo USD"]}
                      />
                      <Area
                        type="monotone"
                        dataKey="balance"
                        stroke="#6366f1"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorBalance)"
                        name="Saldo Portofolio"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Trade Logs Details Table */}
      {result && result.trades.length > 0 && (
        <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/60 rounded-2xl p-6 shadow-2xl">
          <h4 className="font-sans font-bold text-white text-base mb-4 flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-indigo-400" />
            Laporan Transaksi Historis Perdagangan ({result.trades.length})
          </h4>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300 border-collapse">
              <thead>
                <tr className="border-b border-slate-800/80 text-slate-400 uppercase text-[10px] font-mono">
                  <th className="py-3 px-4"># ID</th>
                  <th className="py-3 px-4">Aksi</th>
                  <th className="py-3 px-4">Harga Entry</th>
                  <th className="py-3 px-4">Harga Keluar</th>
                  <th className="py-3 px-4">PnL Realisasi</th>
                  <th className="py-3 px-4">Persentase</th>
                  <th className="py-3 px-4">Pemicu Keluar</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/30 font-mono">
                {result.trades.map((trade, idx) => {
                  const isGain = trade.pnlUSD >= 0;
                  return (
                    <tr key={trade.id} className="hover:bg-slate-800/20 transition">
                      <td className="py-3.5 px-4 text-slate-500">bt-{idx + 1}</td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded font-bold text-[9px] ${trade.type === "LONG" ? "text-emerald-400 bg-emerald-500/10" : "text-amber-400 bg-amber-500/10"}`}>
                          {trade.type}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">${trade.entryPrice.toLocaleString()}</td>
                      <td className="py-3.5 px-4">${trade.exitPrice.toLocaleString()}</td>
                      <td className={`py-3.5 px-4 font-bold ${isGain ? "text-emerald-400" : "text-red-400"}`}>
                        {isGain ? "+" : ""}${trade.pnlUSD.toLocaleString()}
                      </td>
                      <td className={`py-3.5 px-4 font-bold ${isGain ? "text-emerald-400" : "text-red-400"}`}>
                        {isGain ? "+" : ""}{trade.pnlPct.toFixed(2)}%
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] ${
                          trade.exitReason === "STOP_LOSS"
                            ? "bg-red-500/10 text-red-400"
                            : trade.exitReason === "TAKE_PROFIT"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : "bg-slate-800 text-slate-300"
                        }`}>
                          {trade.exitReason}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
