import React, { useEffect, useState, useRef } from "react";
import { TrendingUp, TrendingDown, RefreshCw, Activity, ArrowUpRight, ArrowDownRight } from "lucide-react";

interface Asset {
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  type: string;
}

interface CryptoTickerProps {
  onSelectCoin?: (symbol: string) => void;
  selectedCoin?: string;
}

export function CryptoTicker({ onSelectCoin, selectedCoin }: CryptoTickerProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [prevPrices, setPrevPrices] = useState<{ [symbol: string]: number }>({});
  const [priceFlash, setPriceFlash] = useState<{ [symbol: string]: "up" | "down" | null }>({});
  const flashTimeouts = useRef<{ [symbol: string]: NodeJS.Timeout }>({});

  const fetchMarketData = async () => {
    try {
      const res = await fetch("/api/market-data");
      if (res.ok) {
        const data = await res.json();
        const newAssetsList: Asset[] = data.assets || [];
        
        // Track price changes for flash animations
        const newFlashes: { [symbol: string]: "up" | "down" | null } = {};
        let priceChanged = false;

        newAssetsList.forEach((asset) => {
          const sym = asset.symbol;
          const prevPrice = prevPrices[sym];
          if (prevPrice !== undefined && prevPrice !== asset.price) {
            newFlashes[sym] = asset.price > prevPrice ? "up" : "down";
            priceChanged = true;

            // Clear existing timeout for this asset
            if (flashTimeouts.current[sym]) {
              clearTimeout(flashTimeouts.current[sym]);
            }

            // Set timeout to clear flash
            flashTimeouts.current[sym] = setTimeout(() => {
              setPriceFlash((prev) => ({ ...prev, [sym]: null }));
            }, 1000);
          }
        });

        if (priceChanged) {
          setPriceFlash((prev) => ({ ...prev, ...newFlashes }));
        }

        // Save current prices as prev for next comparison
        const priceMap: { [symbol: string]: number } = {};
        newAssetsList.forEach((a) => {
          priceMap[a.symbol] = a.price;
        });
        setPrevPrices(priceMap);

        setAssets(newAssetsList);
        setError(false);
        setLastUpdated(new Date().toLocaleTimeString());
      } else {
        setError(true);
      }
    } catch (e) {
      console.error("Gagal mengambil data market ticker:", e);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 4000);
    return () => {
      clearInterval(interval);
      // Clean up any pending timeouts
      Object.values(flashTimeouts.current).forEach(clearTimeout);
    };
  }, [prevPrices]);

  // Translate symbol for app selection
  const handleCardClick = (symbol: string) => {
    if (!onSelectCoin) return;
    if (symbol === "XAU" || symbol === "DXY") {
      // These are non-tradable or distinct assets in the simulator, but let's pass them
      onSelectCoin(`${symbol}USDT`);
    } else {
      onSelectCoin(`${symbol}USDT`);
    }
  };

  const getAssetBadgeColor = (type: string) => {
    switch (type) {
      case "metal":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "fiat":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      default:
        return "bg-indigo-500/10 text-indigo-400 border-indigo-500/20";
    }
  };

  const formatPrice = (price: number, symbol: string) => {
    if (symbol === "XRP") return price.toFixed(4);
    if (symbol === "DXY") return price.toFixed(2); // index points
    return price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div className="bg-slate-950/80 border-b border-slate-900 px-6 py-3 flex flex-wrap items-center justify-between gap-4 backdrop-blur-md">
      {/* Label and Live Status */}
      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <span className="text-[11px] font-bold tracking-wider text-slate-400 uppercase font-sans">
          Live Market Ticker
        </span>
        {lastUpdated && (
          <span className="text-[9px] font-mono text-slate-600 hidden sm:inline">
            (Sinc: {lastUpdated})
          </span>
        )}
      </div>

      {/* Ticker Row */}
      <div className="flex items-center gap-3 overflow-x-auto no-scrollbar scroll-smooth flex-1 justify-start md:justify-end">
        {loading && assets.length === 0 ? (
          <div className="flex items-center gap-2 text-xs text-slate-500 font-mono py-1">
            <RefreshCw className="h-3 w-3 animate-spin text-slate-400" />
            Loading prices...
          </div>
        ) : error && assets.length === 0 ? (
          <div className="text-xs text-red-400 font-mono py-1">
            ⚠️ Gagal memuat data ticker.
          </div>
        ) : (
          assets.map((asset) => {
            const isSelected = selectedCoin === `${asset.symbol}USDT` || (asset.symbol === "XAU" && selectedCoin === "XAUUSDT") || (asset.symbol === "DXY" && selectedCoin === "DXYUSDT");
            const changeIsPositive = asset.change24h >= 0;
            const flash = priceFlash[asset.symbol];
            
            // Pulse class based on price direction changes
            let flashClass = "";
            if (flash === "up") flashClass = "ring-2 ring-emerald-500/50 bg-emerald-950/20";
            if (flash === "down") flashClass = "ring-2 ring-red-500/50 bg-red-950/20";

            return (
              <div
                key={asset.symbol}
                onClick={() => handleCardClick(asset.symbol)}
                className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl border transition-all duration-300 cursor-pointer select-none shrink-0 ${
                  isSelected
                    ? "bg-slate-900/90 border-indigo-500 shadow-sm shadow-indigo-500/10 scale-102"
                    : "bg-slate-900/30 border-slate-900 hover:border-slate-800 hover:bg-slate-900/50"
                } ${flashClass}`}
              >
                {/* Asset Label & Type */}
                <div className="flex flex-col">
                  <div className="flex items-center gap-1">
                    <span className={`text-[10px] font-mono px-1 rounded border font-bold ${getAssetBadgeColor(asset.type)}`}>
                      {asset.symbol}
                    </span>
                    <span className="text-[10px] font-medium text-slate-400 hidden lg:inline max-w-[80px] truncate">
                      {asset.name}
                    </span>
                  </div>
                </div>

                {/* Price Display */}
                <div className="flex flex-col items-end">
                  <span className="text-xs font-mono font-bold text-white transition-colors duration-200">
                    {asset.symbol !== "DXY" ? "$" : ""}{formatPrice(asset.price, asset.symbol)}
                  </span>
                  
                  {/* 24h Change badge */}
                  <span className={`flex items-center text-[9px] font-mono font-bold ${changeIsPositive ? "text-emerald-400" : "text-red-400"}`}>
                    {changeIsPositive ? (
                      <ArrowUpRight className="h-2.5 w-2.5 inline shrink-0" />
                    ) : (
                      <ArrowDownRight className="h-2.5 w-2.5 inline shrink-0" />
                    )}
                    {changeIsPositive ? "+" : ""}{asset.change24h.toFixed(2)}%
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
