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
import { SettingsPanel } from "./components/SettingsPanel";
import { AIBotPanel } from "./components/AIBotPanel";
import { DocsPanel } from "./components/DocsPanel";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { CorrelationMatrix } from "./components/CorrelationMatrix";
import { CryptoTicker } from "./components/CryptoTicker";


import { LiveTradingPanel } from "./components/live_trading/LiveTradingPanel";
import { LoginScreen } from "./components/LoginScreen";


export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState<"TRADING" | "NEWS" | "BACKTEST" | "ML" | "AI_BOT" | "SETTINGS" | "LIVE" | "DOCS">("TRADING");

  // Tab Visit Flags to lazy-mount tabs and keep them persistently mounted once visited
  const [newsVisited, setNewsVisited] = useState(false);
  const [backtestVisited, setBacktestVisited] = useState(false);
  const [mlVisited, setMlVisited] = useState(false);
  const [aiBotVisited, setAiBotVisited] = useState(false);
  const [settingsVisited, setSettingsVisited] = useState(false);
  const [liveVisited, setLiveVisited] = useState(false);
  const [docsVisited, setDocsVisited] = useState(false);

  useEffect(() => {
    if (activeTab === "NEWS") setNewsVisited(true);
    if (activeTab === "BACKTEST") setBacktestVisited(true);
    if (activeTab === "ML") setMlVisited(true);
    if (activeTab === "AI_BOT") setAiBotVisited(true);
    if (activeTab === "SETTINGS") setSettingsVisited(true);
    if (activeTab === "LIVE") setLiveVisited(true);
    if (activeTab === "DOCS") setDocsVisited(true);
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

  // Order Ticket Widget State
  const [orderType, setOrderType] = useState<"BUY" | "SELL">("BUY");
  const [orderSizeUSD, setOrderSizeUSD] = useState(1000);
  const [orderLeverage, setOrderLeverage] = useState(10);
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [trailingStopPct, setTrailingStopPct] = useState("");

  const [isSubmittingOrder, setIsSubmittingOrder] = useState(false);
  const [orderFeedback, setOrderFeedback] = useState({ text: "", isError: false });

  const [isLoadingNews, setIsLoadingNews] = useState(false);

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
        setTrades(tData.trades);
      }

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
  }, [isAuthenticated, fetchBackendState, fetchBinanceCandles]);

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

  // Handler: Execute new simulated trading position
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
        fetchBackendState();
      } else {
        setOrderFeedback({ text: resData.message || "Gagal mengeksekusi transaksi.", isError: true });
      }
    } catch (err: any) {
      setOrderFeedback({ text: err.message || "Gagal menghubungkan ke server.", isError: true });
    } finally {
      setIsSubmittingOrder(false);
    }
  };

  const handleClosePosition = async (tradeId: string) => {
    try {
      const response = await fetch("/api/trade/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tradeId }),
      });
      if (response.ok) {
        const resData = await response.json();
        if (resData.success) {
          fetchBackendState();
        } else {
          alert(resData.message || "Gagal melikuidasi posisi.");
        }
      } else {
        const resData = await response.json();
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

  // Handler: Logout Session
  const handleLogout = async () => {
    if (window.confirm("Apakah Anda yakin ingin keluar dari terminal?")) {
      try {
        await fetch("/api/logout", { method: "POST" });
      } catch (err) {
        console.error("Gagal logout:", err);
      }
      setIsAuthenticated(false);
    }
  };

  // Handler: Reset Account Balance
  const handleResetPortfolio = async () => {
    if (window.confirm("Apakah Anda yakin ingin mengatur ulang portofolio kembali ke saldo demo awal $100.000 USD? Semua riwayat posisi akan dibersihkan.")) {
      try {
        const response = await fetch("/api/portfolio/reset", { method: "POST" });
        if (response.ok) {
          fetchBackendState();
          alert("Portofolio direset berhasil.");
        }
      } catch (err) {
        console.error(err);
      }
    }
  };

  // State calculations for balance metrics HUD
  const liveCoinPrice = livePrices[selectedCoin] || 0;

  const { openPositions, completedTrades } = React.useMemo(() => {
    return {
      openPositions: trades.filter((t) => t.status === "OPEN"),
      completedTrades: trades.filter((t) => t.status === "CLOSED"),
    };
  }, [trades]);

  // Calculate Unrealized PnL (fluctuating based on live tickers!)
  const totalUnrealizedPnlUSD = React.useMemo(() => {
    return openPositions.reduce((sum, pos) => {
      const currentPrice = livePrices[pos.symbol] || pos.entryPrice;
      const priceDiff = pos.type === "BUY" ? currentPrice - pos.entryPrice : pos.entryPrice - currentPrice;
      const rawReturn = priceDiff / pos.entryPrice;
      const fee = pos.size * pos.entryPrice * 0.001;
      const pnl = rawReturn * (pos.size * pos.entryPrice) - fee; // no double-leverage
      return sum + pnl;
    }, 0);
  }, [openPositions, livePrices]);

  const accountNetWorthUSD = portfolio.balanceUSD + totalUnrealizedPnlUSD;
  const netWorthReturnPct = ((accountNetWorthUSD - portfolio.initialBalance) / portfolio.initialBalance) * 100;

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
        {/* 1. TOP PREMIUM NAV RAIL / BAR */}
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
            <button
              onClick={handleResetPortfolio}
              className="text-[10px] font-mono bg-red-950/20 border border-red-900/30 hover:border-red-500 hover:text-white text-red-400 px-3 py-1.5 rounded-lg transition active:scale-95 cursor-pointer"
            >
              Reset Demo Wallet
            </button>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-[10px] font-mono bg-slate-900/60 border border-slate-800 hover:border-slate-650 hover:border-slate-500 hover:text-white text-slate-400 px-3 py-1.5 rounded-lg transition active:scale-95 cursor-pointer"
            >
              <LogOut className="h-3 w-3" /> Keluar
            </button>
          </div>
        </nav>

        {/* 1.5. LIVE CRYPTO TICKER (MODULAR) */}
        <CryptoTicker
          selectedCoin={selectedCoin}
          onSelectCoin={(coin) => {
            setSelectedCoin(coin);
            setActiveTab("TRADING");
          }}
        />
      </header>

      {/* 2. LIVE WALLET METRICS OVERVIEW (HUD) */}
      <div className="bg-slate-900/20 border-b border-slate-900/60 px-6 py-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric block 1 */}
        <div className="flex items-center gap-4 bg-slate-950/35 border border-slate-900/50 p-4 rounded-2xl">
          <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400 border border-indigo-500/20">
            <DollarSign className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[10px] font-mono text-slate-500 uppercase">Total Net Worth (USD)</p>
            <p className="text-xl font-mono font-bold text-white mt-0.5">
              ${accountNetWorthUSD.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {/* Metric block 2 */}
        <div className="flex items-center gap-4 bg-slate-950/35 border border-slate-900/50 p-4 rounded-2xl">
          <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400 border border-emerald-500/20">
            <Coins className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[10px] font-mono text-slate-500 uppercase">Saldo Bebas (Margin)</p>
            <p className="text-xl font-mono font-bold text-slate-200 mt-0.5">
              ${portfolio.balanceUSD.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {/* Metric block 3 */}
        <div className="flex items-center gap-4 bg-slate-950/35 border border-slate-900/50 p-4 rounded-2xl">
          <div className={`p-3 rounded-xl border ${totalUnrealizedPnlUSD >= 0 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-red-500/10 text-red-400 border-red-500/20"}`}>
            <Percent className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[10px] font-mono text-slate-500 uppercase">Floating Unrealized P&L</p>
            <p className={`text-xl font-mono font-bold mt-0.5 ${totalUnrealizedPnlUSD >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {totalUnrealizedPnlUSD >= 0 ? "+" : ""}${totalUnrealizedPnlUSD.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {/* Metric block 4 */}
        <div className="flex items-center gap-4 bg-slate-950/35 border border-slate-900/50 p-4 rounded-2xl">
          <div className={`p-3 rounded-xl border ${netWorthReturnPct >= 0 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-red-500/10 text-red-400 border-red-500/20"}`}>
            {netWorthReturnPct >= 0 ? <ArrowUpRight className="h-5 w-5" /> : <ArrowDownRight className="h-5 w-5" />}
          </div>
          <div>
            <p className="text-[10px] font-mono text-slate-500 uppercase">Kinerja Return Akun</p>
            <p className={`text-xl font-mono font-bold mt-0.5 ${netWorthReturnPct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {netWorthReturnPct >= 0 ? "+" : ""}{netWorthReturnPct.toFixed(2)}%
            </p>
          </div>
        </div>
      </div>

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
              {/* Leverage Ticket form widget */}
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

          {newsVisited && (
            <div style={{ display: activeTab === "NEWS" ? "block" : "none" }}>
              <NewsPanel
                news={news}
                macroEvents={macroEvents}
                onRefreshNews={handleRefreshNewsFeed}
                isLoading={isLoadingNews}
              />
            </div>
          )}

          {backtestVisited && (
            <div style={{ display: activeTab === "BACKTEST" ? "block" : "none" }}>
              <BacktestPanel onRunBacktest={handleRunStrategyBacktest} />
            </div>
          )}

          {mlVisited && (
            <div style={{ display: activeTab === "ML" ? "block" : "none" }}>
              <MLPanel
                onTrainModel={handleTrainLocalMLModel}
                onGetForecast={handleRequestAIForecast}
                savedModels={mlModels}
              />
            </div>
          )}

          {aiBotVisited && (
            <div style={{ display: activeTab === "AI_BOT" ? "block" : "none" }}>
              <AIBotPanel
                savedModels={mlModels}
                llmSettings={llmSettings}
                active={activeTab === "AI_BOT"}
              />
            </div>
          )}

          {settingsVisited && (
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

          {liveVisited && (
            <div style={{ display: activeTab === "LIVE" ? "block" : "none" }}>
              <LiveTradingPanel
                lang="ID"
                selectedCoin={selectedCoin}
                active={activeTab === "LIVE"}
              />
            </div>
          )}

          {docsVisited && (
            <div style={{ display: activeTab === "DOCS" ? "block" : "none" }}>
              <DocsPanel />
            </div>
          )}
        </ErrorBoundary>
      </main>
    </div>
  );
}
