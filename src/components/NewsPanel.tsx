import React, { useState } from "react";
import { NewsArticle, MacroEvent } from "../types";
import { 
  Newspaper, 
  RefreshCw, 
  Compass, 
  ShieldAlert, 
  CheckCircle, 
  Flame, 
  Calendar, 
  Clock, 
  Filter, 
  ShieldCheck, 
  ChevronRight,
  TrendingUp,
  AlertTriangle
} from "lucide-react";

interface NewsPanelProps {
  news: NewsArticle[];
  macroEvents?: MacroEvent[];
  onRefreshNews: () => void;
  isLoading: boolean;
}

export function getSourceReliability(source: string): { label: "High" | "Medium" | "Low"; color: string; bg: string; border: string } {
  const src = source.toLowerCase();
  if (src.includes("reuters") || src.includes("panic") || src.includes("bbc") || src.includes("bloomberg")) {
    return {
      label: "High",
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20"
    };
  }
  if (src.includes("coindesk") || src.includes("decrypt") || src.includes("cointelegraph")) {
    return {
      label: "Medium",
      color: "text-amber-400",
      bg: "bg-amber-500/10",
      border: "border-amber-500/20"
    };
  }
  return {
    label: "Low",
    color: "text-slate-400",
    bg: "bg-slate-500/10",
    border: "border-slate-800"
  };
}

export function NewsPanel({ news, macroEvents = [], onRefreshNews, isLoading }: NewsPanelProps) {
  const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(null);
  const [sourceFilter, setSourceFilter] = useState<string>("ALL");

  // Calculate overall market sentiment score
  const { averageScore, label, color, description, percentage } = React.useMemo(() => {
    if (!news || news.length === 0) {
      return { averageScore: 0, label: "NETRAL", color: "text-slate-400 bg-slate-500/10", description: "Pasar sedang menunggu arah perkembangan baru.", percentage: 50 };
    }
    const total = news.reduce((acc, curr) => acc + curr.sentimentScore, 0);
    const avg = total / news.length;

    // Map -1 to 1 into 0% to 100%
    const pct = ((avg + 1) / 2) * 100;

    let lbl = "NETRAL";
    let col = "text-slate-400 border-slate-800 bg-slate-900/40";
    let desc = "Sentimen pasar saat ini berada dalam kondisi konsolidasi netral.";

    if (avg > 0.4) {
      lbl = "SANGAT BULLISH";
      col = "text-emerald-400 border-emerald-950 bg-emerald-950/20";
      desc = "Kombinasi berita didominasi oleh aliran akumulasi dana institusi dan adopsi regulasi positif.";
    } else if (avg > 0.1) {
      lbl = "BULLISH";
      col = "text-green-400 border-green-950 bg-green-950/20";
      desc = "Arus berita positif mendominasi pergerakan. Mendukung sentimen beli bertahap.";
    } else if (avg < -0.4) {
      lbl = "SANGAT BEARISH";
      col = "text-red-400 border-red-950 bg-red-950/20";
      desc = "FUD makroekonomi, tuntutan regulasi, atau masalah keamanan memicu kepanikan jual masal.";
    } else if (avg < -0.1) {
      lbl = "BEARISH";
      col = "text-amber-400 border-amber-950 bg-amber-950/20";
      desc = "Sentimen miring ke arah negatif. Sebaiknya lakukan manajemen risiko posisi long secara ketat.";
    }

    return {
      averageScore: avg,
      label: lbl,
      color: col,
      description: desc,
      percentage: pct,
    };
  }, [news]);

  // Unique sources for filter dropdown options
  const uniqueSources = React.useMemo(() => {
    const list = new Set<string>();
    news.forEach((n) => {
      if (n.source) list.add(n.source);
    });
    return Array.from(list);
  }, [news]);

  // Filtered news articles list
  const filteredNews = React.useMemo(() => {
    if (sourceFilter === "ALL") return news;
    if (sourceFilter === "HIGH_ONLY") {
      return news.filter((n) => getSourceReliability(n.source).label === "High");
    }
    return news.filter((n) => n.source === sourceFilter);
  }, [news, sourceFilter]);

  return (
    <div className="space-y-6">
      {/* Top Banner & Sentiment Gauge */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Metric Card 1: Gauge */}
        <div className="lg:col-span-2 bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center mb-4 flex-wrap gap-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-slate-800 rounded-lg border border-slate-700">
                  <Compass className="h-5 w-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-sans font-bold text-lg tracking-tight text-white">Barometer Sentimen Pasar Global</h3>
                  <p className="text-xs text-slate-500 font-mono">Diperbarui melalui Analisis Sentimen Multi-Model AI secara Real-time</p>
                </div>
              </div>
              <button
                onClick={onRefreshNews}
                disabled={isLoading}
                className="flex items-center gap-1.5 text-xs font-mono font-bold bg-slate-800 hover:bg-slate-700 active:scale-95 disabled:opacity-50 text-indigo-400 hover:text-white px-3.5 py-2 rounded-xl border border-slate-700 transition cursor-pointer"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
                Scrape & Analisis Berita
              </button>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed mb-6">{description}</p>
          </div>

          {/* Graphical Gauge Slider */}
          <div className="space-y-3">
            <div className="flex justify-between items-end text-xs font-mono">
              <span className="text-red-400 flex items-center gap-1">
                <ShieldAlert className="h-3 w-3" /> BEARISH (-1.0)
              </span>
              <div className={`px-3 py-1 rounded-full border text-xs font-bold ${color}`}>
                KONDISI: {label} ({averageScore.toFixed(2)})
              </div>
              <span className="text-emerald-400 flex items-center gap-1">
                <Flame className="h-3 w-3 animate-bounce" /> BULLISH (+1.0)
              </span>
            </div>

            {/* Glowing gauge track */}
            <div className="w-full h-4 bg-slate-950 rounded-full border border-slate-800/80 p-0.5 overflow-hidden relative">
              {/* Dynamic colored progress fill */}
              <div
                className="h-full rounded-full bg-gradient-to-r from-red-500 via-yellow-400 via-green-400 to-emerald-500 transition-all duration-1000"
                style={{ width: `${percentage}%` }}
              ></div>
              {/* Pointer indicator pin */}
              <div
                className="absolute top-0 bottom-0 w-1.5 bg-white border border-slate-950 shadow-xl transition-all duration-1000"
                style={{ left: `calc(${percentage}% - 3px)` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Fact Card 2: Sentiment Summary info */}
        <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl flex flex-col justify-between">
          <div className="space-y-4">
            <h4 className="text-xs font-mono text-slate-400 uppercase tracking-wider">Metrik Scraping Terkini</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-950/50 border border-slate-800/40 rounded-xl p-3 text-center">
                <p className="text-2xl font-mono font-bold text-white">{news.length}</p>
                <p className="text-[10px] text-slate-500 uppercase">Total Artikel</p>
              </div>
              <div className="bg-slate-950/50 border border-slate-800/40 rounded-xl p-3 text-center">
                <p className="text-2xl font-mono font-bold text-emerald-400">
                  {news.filter((n) => n.sentimentLabel === "BULLISH").length}
                </p>
                <p className="text-[10px] text-slate-500 uppercase">Bullish Feed</p>
              </div>
              <div className="bg-slate-950/50 border border-slate-800/40 rounded-xl p-3 text-center">
                <p className="text-2xl font-mono font-bold text-red-400">
                  {news.filter((n) => n.sentimentLabel === "BEARISH").length}
                </p>
                <p className="text-[10px] text-slate-500 uppercase">Bearish Feed</p>
              </div>
              <div className="bg-slate-950/50 border border-slate-800/40 rounded-xl p-3 text-center">
                <p className="text-2xl font-mono font-bold text-slate-400">
                  {news.filter((n) => n.sentimentLabel === "NEUTRAL").length}
                </p>
                <p className="text-[10px] text-slate-500 uppercase">Netral Feed</p>
              </div>
            </div>
          </div>

          <div className="text-[11px] font-mono text-slate-500 border-t border-slate-800/50 pt-4 flex gap-1.5 items-center">
            <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
            <span>Kredibilitas Tinggi (CryptoPanic, Reuters, BBC, CoinDesk)</span>
          </div>
        </div>
      </div>

      {/* Rebalanced Layout: Global Macroeconomic Calendar on the LEFT (Wider Column) + News Stream on the RIGHT (Stacked Column) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: Global Macro Calendar (Col-span-2) - Wider layout */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-800 pb-2">
            <h4 className="font-sans font-bold text-white text-base flex items-center gap-2">
              <Calendar className="h-5 w-5 text-indigo-400" />
              Kalender Makroekonomi Global (Dampak Likuiditas & DXY)
            </h4>
            <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-2.5 py-0.5 rounded border border-amber-500/20 font-bold">
              ForexFactory RSS
            </span>
          </div>

          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/60 rounded-2xl p-5 shadow-2xl space-y-4">
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Pengumuman kalender ekonomi global yang berdampak langsung terhadap pergerakan indeks Dolar AS (DXY) dan likuiditas pasar modal/kripto di seluruh dunia.
            </p>

            {macroEvents.length === 0 ? (
              <div className="py-24 text-center">
                <p className="text-sm text-slate-500 font-mono">Sedang menyinkronkan jadwal kalender ekonomi makro...</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[110vh] overflow-y-auto pr-2 custom-scrollbar">
                {macroEvents.map((evt) => {
                  const isHigh = evt.impact.toLowerCase() === "high";
                  const isMedium = evt.impact.toLowerCase() === "medium";
                  const impactColor = isHigh
                    ? "text-red-400 bg-red-500/10 border-red-500/20"
                    : isMedium
                    ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                    : "text-slate-400 bg-slate-500/10 border-slate-800";

                  return (
                    <div
                      key={evt.id}
                      className="bg-slate-950/60 border border-slate-850 p-4 rounded-xl space-y-3 hover:border-slate-800 transition flex flex-col justify-between group"
                    >
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-[10px] font-mono text-indigo-400 font-bold bg-slate-900 px-2.5 py-0.5 rounded border border-slate-800">
                            🌍 {evt.country}
                          </span>
                          <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border uppercase tracking-wider ${impactColor}`}>
                            {evt.impact} Impact
                          </span>
                        </div>

                        <h5 className="font-sans font-bold text-white text-sm leading-snug group-hover:text-indigo-300 transition duration-150">
                          {evt.title}
                        </h5>
                      </div>

                      <div className="space-y-2 pt-2 border-t border-slate-900/60">
                        <div className="flex items-center gap-1 text-[10px] font-mono text-slate-500">
                          <Clock className="h-3 w-3" />
                          <span>{evt.date} • {evt.time}</span>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono pt-1">
                          <div className="bg-slate-950/90 border border-slate-900 p-1.5 rounded text-center">
                            <p className="text-slate-500 text-[9px] uppercase">Forecast</p>
                            <p className="text-slate-200 font-bold">{evt.forecast || "-"}</p>
                          </div>
                          <div className="bg-slate-950/90 border border-slate-900 p-1.5 rounded text-center">
                            <p className="text-slate-500 text-[9px] uppercase">Previous</p>
                            <p className="text-slate-300">{evt.previous || "-"}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: News Stream Stacked (Col-span-1) - Stacked Vertically with filter */}
        <div className="lg:col-span-1 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800 pb-2 gap-2">
            <h4 className="font-sans font-bold text-white text-base flex items-center gap-2">
              <Newspaper className="h-5 w-5 text-indigo-400" />
              Aliran Berita Terkini
            </h4>
            <span className="text-[10px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/10 font-bold self-start">
              Newest First
            </span>
          </div>

          {/* Filtering Dropdown Toolbar */}
          <div className="bg-slate-900/80 border border-slate-850 p-3 rounded-xl flex items-center gap-2.5">
            <Filter className="h-4 w-4 text-slate-400 shrink-0" />
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-lg px-2.5 py-1.5 outline-none font-sans font-semibold text-white text-xs"
            >
              <option value="ALL">📰 Semua Penerbit Berita ({news.length})</option>
              <option value="HIGH_ONLY">⚡ Signifikansi Tinggi (Reuters, CryptoPanic, BBC)</option>
              {uniqueSources.map((src) => (
                <option key={src} value={src}>
                  🎯 {src} ({news.filter((n) => n.source === src).length})
                </option>
              ))}
            </select>
          </div>

          {isLoading && news.length === 0 ? (
            <div className="h-96 flex flex-col justify-center items-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mb-3"></div>
              <p className="text-slate-500 font-mono text-xs text-center">Scraping global rss tickers...</p>
            </div>
          ) : (
            <div className="space-y-4 max-h-[110vh] overflow-y-auto pr-1 custom-scrollbar">
              {filteredNews.length === 0 ? (
                <div className="p-8 text-center bg-slate-950/40 border border-slate-850 rounded-2xl">
                  <p className="text-xs text-slate-500 font-mono">Tidak ada artikel yang cocok dengan filter sumber.</p>
                </div>
              ) : (
                filteredNews.map((article) => {
                  const isBullish = article.sentimentLabel === "BULLISH";
                  const isBearish = article.sentimentLabel === "BEARISH";
                  const badgeColor = isBullish
                    ? "text-emerald-400 border-emerald-950 bg-emerald-950/30"
                    : isBearish
                    ? "text-red-400 border-red-950 bg-red-950/30"
                    : "text-slate-300 border-slate-800 bg-slate-800/30";

                  const reliability = getSourceReliability(article.source);

                  return (
                    <div
                      key={article.id}
                      className="bg-slate-900/50 backdrop-blur-md border border-slate-800/80 rounded-2xl p-4.5 hover:border-slate-700 hover:bg-slate-900/80 transition duration-200 flex flex-col justify-between hover:shadow-xl group"
                    >
                      <div className="space-y-3">
                        {/* Header: Publisher name & Time */}
                        <div className="flex justify-between items-center flex-wrap gap-2">
                          <span className="text-[10px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/10 font-bold">
                            {article.source}
                          </span>
                          
                          <span className="text-[10px] font-mono text-slate-500">
                            {new Date(article.timestamp).toLocaleDateString("id-ID", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>

                        {/* Title */}
                        <h4 className="font-sans font-bold text-white text-sm leading-snug group-hover:text-indigo-300 transition duration-150 line-clamp-3">
                          {article.title}
                        </h4>

                        {/* Reliability and Sentiment Badges */}
                        <div className="flex flex-wrap gap-1.5 items-center">
                          {/* Institutional reliability Badge */}
                          <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border flex items-center gap-1 ${reliability.bg} ${reliability.color} ${reliability.border}`}>
                            <ShieldCheck className="h-2.5 w-2.5" />
                            {reliability.label} Reliability
                          </span>

                          <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border ${badgeColor}`}>
                            {article.sentimentLabel} ({article.sentimentScore >= 0 ? "+" : ""}{article.sentimentScore})
                          </span>
                        </div>

                        {/* Text snippet */}
                        <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                          {article.content}
                        </p>

                        {/* Quick AI bullet review */}
                        {article.summary && (
                          <div className="bg-slate-950/80 border border-slate-850 p-2.5 rounded-lg text-[11px] text-slate-300 leading-normal italic">
                            <span className="text-[9px] font-mono font-bold text-indigo-400 uppercase block tracking-wider mb-0.5">💡 AI Insight Summary</span>
                            "{article.summary}"
                          </div>
                        )}
                      </div>

                      {/* Footer Actions */}
                      <div className="flex justify-between items-center pt-3 border-t border-slate-800/40 mt-3">
                        <button
                          onClick={() => setSelectedArticle(article)}
                          className="text-xs font-mono font-bold text-indigo-400 hover:text-indigo-300 underline cursor-pointer flex items-center gap-0.5"
                        >
                          Selengkapnya <ChevronRight className="h-3 w-3" />
                        </button>
                        
                        <a
                          href={article.url}
                          target="_blank"
                          referrerPolicy="no-referrer"
                          className="text-[10px] font-mono text-slate-500 hover:text-slate-300"
                        >
                          Sumber ↗
                        </a>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>

      </div>

      {/* Detailed Modal Overlay */}
      {selectedArticle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full p-6 shadow-2xl overflow-y-auto max-h-[85vh] space-y-4">
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-lg border border-indigo-500/10">
                  {selectedArticle.source}
                </span>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${getSourceReliability(selectedArticle.source).bg} ${getSourceReliability(selectedArticle.source).color} ${getSourceReliability(selectedArticle.source).border}`}>
                  {getSourceReliability(selectedArticle.source).label} Reliability
                </span>
              </div>
              <button
                onClick={() => setSelectedArticle(null)}
                className="text-slate-400 hover:text-white font-mono text-sm bg-slate-800 hover:bg-slate-700 px-3 py-1 rounded-xl border border-slate-700 transition cursor-pointer"
              >
                Tutup
              </button>
            </div>

            <h3 className="font-sans font-bold text-xl text-white tracking-tight leading-snug">
              {selectedArticle.title}
            </h3>

            <div className="flex flex-wrap gap-2 py-1 border-y border-slate-800/40 font-mono text-xs text-slate-500">
              <span>
                Dipublikasi: {new Date(selectedArticle.timestamp).toLocaleString("id-ID")}
              </span>
              <span>•</span>
              <span className="text-emerald-400 font-bold">
                Sentimen: {selectedArticle.sentimentLabel} ({selectedArticle.sentimentScore})
              </span>
              <span>•</span>
              <span>
                Driver: {selectedArticle.impactFactor}
              </span>
            </div>

            <div className="space-y-3">
              <h5 className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">Isi Berita Lengkap (Scraped)</h5>
              <p className="text-sm text-slate-300 leading-relaxed bg-slate-950/30 p-4 rounded-xl border border-slate-800/30">
                {selectedArticle.content}
              </p>
            </div>

            {selectedArticle.summary && (
              <div className="bg-indigo-950/20 border border-indigo-900/40 rounded-2xl p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Newspaper className="h-4 w-4 text-indigo-400" />
                  <span className="text-xs font-mono font-bold text-indigo-400 uppercase tracking-wider">
                    Ulasan Sentimen Mendalam AI
                  </span>
                </div>
                <p className="text-sm text-slate-200 leading-relaxed italic">
                  "{selectedArticle.summary}"
                </p>
              </div>
            )}

            <div className="pt-3 flex justify-end">
              <a
                href={selectedArticle.url}
                target="_blank"
                referrerPolicy="no-referrer"
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-bold px-4 py-2.5 rounded-xl flex items-center gap-1.5 active:scale-95 transition cursor-pointer"
              >
                Baca Artikel Asli di {selectedArticle.source} ↗
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
