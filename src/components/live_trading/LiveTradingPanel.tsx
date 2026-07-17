import React, { useState, useEffect } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity, 
  Compass, 
  Trash2, 
  AlertTriangle, 
  Cpu, 
  Layers, 
  RefreshCw, 
  XCircle,
  HelpCircle,
  ShieldAlert
} from "lucide-react";

interface Position {
  symbol: string;
  positionAmt: number;
  entryPrice: number;
  markPrice: number;
  unrealizedProfit: number;
  leverage: number;
  liquidationPrice: number;
  positionSide: string;
  marginType: string;
}

interface OpenOrder {
  orderId: number;
  symbol: string;
  status: string;
  price: number;
  origQty: number;
  executedQty: number;
  type: string;
  side: string;
  stopPrice: number;
  time: number;
  positionSide: string;
}

interface AccountInfo {
  walletBalance: number;
  availableBalance: number;
  marginBalance: number;
  unrealizedProfit: number;
  marginRatio: number;
}

interface LiveTradingPanelProps {
  lang: "ID" | "EN";
  selectedCoin: string;
  active?: boolean;
}

export function LiveTradingPanel({ lang, selectedCoin, active }: LiveTradingPanelProps) {
  const [configChecked, setConfigChecked] = useState(false);
  const [hasCredentials, setHasCredentials] = useState(false);
  
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [orders, setOrders] = useState<OpenOrder[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  
  // Execution Form States
  const [symbol, setSymbol] = useState(selectedCoin.replace("USDT", ""));
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("MARKET");
  const [quantity, setQuantity] = useState<number>(0.01);
  const [limitPrice, setLimitPrice] = useState<number>(0.0);
  const [leverage, setLeverage] = useState<number>(5);
  const [stopLossPct, setStopLossPct] = useState<string>("");
  const [takeProfitPct, setTakeProfitPct] = useState<string>("");
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionFeedback, setActionFeedback] = useState({ text: "", isError: false });

  // 1. Check credentials
  const checkConfig = async () => {
    try {
      const res = await fetch("/api/ai/config");
      if (res.ok) {
        const config = await res.json();
        const hasKeys = !!(config.binanceApiKey && config.binanceApiSecret);
        setHasCredentials(hasKeys);
        if (config.dryRun === false && hasKeys) {
          // If live mode is selected in settings, default symbol and details accordingly
        }
      }
    } catch (e) {
      console.error("Gagal memeriksa konfigurasi Binance:", e);
    } finally {
      setConfigChecked(true);
    }
  };

  // 2. Fetch live Binance data
  const fetchLiveTradingData = async () => {
    if (!hasCredentials) return;
    try {
      // Account
      const accRes = await fetch("/api/live-trading/account");
      if (accRes.ok) {
        const accData = await accRes.json();
        setAccount(accData);
      }
      
      // Positions
      const posRes = await fetch("/api/live-trading/positions");
      if (posRes.ok) {
        const posData = await posRes.json();
        setPositions(posData);
      }
      
      // Orders
      const ordRes = await fetch("/api/live-trading/orders");
      if (ordRes.ok) {
        const ordData = await ordRes.json();
        setOrders(ordData);
      }
      
      setErrorMsg("");
    } catch (e: any) {
      console.error("Error fetching live Binance data:", e);
      setErrorMsg(lang === "ID" ? "Gagal memuat data Binance API. Periksa internet atau koneksi API Key." : "Failed to load Binance API data. Check internet or API Key connection.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (active) {
      checkConfig();
    }
  }, [active]);

  useEffect(() => {
    if (hasCredentials && active) {
      fetchLiveTradingData();
      const interval = setInterval(fetchLiveTradingData, 3000);
      return () => clearInterval(interval);
    } else if (!hasCredentials) {
      setLoading(false);
    }
  }, [hasCredentials, active]);

  // Handle Order Submit
  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setActionFeedback({ text: "", isError: false });

    try {
      const payload = {
        symbol: symbol,
        side: side,
        positionSide: "BOTH",
        orderType: orderType,
        quantity: quantity,
        leverage: leverage,
        stopLossPct: stopLossPct ? parseFloat(stopLossPct) : null,
        takeProfitPct: takeProfitPct ? parseFloat(takeProfitPct) : null,
      };

      const res = await fetch("/api/live-trading/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok) {
        setActionFeedback({
          text: lang === "ID" ? "Order Live berhasil ditempatkan ke akun Binance!" : "Live order successfully placed to Binance account!",
          isError: false,
        });
        fetchLiveTradingData();
      } else {
        setActionFeedback({ text: data.detail || "Gagal menempatkan order.", isError: true });
      }
    } catch (err: any) {
      setActionFeedback({ text: err.message || "Kesalahan koneksi saat submit order.", isError: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Cancel Order
  const handleCancelOrder = async (targetSymbol: string, orderId: number) => {
    if (!window.confirm(lang === "ID" ? `Batal order #${orderId}?` : `Cancel order #${orderId}?`)) return;
    try {
      const res = await fetch("/api/live-trading/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: targetSymbol, orderId }),
      });
      if (res.ok) {
        fetchLiveTradingData();
      } else {
        const data = await res.json();
        alert(data.detail || "Gagal membatalkan order.");
      }
    } catch (err: any) {
      alert(err.message || "Gagal membatalkan order.");
    }
  };

  // Handle Close Position
  const handleClosePosition = async (targetSymbol: string, posSide: string, amt: number, positionSide: string) => {
    if (!window.confirm(lang === "ID" ? `Tutup paksa posisi ${targetSymbol} dengan harga MARKET?` : `Force close position ${targetSymbol} with MARKET price?`)) return;
    try {
      const res = await fetch("/api/live-trading/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: targetSymbol, side: posSide, quantity: amt, positionSide }),
      });
      if (res.ok) {
        fetchLiveTradingData();
      } else {
        const data = await res.json();
        alert(data.detail || "Gagal menutup posisi.");
      }
    } catch (err: any) {
      alert(err.message || "Gagal menutup posisi.");
    }
  };

  const t = {
    title: lang === "ID" ? "Live Trading Terminal (Binance)" : "Live Trading Terminal (Binance)",
    desc: lang === "ID" ? "Terminal perdagangan riil terhubung ke akun Binance Futures Anda dengan proteksi risiko berlapis." : "Real-time trading terminal connected directly to your Binance Futures account with multi-layered risk guards.",
    noCredsTitle: lang === "ID" ? "Koneksi API Binance Belum Aktif" : "Binance API Connection Inactive",
    noCredsDesc: lang === "ID" ? "Untuk melakukan live trading nyata, Anda harus memasukkan Binance API Key dan API Secret di tab Pengaturan terlebih dahulu, lalu matikan mode simulasi." : "To execute real live trades, you must first input your Binance API Key and API Secret in the Settings tab, and disable simulation mode.",
    goToSettings: lang === "ID" ? "Buka Pengaturan Koneksi" : "Open Connection Settings",
    walletBal: lang === "ID" ? "Saldo Dompet" : "Wallet Balance",
    marginBal: lang === "ID" ? "Saldo Margin" : "Margin Balance",
    availBal: lang === "ID" ? "Saldo Tersedia" : "Available Balance",
    unrealPnL: lang === "ID" ? "PnL Mengambang" : "Floating PnL",
    orderTicket: lang === "ID" ? "Tiket Eksekusi Live" : "Live Execution Ticket",
    activePositions: lang === "ID" ? "Posisi Aktif Riil" : "Real Active Positions",
    openOrders: lang === "ID" ? "Antrean Order Aktif" : "Active Open Orders",
    leverageClamped: lang === "ID" ? "Leverage Maks 10x untuk proteksi risiko" : "Leverage clamped to 10x for risk protection",
  };

  if (!configChecked || loading) {
    return (
      <div className="py-12 flex flex-col items-center justify-center gap-2 font-mono">
        <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
        <span className="text-xs text-slate-500 uppercase tracking-widest animate-pulse">
          {lang === "ID" ? "MENGHUBUNGKAN KE BINANCE FUTURES..." : "CONNECTING TO BINANCE FUTURES..."}
        </span>
      </div>
    );
  }

  if (!hasCredentials) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 max-w-2xl mx-auto shadow-2xl text-center space-y-6 my-10">
        <div className="mx-auto w-12 h-12 bg-amber-500/10 rounded-full flex items-center justify-center border border-amber-500/20 text-amber-400">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-bold text-white">{t.noCredsTitle}</h3>
          <p className="text-xs text-slate-400 leading-relaxed font-mono">
            {t.noCredsDesc}
          </p>
        </div>
        <div className="p-4 bg-slate-950/50 border border-slate-850 rounded-xl space-y-2.5 text-left text-[11px] font-mono text-slate-500 leading-relaxed">
          <p className="font-bold text-slate-400">⚠️ Catatan Keamanan Penting:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>API Key disimpan terenkripsi dengan algoritma AES-128 di penyimpanan lokal.</li>
            <li>Sistem membatasi leverage maksimal **10x** dan margin maksimal **$100** per order demi keamanan modal Anda.</li>
            <li>Sistem memiliki **Circuit Breaker** otomatis yang mengunci bot jika batas rugi harian terlewati.</li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/40 p-4 border border-slate-850 rounded-xl">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            {t.title}
          </h2>
          <p className="text-[11px] text-slate-500 font-mono">{t.desc}</p>
        </div>
        
        {/* Status indicator */}
        <div className="flex items-center gap-3">
          <span className="text-[9px] font-mono text-white/30 uppercase bg-emerald-950/30 border border-emerald-900/30 px-2 py-0.5 rounded">
            Live Endpoint Connected
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-950/20 border border-red-900/30 text-red-400 text-xs font-mono rounded-xl">
          ⚠️ {errorMsg}
        </div>
      )}

      {/* Account Balance Metrics Card */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Wallet Balance */}
        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl shadow-inner relative overflow-hidden group">
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">{t.walletBal}</div>
          <div className="text-lg font-black text-white mt-1 font-mono">
            ${account ? account.walletBalance.toLocaleString(undefined, { minimumFractionDigits: 2 }) : "0.00"}
          </div>
          <DollarSign className="absolute right-2 top-2 h-7 w-7 text-slate-800/40 group-hover:text-slate-700/40 transition-colors" />
        </div>

        {/* Margin Balance */}
        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl shadow-inner relative overflow-hidden group">
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">{t.marginBal}</div>
          <div className="text-lg font-black text-white mt-1 font-mono">
            ${account ? account.marginBalance.toLocaleString(undefined, { minimumFractionDigits: 2 }) : "0.00"}
          </div>
          <Layers className="absolute right-2 top-2 h-7 w-7 text-slate-800/40 group-hover:text-slate-700/40 transition-colors" />
        </div>

        {/* Available Balance */}
        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl shadow-inner relative overflow-hidden group">
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">{t.availBal}</div>
          <div className="text-lg font-black text-indigo-400 mt-1 font-mono">
            ${account ? account.availableBalance.toLocaleString(undefined, { minimumFractionDigits: 2 }) : "0.00"}
          </div>
          <Compass className="absolute right-2 top-2 h-7 w-7 text-slate-800/40 group-hover:text-slate-700/40 transition-colors" />
        </div>

        {/* Floating PnL */}
        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl shadow-inner relative overflow-hidden group">
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">{t.unrealPnL}</div>
          <div className={`text-lg font-black mt-1 font-mono flex items-center gap-1 ${
            account && account.unrealizedProfit > 0 
              ? "text-emerald-400" 
              : account && account.unrealizedProfit < 0 
              ? "text-red-400" 
              : "text-white"
          }`}>
            {account && account.unrealizedProfit > 0 ? "+" : ""}
            ${account ? account.unrealizedProfit.toLocaleString(undefined, { minimumFractionDigits: 2 }) : "0.00"}
            {account && account.unrealizedProfit !== 0 && (
              account.unrealizedProfit > 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />
            )}
          </div>
          <Activity className="absolute right-2 top-2 h-7 w-7 text-slate-800/40 group-hover:text-slate-700/40 transition-colors" />
        </div>
      </div>

      {/* Main Grid: Ticket vs List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Execution Ticket (1 col) */}
        <div className="lg:col-span-1 bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl shadow-xl space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-850 pb-3">
            <Cpu className="h-4 w-4 text-indigo-400" />
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">{t.orderTicket}</h3>
          </div>

          <form onSubmit={handlePlaceOrder} className="space-y-4 text-xs font-mono">
            {/* Symbol dropdown */}
            <div className="space-y-1">
              <label className="text-slate-500 uppercase font-bold">Aset Target</label>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-200 outline-none"
              >
                <option value="BTC">BTC / USDT</option>
                <option value="ETH">ETH / USDT</option>
                <option value="SOL">SOL / USDT</option>
                <option value="XRP">XRP / USDT</option>
              </select>
            </div>

            {/* Side Toggle */}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setSide("BUY")}
                className={`py-2 rounded-xl font-bold uppercase transition ${
                  side === "BUY" 
                    ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/10" 
                    : "bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                Buy / Long
              </button>
              <button
                type="button"
                onClick={() => setSide("SELL")}
                className={`py-2 rounded-xl font-bold uppercase transition ${
                  side === "SELL" 
                    ? "bg-red-600 text-white shadow-lg shadow-red-600/10" 
                    : "bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                Sell / Short
              </button>
            </div>

            {/* Order Type */}
            <div className="space-y-1">
              <label className="text-slate-500 uppercase font-bold">Tipe Order</label>
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value as any)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-200 outline-none"
              >
                <option value="MARKET">MARKET</option>
                <option value="LIMIT">LIMIT</option>
              </select>
            </div>

            {/* Price (visible for Limit) */}
            {orderType === "LIMIT" && (
              <div className="space-y-1">
                <label className="text-slate-500 uppercase font-bold">Harga Batas (USDT)</label>
                <input
                  type="number"
                  step="0.01"
                  value={limitPrice}
                  onChange={(e) => setLimitPrice(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-200 outline-none"
                />
              </div>
            )}

            {/* Quantity */}
            <div className="space-y-1">
              <label className="text-slate-500 uppercase font-bold">Kuantitas Kontrak ({symbol})</label>
              <input
                type="number"
                step="0.001"
                min="0.001"
                value={quantity}
                onChange={(e) => setQuantity(parseFloat(e.target.value) || 0.001)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-200 outline-none"
              />
            </div>

            {/* Leverage Slider */}
            <div className="space-y-1.5 bg-slate-950/55 p-3 rounded-xl border border-slate-850">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-400 font-bold">LEVERAGE: {leverage}x</span>
                <span className="text-red-500/70 text-[9px] font-mono uppercase">{t.leverageClamped}</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={leverage}
                onChange={(e) => setLeverage(parseInt(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
            </div>

            {/* Stop Loss & Take Profit Bracket (Optional) */}
            <div className="grid grid-cols-2 gap-3.5">
              <div className="space-y-1">
                <label className="text-slate-500 uppercase font-bold">Stop Loss (%)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="Contoh: 1.5"
                  value={stopLossPct}
                  onChange={(e) => setStopLossPct(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-200 outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-slate-500 uppercase font-bold">Take Profit (%)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="Contoh: 3.0"
                  value={takeProfitPct}
                  onChange={(e) => setTakeProfitPct(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-200 outline-none"
                />
              </div>
            </div>

            {actionFeedback.text && (
              <div className={`p-3 rounded-xl border text-[11px] font-sans leading-relaxed ${
                actionFeedback.isError
                  ? "bg-red-950/20 border-red-900/30 text-red-400"
                  : "bg-emerald-950/20 border-emerald-900/30 text-emerald-400"
              }`}>
                {actionFeedback.text}
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting || quantity <= 0}
              className="w-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2 transition active:scale-95 disabled:opacity-40 cursor-pointer shadow-lg shadow-orange-600/10 font-sans uppercase"
            >
              <AlertTriangle className="h-4 w-4 animate-pulse" />
              {isSubmitting ? "Memproses Order..." : "Kirim Order Real Binance"}
            </button>
          </form>
        </div>

        {/* Positions & Orders Display (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Active Positions */}
          <div className="bg-slate-900/40 border border-slate-850 p-5 rounded-2xl shadow-xl space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-850 pb-3">
              <Activity className="h-4 w-4 text-emerald-400" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">{t.activePositions} ({positions.length})</h3>
            </div>

            {positions.length === 0 ? (
              <p className="text-xs text-slate-500 font-mono py-4">Tidak ada posisi terbuka di akun Binance Futures saat ini.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-500 uppercase text-[9px] font-mono">
                      <th className="py-2.5 px-2">Aset</th>
                      <th className="py-2.5 px-2">Arah</th>
                      <th className="py-2.5 px-2">Leverage</th>
                      <th className="py-2.5 px-2">Kuantitas</th>
                      <th className="py-2.5 px-2">Entry</th>
                      <th className="py-2.5 px-2">Mark Price</th>
                      <th className="py-2.5 px-2">Unrealized PNL</th>
                      <th className="py-2.5 px-2 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850 font-mono">
                    {positions.map((pos) => {
                      const isLong = pos.positionAmt > 0;
                      const pnlPositive = pos.unrealizedProfit >= 0;
                      return (
                        <tr key={pos.symbol} className="hover:bg-slate-800/10 transition">
                          <td className="py-3 px-2 text-white font-extrabold">{pos.symbol}</td>
                          <td className="py-3 px-2">
                            <span className={`px-1.5 py-0.5 rounded font-bold text-[9px] ${
                              isLong ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                            }`}>
                              {isLong ? "LONG" : "SHORT"}
                            </span>
                          </td>
                          <td className="py-3 px-2 text-slate-400">{pos.leverage}x</td>
                          <td className="py-3 px-2 text-slate-300">{Math.abs(pos.positionAmt)}</td>
                          <td className="py-3 px-2 text-slate-400">${pos.entryPrice.toLocaleString()}</td>
                          <td className="py-3 px-2 text-slate-400">${pos.markPrice.toLocaleString()}</td>
                          <td className={`py-3 px-2 font-bold ${pnlPositive ? "text-emerald-400" : "text-red-400"}`}>
                            {pnlPositive ? "+" : ""}${pos.unrealizedProfit.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          <td className="py-3 px-2 text-right">
                            <button
                              onClick={() => handleClosePosition(pos.symbol, isLong ? "BUY" : "SELL", Math.abs(pos.positionAmt), pos.positionSide)}
                              className="px-2.5 py-1 bg-red-600/10 border border-red-500/20 text-red-400 hover:bg-red-600 hover:text-white rounded transition text-[10px] uppercase font-sans font-bold flex items-center gap-1 ml-auto"
                            >
                              <XCircle className="h-3 w-3" />
                              Tutup
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Open Orders */}
          <div className="bg-slate-900/40 border border-slate-850 p-5 rounded-2xl shadow-xl space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-850 pb-3">
              <Layers className="h-4 w-4 text-indigo-400" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">{t.openOrders} ({orders.length})</h3>
            </div>

            {orders.length === 0 ? (
              <p className="text-xs text-slate-500 font-mono py-4">Tidak ada order antrean aktif di Binance Futures saat ini.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-500 uppercase text-[9px] font-mono">
                      <th className="py-2.5 px-2">ID</th>
                      <th className="py-2.5 px-2">Aset</th>
                      <th className="py-2.5 px-2">Tipe</th>
                      <th className="py-2.5 px-2">Arah</th>
                      <th className="py-2.5 px-2">Jumlah</th>
                      <th className="py-2.5 px-2">Harga</th>
                      <th className="py-2.5 px-2">Trigger</th>
                      <th className="py-2.5 px-2 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850 font-mono">
                    {orders.map((ord) => {
                      const isBuy = ord.side === "BUY";
                      return (
                        <tr key={ord.orderId} className="hover:bg-slate-800/10 transition text-slate-300">
                          <td className="py-3 px-2 text-slate-500 text-[10px]">#{ord.orderId}</td>
                          <td className="py-3 px-2 text-white font-extrabold">{ord.symbol}</td>
                          <td className="py-3 px-2 text-slate-400 text-[10px]">{ord.type}</td>
                          <td className="py-3 px-2">
                            <span className={`px-1.5 py-0.5 rounded font-bold text-[9px] ${
                              isBuy ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                            }`}>
                              {ord.side}
                            </span>
                          </td>
                          <td className="py-3 px-2 text-slate-350">{ord.origQty}</td>
                          <td className="py-3 px-2 text-slate-350">${ord.price > 0 ? ord.price.toLocaleString() : "-"}</td>
                          <td className="py-3 px-2 text-yellow-500/80 font-bold">${ord.stopPrice > 0 ? ord.stopPrice.toLocaleString() : "-"}</td>
                          <td className="py-3 px-2 text-right">
                            <button
                              onClick={() => handleCancelOrder(ord.symbol, ord.orderId)}
                              className="px-2 py-1 bg-slate-800 border border-slate-700 text-slate-400 hover:bg-slate-700 hover:text-white rounded transition text-[10px] flex items-center gap-1 ml-auto"
                            >
                              <Trash2 className="h-3 w-3" />
                              Batal
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
}
