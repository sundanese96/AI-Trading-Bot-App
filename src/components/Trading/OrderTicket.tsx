import React, { useState } from "react";
import { PortfolioData } from "../../types";

interface Props {
  portfolio: PortfolioData;
  selectedCoin: string;
  liveCoinPrice: number;
  onOrderSuccess: () => void;
}

export function OrderTicket({ portfolio, selectedCoin, liveCoinPrice, onOrderSuccess }: Props) {
  const [orderType, setOrderType] = useState<"BUY" | "SELL">("BUY");
  const [orderSizeUSD, setOrderSizeUSD] = useState(1000);
  const [orderLeverage, setOrderLeverage] = useState(10);
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [trailingStopPct, setTrailingStopPct] = useState("");

  const [isSubmittingOrder, setIsSubmittingOrder] = useState(false);
  const [orderFeedback, setOrderFeedback] = useState({ text: "", isError: false });

  const handleExecuteOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingOrder(true);
    setOrderFeedback({ text: "", isError: false });

    try {
      const response = await fetch("/api/trade/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: selectedCoin,
          type: orderType,
          sizeUSD: orderSizeUSD,
          leverage: orderLeverage,
          sl: stopLoss || null,
          tp: takeProfit || null,
          trailingStopPct: trailingStopPct || null,
        }),
      });

      const resData = await response.json();
      if (response.ok) {
        setOrderFeedback({ text: "Order berhasil dieksekusi secara instan!", isError: false });
        setStopLoss("");
        setTakeProfit("");
        setTrailingStopPct("");
        onOrderSuccess();
      } else {
        setOrderFeedback({ text: resData.message || "Gagal mengeksekusi transaksi.", isError: true });
      }
    } catch (err: any) {
      setOrderFeedback({ text: err.message || "Gagal menghubungkan ke server.", isError: true });
    } finally {
      setIsSubmittingOrder(false);
    }
  };

  return (
    <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
      <div className="flex justify-between items-center mb-5 pb-3 border-b border-slate-850">
        <h3 className="font-sans font-extrabold text-base text-white">Tiket Margin Simulasi</h3>
        <span className="text-[10px] font-mono text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded border border-indigo-500/20">
          Sisa Saldo: ${portfolio.balanceUSD.toLocaleString("en-US", { maximumFractionDigits: 1 })}
        </span>
      </div>

      <form onSubmit={handleExecuteOrder} className="space-y-4 text-xs">
        {/* Order side selector */}
        <div className="grid grid-cols-2 gap-2 p-1 bg-slate-950 rounded-xl border border-slate-850">
          <button
            type="button"
            onClick={() => setOrderType("BUY")}
            className={`py-2 rounded-lg text-xs font-bold transition font-sans cursor-pointer ${
              orderType === "BUY" ? "bg-emerald-600 text-white shadow" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            LONG (BELI)
          </button>
          <button
            type="button"
            onClick={() => setOrderType("SELL")}
            className={`py-2 rounded-lg text-xs font-bold transition font-sans cursor-pointer ${
              orderType === "SELL" ? "bg-red-600 text-white shadow" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            SHORT (JUAL)
          </button>
        </div>

        {/* Leverage slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-[10px] font-mono text-slate-400">
            <span>LEVERAGE MARGIN</span>
            <span className="text-indigo-400 font-bold">{orderLeverage}x</span>
          </div>
          <input
            type="range"
            min="1"
            max="100"
            value={orderLeverage}
            onChange={(e) => setOrderLeverage(parseInt(e.target.value))}
            className="w-full h-1 bg-slate-850 rounded-lg appearance-none cursor-pointer accent-indigo-500"
          />
        </div>

        {/* Margin Collateral Size */}
        <div className="space-y-1.5">
          <label className="text-slate-400 font-mono">COLLATERAL MARGIN (USD)</label>
          <div className="relative">
            <span className="absolute left-3.5 top-2.5 text-slate-500 font-mono font-bold">$</span>
            <input
              type="number"
              min="10"
              value={orderSizeUSD}
              onChange={(e) => setOrderSizeUSD(Math.max(10, parseInt(e.target.value) || 0))}
              className="w-full bg-slate-950 border border-slate-850 focus:border-indigo-500 rounded-xl pl-8 pr-3 py-2.5 text-slate-200 outline-none font-mono font-bold"
            />
          </div>
          <p className="text-[9px] text-slate-500 font-mono">
            * Total Ukuran Posisi: <span className="text-white">${(orderSizeUSD * orderLeverage).toLocaleString()} USD</span> ({(orderSizeUSD * orderLeverage / liveCoinPrice).toFixed(4)} {selectedCoin.replace("USDT", "")})
          </p>
        </div>

        {/* Stop Loss & Take Profit limits setup */}
        <div className="grid grid-cols-2 gap-3 border-t border-slate-850/50 pt-3">
          <div className="space-y-1.5">
            <label className="text-slate-400 font-mono">STOP LOSS (HARGA)</label>
            <input
              type="number"
              placeholder="Contoh: 92000"
              value={stopLoss}
              onChange={(e) => setStopLoss(e.target.value)}
              className="w-full bg-slate-950 border border-slate-850 focus:border-indigo-500 rounded-xl px-3 py-2 text-slate-200 outline-none font-mono"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-slate-400 font-mono">TAKE PROFIT (HARGA)</label>
            <input
              type="number"
              placeholder="Contoh: 98000"
              value={takeProfit}
              onChange={(e) => setTakeProfit(e.target.value)}
              className="w-full bg-slate-950 border border-slate-850 focus:border-indigo-500 rounded-xl px-3 py-2 text-slate-200 outline-none font-mono"
            />
          </div>
        </div>

        {/* Trailing Stop configuration options */}
        <div className="space-y-1.5">
          <label className="text-slate-400 font-mono">TRAILING STOP (%)</label>
          <input
            type="number"
            step="0.1"
            placeholder="Contoh: 1.5 untuk 1.5%"
            value={trailingStopPct}
            onChange={(e) => setTrailingStopPct(e.target.value)}
            className="w-full bg-slate-950 border border-slate-850 focus:border-indigo-500 rounded-xl px-3 py-2 text-slate-200 outline-none font-mono"
          />
          <p className="text-[9px] text-slate-500 font-mono leading-relaxed">
            * Trailing Stop melacak harga secara otomatis dan melikuidasi posisi jika harga berbalik melawan Anda sebesar persentase ini.
          </p>
        </div>

        {/* Action feedback info */}
        {orderFeedback.text && (
          <div className={`p-3 rounded-xl text-[11px] leading-relaxed border ${orderFeedback.isError ? "bg-red-950/20 border-red-900/30 text-red-400" : "bg-emerald-950/20 border-emerald-900/30 text-emerald-400"}`}>
            {orderFeedback.text}
          </div>
        )}

        {/* Execute Button */}
        <button
          type="submit"
          disabled={isSubmittingOrder}
          className={`w-full font-sans font-bold text-white py-3 px-4 rounded-xl active:scale-[0.98] transition cursor-pointer shadow-lg ${
            orderType === "BUY"
              ? "bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-emerald-600/10"
              : "bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 shadow-red-600/10"
          }`}
        >
          {isSubmittingOrder ? "Memproses Margin..." : `Buka Posisi ${orderType === "BUY" ? "LONG" : "SHORT"}`}
        </button>
      </form>
    </div>
  );
}
