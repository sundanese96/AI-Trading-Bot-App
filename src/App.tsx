import React, { useState, useEffect, useCallback } from "react";
import {
  TrendingUp,
  Newspaper,
  Cpu,
  Bell,
  History,
  DollarSign,
  Coins,
  Percent,
  ArrowUpRight,
  ArrowDownRight,
  Scale,
  RefreshCw,
  Sliders,
  XCircle,
  Info,
  ShieldAlert,
  Bot,
  Activity,
  LogOut,
  HelpCircle,
} from "lucide-react";

import { PortfolioData, TradePosition, NewsArticle, MacroEvent, MLModel, NotificationSettings, NotificationLog, Candlestick, BacktestParams, LlmSettings } from "./types";
import { CandleChart } from "./components/CandleChart";
import { NewsPanel } from "./components/NewsPanel";
import { BacktestPanel } from "./components/BacktestPanel";
import { MLPanel } from "./components/MLPanel";
import { SettingsPanel } from "./components/Settings/SettingsPanel";
import { AIBotPanel } from "./components/AIBot/AIBotPanel";
import { DocsPanel } from "./components/DocsPanel";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { CorrelationMatrix } from "./components/CorrelationMatrix";
import { CryptoTicker } from "./components/CryptoTicker";
import { Navbar } from "./components/Layout/Navbar";
import { PortfolioWidget } from "./components/Trading/PortfolioWidget";
import { OrderTicket } from "./components/Trading/OrderTicket";

import { LiveTradingPanel } from "./components/live_trading/LiveTradingPanel";
import { LoginScreen } from "./components/LoginScreen";


export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState<"TRADING" | "NEWS" | "BACKTEST" | "ML" | "AI_BOT" | "SETTINGS" | "LIVE" | "DOCS">("TRADING");

  // Tab Visit Flags to lazy-mount tabs and keep them persistently mounted once visited
  const [visitedTabs, setVisitedTabs] = useState<Set<string>>(new Set(["TRADING"]));

  useEffect(() => {
    setVisitedTabs((prev) => {
      const newSet = new Set(prev);
      newSet.add(activeTab);
      return newSet;
    });
  }, [activeTab]);


  // Market & Candlestick Feed States
  const [selectedCoin, setSelectedCoin] = useState("BTCUSDT");
  const [selectedInterval, setSelectedInterval] = useState("1m");
  const [candles, setCandles] = useState<Candlestick[]>([]);
  const [livePrices, setLivePrices] = useState<{ [symbol: string]: number }>({});

  // Account Portfolio & Trading Log States
  const [portfolio, setPortfolio] = useState<PortfolioData>({ balanceUSD: 100000, assets: {}, initialBalance: 100000 });
  const [trades, setTrades] = useState<TradePosition[]>([]);
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [macroEvents, setMacroEvents] = useState<MacroEvent[]>([]);
  const [mlModels, setMlModels] = useState<MLModel[]>([]);
  const [settings, setSettings] = useState<NotificationSettings>({
    telegramToken: "",
    telegramChatId: "",
    emailAddress: "",
    tradeExecuted: true,
    riskTriggered: true,
    highSentimentAlert: true,
  });
  const [llmSettings, setLlmSettings] = useState<LlmSettings>({
    provider: "simulated",
    apiKey: "",
    baseUrl: "",
    modelName: "",
  });
  const [notifLogs, setNotifLogs] = useState<NotificationLog[]>([]);

  const [isLoadingNews, setIsLoadingNews] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [confirmLogout, setConfirmLogout] = useState(false);

  // Check session status on mount and intercept fetch requests for 401 redirection
  useEffect(() => {
    // Intercept fetch to redirect on 401 Unauthorized globally
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      const response = await originalFetch(...args);
      if (response.status === 401) {
        const url = typeof args[0] === "string" ? args[0] : ((args[0] as any).url || (args[0] as any).href || String(args[0]));
        if (url && !url.includes("/api/login") && !url.includes("/api/auth/status")) {
          setIsAuthenticated(false);
        }
      }
      return response;
    };

    const checkAuthStatus = async () => {
      try {
        const res = await fetch("/api/auth/status");
        if (res.ok) {
          const data = await res.json();
          setIsAuthenticated(!!data.authenticated);
        } else {
          setIsAuthenticated(false);
        }
      } catch (err) {
        setIsAuthenticated(false);
      }
    };
    checkAuthStatus();

    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  // Synchronize Backend Wallet Balance, Active Trades, News Logs, and Notification setups
  const fetchBackendState = useCallback(async () => {
    try {
      const pRes = await fetch("/api/portfolio");
      if (pRes.ok) {
        const pData = await pRes.json();
        setPortfolio(pData.portfolio);
        setLivePrices(pData.currentPrices);
      }

      const tRes = await fetch("/api/trades");
      if (tRes.ok) {
        const tData = await tRes.json();
        let safeTrades = Array.isArray(tData) ? tData : (tData.trades || []);
        safeTrades = safeTrades.map((t: any) => ({
          ...t,
          symbol: t.symbol || t.targetAsset || "UNKNOWN"
        }));
        setTrades(safeTrades);
      }
    } catch (e) {
      console.error("Gagal sinkronisasi data dengan backend server:", e);
    }
  }, []);

  const fetchInitialSettings = useCallback(async () => {
    try {
      const nRes = await fetch("/api/notifications/settings");
      if (nRes.ok) {
        const nData = await nRes.json();
        setSettings(nData.settings);
        setNotifLogs(nData.logs);
      }

      const llmRes = await fetch("/api/llm/settings");
      if (llmRes.ok) {
        const llmData = await llmRes.json();
        setLlmSettings(llmData.settings);
      }

      const mlRes = await fetch("/api/ml/models");
      if (mlRes.ok) {
        const mlData = await mlRes.json();
        setMlModels(mlData.models);
      }
    } catch (e) {
      console.error("Gagal sinkronisasi data dengan backend server:", e);
    }
  }, []);

  // Fetch real-time Candlesticks from Binance API directly for low latency
  const fetchBinanceCandles = useCallback(async () => {
    try {
      const response = await fetch(
        `https://api.binance.com/api/v3/klines?symbol=${selectedCoin}&interval=${selectedInterval}&limit=80`
      );
      if (response.ok) {
        const data = await response.json();
        if (!Array.isArray(data)) {
          console.error("Invalid Binance response", data);
          return;
        }
        const parsed: Candlestick[] = data.map((k: any) => ({
          time: k[0],
          open: parseFloat(k[1]),
          high: parseFloat(k[2]),
          low: parseFloat(k[3]),
          close: parseFloat(k[4]),
          volume: parseFloat(k[5]),
        }));
        setCandles(parsed);

        // Update current coin price
        if (parsed.length > 0) {
          const lastClose = parsed[parsed.length - 1].close;
          setLivePrices((prev) => ({ ...prev, [selectedCoin]: lastClose }));
        }
      }
    } catch (e) {
      console.error("Gagal memuat candle Binance:", e);
    }
  }, [selectedCoin, selectedInterval]);

  // Periodic Polling synchronization loops
  useEffect(() => {
    if (isAuthenticated !== true) return;
    
    // Initial fetch for settings that rarely change
    fetchInitialSettings();

    fetchBackendState();
    fetchBinanceCandles();

    // Fast interval for live rates and backend sync
    const fastSync = setInterval(() => {
      fetchBackendState();
    }, 4000);

    // Medium interval for candlestick bars update
    const candleSync = setInterval(() => {
      fetchBinanceCandles();
    }, 10000);

    return () => {
      clearInterval(fastSync);
      clearInterval(candleSync);
    };
  }, [isAuthenticated, fetchBackendState, fetchBinanceCandles, fetchInitialSettings]);

  // Sync news logs once on mount
  useEffect(() => {
    if (isAuthenticated !== true) return;
    const fetchNews = async () => {
      try {
        const response = await fetch("/api/news");
        if (response.ok) {
          const data = await response.json();
          setNews(data.news || []);
          if (data.macroEvents) {
            setMacroEvents(data.macroEvents);
          }
        }
      } catch (err) {
        console.error("Gagal inisialisasi news feed:", err);
      }
    };
    fetchNews();
  }, [isAuthenticated]);

  const handleClosePosition = async (tradeId: string) => {
    try {
      const response = await fetch("/api/trade/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tradeId }),
      });

      if (!response.ok) {
        try {
          const resData = await response.json();
          alert(resData.message || "Gagal melikuidasi posisi.");
        } catch {
          alert("Server error. Cek log backend.");
        }
        return;
      }

      const resData = await response.json();
      if (resData.success) {
        fetchBackendState();
      } else {
        alert(resData.message || "Gagal melikuidasi posisi.");
      }
    } catch (e: any) {
      console.error("Error closing position manual:", e);
      alert("Error: " + e.message);
    }
  };

  // Handler: Scrape fresh news trigger
  const handleRefreshNewsFeed = async () => {
    setIsLoadingNews(true);
    try {
      const response = await fetch("/api/news?refresh=true");
      if (response.ok) {
        const data = await response.json();
        setNews(data.news);
        if (data.macroEvents) {
          setMacroEvents(data.macroEvents);
        }
      }
    } catch (e) {
      console.error("News Refresh Error:", e);
    } finally {
      setIsLoadingNews(false);
    }
  };

  // Handler: Backtest strategies integration
  const handleRunStrategyBacktest = async (params: BacktestParams) => {
    const response = await fetch("/api/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    if (!response.ok) {
      const resData = await response.json();
      throw new Error(resData.message || "Gagal menjalankan pengujian backtest.");
    }
    const data = await response.json();
    return data.report;
  };

// Handler: Local Machine Learning Training
  const handleTrainLocalMLModel = async (params: {
    learningRate: number;
    epochs: number;
    features: string[];
    symbol: string;
    modelType?: string;
  }) => {
    const response = await fetch("/api/ml/train", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.message || "Gagal melatih model lokal.");
    }
    const resData = await response.json();
    fetchBackendState(); // sync models list
    return resData.result;
  };

  // Handler: Request Gemini Strategic Adviser Forecast
  const handleRequestAIForecast = async (params: {
    symbol: string;
    rsi: number;
    macd: { line: number; signal: number; histogram: number };
    sentimentScore: number;
  }) => {
    const response = await fetch("/api/gemini/forecast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.message || "Gagal memproses analisis kecerdasan.");
    }
    const resData = await response.json();
    return resData.advisory;
  };

  // Handler: Save Notification Settings
  const handleSaveNotificationSettings = async (payload: NotificationSettings) => {
    const response = await fetch("/api/notifications/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (response.ok) {
      fetchBackendState();
      return true;
    }
    return false;
  };

  // Handler: Save LLM settings
  const handleSaveLlmSettings = async (payload: LlmSettings) => {
    const response = await fetch("/api/llm/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (response.ok) {
      fetchBackendState();
      return true;
    }
    return false;
  };

  // Handler: Dispatch Test Alert Channels
  const handleTriggerTestAlert = async () => {
    const response = await fetch("/api/notifications/test", { method: "POST" });
    if (response.ok) {
      fetchBackendState();
      return true;
    }
    return false;
  };

  // Handler: Logout process
  const handleLogout = async () => {
    try {
      await fetch("/api/logout", { method: "POST" });
    } catch (err) {
      console.error("Gagal logout:", err);
    }
    setIsAuthenticated(false);
  };

  // Handler: Reset Account Balance
  const handleResetPortfolio = async () => {
    try {
      const response = await fetch("/api/portfolio/reset", { method: "POST" });
      if (response.ok) {
        fetchBackendState();
        setConfirmReset(false);
      } else {
        try {
          const resData = await response.json();
          alert(resData.message || "Gagal mereset portofolio.");
        } catch {
          alert("Server error. Cek log backend.");
        }
        setConfirmReset(false);
      }
    } catch (err) {
      console.error(err);
      alert("Error: " + err.message);
      setConfirmReset(false);
    }
  };

  // State calculations for balance metrics HUD
  const liveCoinPrice = livePrices[selectedCoin] || 0;

  const { openPositions, completedTrades } = React.useMemo(() => {
    const safeTrades = Array.isArray(trades) ? trades : [];
    return {
      openPositions: safeTrades.filter((t) => t.status === "OPEN"),
      completedTrades: safeTrades.filter((t) => t.status === "CLOSED"),
    };
  }, [trades]);

  // Calculate Unrealized PnL (fluctuating based on live tickers!)
  const totalUnrealizedPnlUSD = React.useMemo(() => {
    return openPositions.reduce((sum, pos) => {
      const entryPrice = Number(pos.entryPrice) || 0;
      const size = Number(pos.size) || 0;
      if (entryPrice === 0 || size === 0) return sum; // prevent NaN/Infinity
      
      const symbol = pos.symbol || pos.targetAsset || "UNKNOWN";
      const currentPrice = Number(livePrices[symbol]) || entryPrice;
      
      const priceDiff = pos.type === "BUY" ? currentPrice - entryPrice : entryPrice - currentPrice;
      const rawReturn = priceDiff / entryPrice;
      const fee = size * entryPrice * 0.001;
      const pnl = rawReturn * (size * entryPrice) - fee; // no double-leverage
      
      return sum + (isNaN(pnl) ? 0 : pnl);
    }, 0);
  }, [openPositions, livePrices]);

  const accountNetWorthUSD = (Number(portfolio.balanceUSD) || 0) + totalUnrealizedPnlUSD;
  const initialBalance = Number(portfolio.initialBalance) || 1; // prevent division by zero
  const netWorthReturnPct = ((accountNetWorthUSD - initialBalance) / initialBalance) * 100;

  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center flex-col gap-4 font-sans text-slate-200">
        <div className="relative w-12 h-12">
          <div className="absolute inset-0 rounded-full border-4 border-slate-800"></div>
          <div className="absolute inset-0 rounded-full border-4 border-t-indigo-500 animate-spin"></div>
        </div>
        <p className="text-sm font-medium tracking-wider text-slate-400 animate-pulse">Memeriksa Sesi...</p>
      </div>
    );
  }

  if (isAuthenticated === false) {
    return <LoginScreen onLoginSuccess={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500/35 selection:text-white">
      {/* Sticky Header Wrapper */}
      <header className="sticky top-0 z-40 flex flex-col">
        <Navbar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab as any} 
          onResetPortfolio={handleResetPortfolio} 
          onLogout={handleLogout} 
        />
        <CryptoTicker
          selectedCoin={selectedCoin}
          onSelectCoin={(coin) => {
            setSelectedCoin(coin);
            setActiveTab("TRADING");
          }}
        />
      </header>

      {/* 2. LIVE WALLET METRICS OVERVIEW (HUD) */}
      <PortfolioWidget 
        portfolio={portfolio}
        accountNetWorthUSD={accountNetWorthUSD}
        totalUnrealizedPnlUSD={totalUnrealizedPnlUSD}
        netWorthReturnPct={netWorthReturnPct}
      />

      {/* 3. CORE SUBPANEL VIEWS ROUTING */}
      <main className="flex-1 p-6">
        <ErrorBoundary fallbackTitle="Dashboard Utama Gagal Memuat" onReset={() => setActiveTab("TRADING")}>
          <div style={{ display: activeTab === "TRADING" ? "block" : "none" }}>
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Left/Middle Column (Chart and Positions Table) */}
            <div className="xl:col-span-2 space-y-6">
              {/* Asset quick settings switcher */}
              <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/30 border border-slate-850 p-4 rounded-2xl">
                <div className="flex items-center gap-2 flex-wrap">
                  {["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"].map((coin) => (
                    <button
                      key={coin}
                      onClick={() => setSelectedCoin(coin)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold cursor-pointer transition ${
                        selectedCoin === coin
                          ? "bg-indigo-600 text-white border border-indigo-500 shadow-md shadow-indigo-600/10"
                          : "bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700"
                      }`}
                    >
                      {coin.replace("USDT", "")}
                    </button>
                  ))}

                  <span className="text-slate-700 mx-1">|</span>

                  <select
                    value={["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"].includes(selectedCoin) ? "" : selectedCoin}
                    onChange={(e) => {
                      if (e.target.value) setSelectedCoin(e.target.value);
                    }}
                    className="bg-slate-950 border border-slate-850 focus:border-indigo-500 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 outline-none font-mono font-bold"
                  >
                    <option value="" disabled>Lainnya (Top 50 Koin)...</option>
                    {[
                      { value: "AAVEUSDT", label: "AAVE" },
                      { value: "ADAUSDT", label: "ADA" },
                      { value: "ALGOUSDT", label: "ALGO" },
                      { value: "APTUSDT", label: "APT" },
                      { value: "ARBUSDT", label: "ARB" },
                      { value: "ATOMUSDT", label: "ATOM" },
                      { value: "AVAXUSDT", label: "AVAX" },
                      { value: "BCHUSDT", label: "BCH" },
                      { value: "BONKUSDT", label: "BONK" },
                      { value: "DOGEUSDT", label: "DOGE" },
                      { value: "DOTUSDT", label: "DOT" },
                      { value: "EGLDUSDT", label: "EGLD" },
                      { value: "ETCUSDT", label: "ETC" },
                      { value: "FETUSDT", label: "FET" },
                      { value: "FILUSDT", label: "FIL" },
                      { value: "FLOKIUSDT", label: "FLOKI" },
                      { value: "FLOWUSDT", label: "FLOW" },
                      { value: "FTMUSDT", label: "FTM" },
                      { value: "GRTUSDT", label: "GRT" },
                      { value: "HBARUSDT", label: "HBAR" },
                      { value: "ICPUSDT", label: "ICP" },
                      { value: "IMXUSDT", label: "IMX" },
                      { value: "INJUSDT", label: "INJ" },
                      { value: "JUPUSDT", label: "JUP" },
                      { value: "LDOUSDT", label: "LDO" },
                      { value: "LINKUSDT", label: "LINK" },
                      { value: "LTCUSDT", label: "LTC" },
                      { value: "MKRUSDT", label: "MKR" },
                      { value: "NEARUSDT", label: "NEAR" },
                      { value: "OPUSDT", label: "OP" },
                      { value: "PEPEUSDT", label: "PEPE" },
                      { value: "PYTHUSDT", label: "PYTH" },
                      { value: "RENDERUSDT", label: "RENDER" },
                      { value: "RUNEUSDT", label: "RUNE" },
                      { value: "SEIUSDT", label: "SEI" },
                      { value: "SHIBUSDT", label: "SHIB" },
                      { value: "STXUSDT", label: "STX" },
                      { value: "SUIUSDT", label: "SUI" },
                      { value: "THETAUSDT", label: "THETA" },
                      { value: "TONUSDT", label: "TON" },
                      { value: "TRXUSDT", label: "TRX" },
                      { value: "UNIUSDT", label: "UNI" },
                      { value: "VETUSDT", label: "VET" },
                      { value: "WIFUSDT", label: "WIF" }
                    ].map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label} ({(livePrices[opt.value] || 0) > 1 ? `$${(livePrices[opt.value] || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : `$${livePrices[opt.value] || 0}`})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-mono text-slate-500 mr-1.5">BAR TIME:</span>
                  {["1m", "5m", "1h", "1d"].map((iVal) => (
                    <button
                      key={iVal}
                      onClick={() => setSelectedInterval(iVal)}
                      className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold cursor-pointer transition ${
                        selectedInterval === iVal
                          ? "bg-slate-800 text-indigo-400 border border-slate-700"
                          : "text-slate-500 hover:text-slate-300"
                      }`}
                    >
                      {iVal}
                    </button>
                  ))}
                </div>
              </div>

              {/* Candlestick visualization */}
              <ErrorBoundary fallbackTitle="Visualisasi Lilin (Candlestick) Gagal Memuat">
                <CandleChart candles={candles} symbol={selectedCoin} interval={selectedInterval} />
              </ErrorBoundary>

              {/* BTC-Altcoin Price Correlation Matrix */}
              <ErrorBoundary fallbackTitle="Matriks Korelasi Harga Gagal Memuat">
                <CorrelationMatrix />
              </ErrorBoundary>

              {/* Open Leverage Positions Table */}
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-2xl">
                <h3 className="font-sans font-bold text-base text-white mb-4 flex items-center gap-2">
                  <Sliders className="h-5 w-5 text-indigo-400" />
                  Posisi Margin Perdagangan Aktif ({openPositions.length})
                </h3>

                {openPositions.length === 0 ? (
                  <div className="text-center text-slate-500 py-10 border border-dashed border-slate-850 rounded-xl bg-slate-950/20">
                    <Info className="h-8 w-8 text-slate-750 mx-auto mb-2" />
                    <p className="text-xs">Tidak ada posisi perdagangan aktif saat ini.</p>
                    <p className="text-[10px] text-slate-600 mt-1 font-mono">Tentukan parameter margin dan buka posisi LONG atau SHORT pada widget samping.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left text-slate-300 border-collapse">
                      <thead>
                        <tr className="border-b border-slate-800/80 text-slate-500 uppercase text-[9px] font-mono">
                          <th className="py-2.5 px-3">Aset</th>
                          <th className="py-2.5 px-3">Tipe</th>
                          <th className="py-2.5 px-3">Leverage</th>
                          <th className="py-2.5 px-3">Harga Entry</th>
                          <th className="py-2.5 px-3">Harga Ticker</th>
                          <th className="py-2.5 px-3">Stop Loss</th>
                          <th className="py-2.5 px-3">Take Profit</th>
                          <th className="py-2.5 px-3">Floating P&L</th>
                          <th className="py-2.5 px-3 text-right">Aksi</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-850 font-mono">
                        {openPositions.map((pos) => {
                          const currentPrice = livePrices[pos.symbol] || pos.entryPrice;
                          const priceDiff = pos.type === "BUY" ? currentPrice - pos.entryPrice : pos.entryPrice - currentPrice;
                          const rawReturn = priceDiff / pos.entryPrice;
                          const fee = pos.size * pos.entryPrice * 0.001;
                          const pnl = rawReturn * (pos.size * pos.entryPrice) - fee; // no double-leverage
                          const marginUsed = (pos.size * pos.entryPrice) / pos.leverage; // undo leverage
                          const pnlPct = (pnl / marginUsed) * 100;
                          const isBullish = pnl >= 0;

                          return (
                            <tr key={pos.id} className="hover:bg-slate-800/10 transition">
                              <td className="py-3 px-3 font-bold text-white">{pos.symbol.replace("USDT", "")}</td>
                              <td className="py-3 px-3">
                                <span className={`px-1.5 py-0.5 rounded text-[9px] font-extrabold ${pos.type === "BUY" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                                  {pos.type === "BUY" ? "LONG" : "SHORT"}
                                </span>
                              </td>
                              <td className="py-3 px-3 text-slate-400">{pos.leverage}x</td>
                              <td className="py-3 px-3 text-slate-400">${pos.entryPrice.toLocaleString()}</td>
                              <td className="py-3 px-3 text-slate-300 animate-pulse">${currentPrice.toLocaleString()}</td>
                              <td className="py-3 px-3 text-red-400/80">${pos.sl ? pos.sl.toLocaleString() : "-"}</td>
                              <td className="py-3 px-3 text-emerald-400/80">${pos.tp ? pos.tp.toLocaleString() : "-"}</td>
                              <td className={`py-3 px-3 font-bold ${isBullish ? "text-emerald-400" : "text-red-400"}`}>
                                {isBullish ? "+" : ""}${pnl.toFixed(2)} ({isBullish ? "+" : ""}{pnlPct.toFixed(2)}%)
                              </td>
                              <td className="py-3 px-3 text-right">
                                <button
                                  onClick={() => handleClosePosition(pos.id)}
                                  className="text-[10px] font-sans font-bold bg-red-950/20 hover:bg-red-500 text-red-400 hover:text-white border border-red-900/30 rounded-lg px-2.5 py-1 transition cursor-pointer"
                                >
                                  Close
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

            {/* Right Column (Leverage Ticket Console) */}
            <div className="xl:col-span-1 space-y-6">
              <OrderTicket 
                portfolio={portfolio} 
                selectedCoin={selectedCoin} 
                liveCoinPrice={livePrices[selectedCoin] || 1} 
                onOrderSuccess={fetchBackendState} 
              />

              {/* Completed closed trades summary history box */}
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-2xl space-y-4">
                <h4 className="font-sans font-bold text-sm text-white flex items-center gap-2">
                  <History className="h-4 w-4 text-indigo-400" />
                  Riwayat Perdagangan Tertutup ({completedTrades.length})
                </h4>

                {completedTrades.length === 0 ? (
                  <p className="text-xs text-slate-500 font-mono text-center py-6">Belum ada riwayat perdagangan virtual.</p>
                ) : (
                  <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
                    {completedTrades.slice(0, 10).map((hist) => {
                      const isGain = (hist.pnl || 0) >= 0;
                      return (
                        <div key={hist.id} className="bg-slate-950/50 border border-slate-850 p-3 rounded-xl flex justify-between items-center text-[10px] font-mono">
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span className="font-sans font-bold text-slate-300">{hist.symbol.replace("USDT", "")}</span>
                              <span className={`px-1 rounded text-[8px] font-extrabold ${hist.type === "BUY" ? "text-emerald-400 bg-emerald-500/10" : "text-red-400 bg-red-500/10"}`}>
                                {hist.type === "BUY" ? "LONG" : "SHORT"}
                              </span>
                            </div>
                            <p className="text-slate-500 mt-0.5">Keluar: {hist.reason || "MANUAL"}</p>
                          </div>
                          <div className="text-right">
                            <p className={`font-bold ${isGain ? "text-emerald-400" : "text-red-400"}`}>
                              {isGain ? "+" : ""}${hist.pnl?.toLocaleString()}
                            </p>
                            <p className="text-[9px] text-slate-500">{new Date(hist.exitTimestamp || hist.timestamp).toLocaleTimeString("id-ID")}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
          </div>

          {visitedTabs.has("NEWS") && (
            <div style={{ display: activeTab === "NEWS" ? "block" : "none" }}>
              <NewsPanel
                news={news}
                macroEvents={macroEvents}
                onRefreshNews={handleRefreshNewsFeed}
                isLoading={isLoadingNews}
              />
            </div>
          )}

          {visitedTabs.has("BACKTEST") && (
            <div style={{ display: activeTab === "BACKTEST" ? "block" : "none" }}>
              <BacktestPanel onRunBacktest={handleRunStrategyBacktest} />
            </div>
          )}

          {visitedTabs.has("ML") && (
            <div style={{ display: activeTab === "ML" ? "block" : "none" }}>
              <MLPanel
                onTrainModel={handleTrainLocalMLModel}
                onGetForecast={handleRequestAIForecast}
                savedModels={mlModels}
              />
            </div>
          )}

          {visitedTabs.has("AI_BOT") && (
            <div style={{ display: activeTab === "AI_BOT" ? "block" : "none" }}>
              <AIBotPanel
                savedModels={mlModels}
                llmSettings={llmSettings}
                active={activeTab === "AI_BOT"}
              />
            </div>
          )}

          {visitedTabs.has("SETTINGS") && (
            <div style={{ display: activeTab === "SETTINGS" ? "block" : "none" }}>
              <SettingsPanel
                settings={settings}
                logs={notifLogs}
                onSaveSettings={handleSaveNotificationSettings}
                onTriggerTest={handleTriggerTestAlert}
                llmSettings={llmSettings}
                onSaveLlmSettings={handleSaveLlmSettings}
              />
            </div>
          )}

          {visitedTabs.has("LIVE") && (
            <div style={{ display: activeTab === "LIVE" ? "block" : "none" }}>
              <LiveTradingPanel
                lang="ID"
                selectedCoin={selectedCoin}
                active={activeTab === "LIVE"}
              />
            </div>
          )}

          {visitedTabs.has("DOCS") && (
            <div style={{ display: activeTab === "DOCS" ? "block" : "none" }}>
              <DocsPanel />
            </div>
          )}
        </ErrorBoundary>
      </main>
    </div>
  );
}
