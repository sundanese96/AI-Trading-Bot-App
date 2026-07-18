import React, { useState, useEffect } from "react";
import { MLModel } from "../types";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip } from "recharts";
import { Cpu, BrainCircuit, Play, CheckCircle2, ChevronRight, HelpCircle, Sparkles } from "lucide-react";

interface MLPanelProps {
  onTrainModel: (params: {
    learningRate: number;
    epochs: number;
    features: string[];
    symbol: string;
    modelType?: string;
  }) => Promise<{ modelId: string; r2Score: number; lossHistory: { epoch: number; loss: number }[]; weights: { [key: string]: number }; bias: number }>;
  onGetForecast: (params: {
    symbol: string;
    rsi: number;
    macd: { line: number; signal: number; histogram: number };
    sentimentScore: number;
  }) => Promise<{ signal: string; priceTargetUSD: number; stopLossUSD: number; reasoning: string }>;
  savedModels: MLModel[];
}

export function MLPanel({ onTrainModel, onGetForecast, savedModels }: MLPanelProps) {
  // ML Local Training Form
  const [learningRate, setLearningRate] = useState(0.01);
  const [epochs, setEpochs] = useState(100);
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>(["ma10", "ma20", "rsi", "volume"]);
  const [modelType, setModelType] = useState('xgboost');

  const [isTraining, setIsTraining] = useState(false);
  const [trainingLoss, setTrainingLoss] = useState<{ epoch: number; loss: number }[]>([]);
  const [currentEpoch, setCurrentEpoch] = useState(0);
  const [trainedModelResult, setTrainedModelResult] = useState<{
    r2Score: number;
    weights: { [key: string]: number };
    bias: number;
  } | null>(null);

  // Gemini Forecast Advisor
  const [forecastSymbol, setForecastSymbol] = useState("BTCUSDT");
  const [rsi, setRsi] = useState(54);
  const [macdHist, setMacdHist] = useState(0.2);
  const [sentimentVal, setSentimentVal] = useState(0.15);

  const [isConsultingAI, setIsConsultingAI] = useState(false);
  const [aiAdvisory, setAiAdvisory] = useState<{
    signal: string;
    priceTargetUSD: number;
    stopLossUSD: number;
    reasoning: string;
  } | null>(null);

  const toggleFeature = (feat: string) => {
    if (selectedFeatures.includes(feat)) {
      if (selectedFeatures.length > 1) {
        setSelectedFeatures(selectedFeatures.filter((f) => f !== feat));
      }
    } else {
      setSelectedFeatures([...selectedFeatures, feat]);
    }
  };

  useEffect(() => {
    return () => {
      if ((window as any)._mlPanelInterval) {
        clearInterval((window as any)._mlPanelInterval);
      }
    };
  }, []);

  const handleTrainLocalModel = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsTraining(true);
    setTrainedModelResult(null);
    setTrainingLoss([]);
    setCurrentEpoch(0);

    try {
      const response = await onTrainModel({
        modelType,
        learningRate,
        epochs,
        features: selectedFeatures,
        symbol,
      });

      const totalEpochs = response.lossHistory.length;
      let i = 0;
      
      const interval = setInterval(() => {
        if (i < totalEpochs) {
          setTrainingLoss(response.lossHistory.slice(0, i + 1));
          setCurrentEpoch(response.lossHistory[i].epoch);
          i += Math.max(1, Math.floor(totalEpochs / 30)); 
        } else {
          setTrainingLoss(response.lossHistory);
          setCurrentEpoch(response.lossHistory[totalEpochs - 1].epoch);
          setTrainedModelResult({
            r2Score: response.r2Score,
            weights: response.weights,
            bias: response.bias,
          });
          setIsTraining(false);
          clearInterval(interval);
        }
      }, 35);
      
      // Store interval globally for cleanup on unmount
      (window as any)._mlPanelInterval = interval;
    } catch (err: any) {
      alert(err.message || "Gagal melatih model lokal.");
      setIsTraining(false);
    }
  };

const handleGetAIForecast = async () => {
    setIsConsultingAI(true);
    try {
      const signal = macdHist * 0.8;
      const histogram = macdHist - signal;

      const advisory = await onGetForecast({
        symbol: forecastSymbol,
        rsi,
        macd: { line: macdHist, signal, histogram },
        sentimentScore: sentimentVal,
      });
      setAiAdvisory(advisory);
    } catch (err: any) {
      alert(err.message || "Gagal mendapatkan analisis dari AI.");
    } finally {
      setIsConsultingAI(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Grid: 1. local ML Trainer, 2. Gemini AI Advisory */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Module 1: ML Model Trainer Local */}
        <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
                <Cpu className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <h3 className="font-sans font-bold text-lg text-white">Latihan Mandiri Model ML (Local CPU/GPU)</h3>
                <p className="text-xs text-slate-500 font-mono">Latih formula regresi multivariat instan berdasarkan data historis real-time.</p>
              </div>
            </div>

<form onSubmit={handleTrainLocalModel} className="space-y-4 text-xs">
              <div className="grid grid-cols-3 gap-2">
                <div className="space-y-1">
                  <label className="text-slate-400 font-mono">KOIN DATASET</label>
                  <select
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none"
                  >
                    <option value="BTCUSDT">BTCUSDT</option>
                    <option value="ETHUSDT">ETHUSDT</option>
                    <option value="SOLUSDT">SOLUSDT</option>
                    <option value="BNBUSDT">BNBUSDT</option>
                    <option value="XRPUSDT">XRPUSDT</option>
                    <option value="ADAUSDT">ADAUSDT</option>
                    <option value="DOGEUSDT">DOGEUSDT</option>
                    <option value="DOTUSDT">DOTUSDT</option>
                    <option value="SHIBUSDT">SHIBUSDT</option>
                    <option value="LTCUSDT">LTCUSDT</option>
                    <option value="LINKUSDT">LINKUSDT</option>
                    <option value="NEARUSDT">NEARUSDT</option>
                    <option value="SUIUSDT">SUIUSDT</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 font-mono">LEARNING RATE</label>
                  <select
                    value={learningRate}
                    onChange={(e) => setLearningRate(parseFloat(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none font-mono"
                  >
                    <option value="0.001">0.001 (Presisi Tinggi)</option>
                    <option value="0.01">0.01 (Standar)</option>
                    <option value="0.05">0.05 (Agresif)</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 font-mono">TIPE MODEL</label>
                  <select
                    value={modelType}
                    onChange={(e) => setModelType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none"
                  >
                    <option value="xgboost">xgboost</option>
                    <option value="catboost">catboost</option>
                    <option value="lightgbm">lightgbm</option>
                    <option value="pytorch">pytorch</option>
                    <option value="gbdt">gbdt (Python GBDT)</option>
                    <option value="linear">linear (Linear JS)</option>
                  </select>
                </div>
              </div>

              {/* Epoch slider */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-[10px] font-mono text-slate-400">
                  <span>EPOCH SIKLUS LATIHAN</span>
                  <span className="text-indigo-400 font-bold">{epochs} Epoch</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="300"
                  step="10"
                  value={epochs}
                  onChange={(e) => setEpochs(parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-850 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              {/* Features checklist */}
              <div className="space-y-2">
                <label className="text-slate-400 font-mono block">FITUR INPUT MATRIX (FEATURES)</label>
                <div className="flex flex-wrap gap-2">
                  {["ma10", "ma20", "rsi", "volume"].map((feat) => {
                    const isChecked = selectedFeatures.includes(feat);
                    return (
                      <button
                        type="button"
                        key={feat}
                        onClick={() => toggleFeature(feat)}
                        className={`px-3 py-1.5 rounded-lg border text-[10px] font-mono font-bold transition ${
                          isChecked
                            ? "bg-indigo-600/10 border-indigo-500 text-indigo-400"
                            : "bg-slate-950 border-slate-800 text-slate-500 hover:border-slate-700"
                        }`}
                      >
                        {feat.toUpperCase()}
                      </button>
                    );
                  })}
                </div>
              </div>

              <button
                type="submit"
                disabled={isTraining}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2.5 px-4 rounded-xl flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50 transition cursor-pointer"
              >
                <Play className="h-4 w-4" />
                {isTraining ? `Melakukan Propagasi... Epoch ${currentEpoch}/${epochs}` : "Mulai Training Local Model"}
              </button>
            </form>
          </div>

          {/* Local Training output graph */}
          <div className="mt-6">
            {trainingLoss.length > 0 && (
              <div className="space-y-4">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-mono text-slate-400 flex items-center gap-1.5">
                    <BrainCircuit className="h-3.5 w-3.5 text-indigo-400" />
                    Grafik Kerugian Kurva (Loss MSE)
                  </span>
                  {trainedModelResult && (
                    <span className="font-mono font-bold text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Latihan Berhasil (Akurasi R²: {trainedModelResult.r2Score})
                    </span>
                  )}
                </div>

                <div className="h-36 w-full bg-slate-950 rounded-xl p-2 border border-slate-800/60">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trainingLoss}>
                      <XAxis dataKey="epoch" stroke="#334155" fontSize={8} />
                      <YAxis stroke="#334155" fontSize={8} />
                      <ChartTooltip
                        contentStyle={{ backgroundColor: "#020617", borderColor: "#1e293b", borderRadius: "8px" }}
                        labelStyle={{ color: "#94a3b8", fontSize: 9 }}
                        itemStyle={{ color: "#ffffff", fontSize: 10 }}
                        formatter={(val) => [parseFloat(val as string).toFixed(5), "Mean Squared Error"]}
                      />
                      <Line type="monotone" dataKey="loss" stroke="#6366f1" strokeWidth={1.5} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {trainedModelResult && (
                  <div className="bg-slate-950/60 border border-slate-800/40 rounded-xl p-3 space-y-2 text-[10px] font-mono">
                    <p className="text-slate-400 font-bold uppercase text-[9px] mb-1">Bobot Linear Ternormalisasi:</p>
                    <div className="grid grid-cols-2 gap-2 text-slate-300">
                      {Object.entries(trainedModelResult.weights).map(([feat, w]) => {
                        const val = w as number;
                        return (
                          <div key={feat} className="flex justify-between bg-slate-900 px-2 py-1 rounded">
                            <span>{feat.toUpperCase()}:</span>
                            <span className={val >= 0 ? "text-emerald-400" : "text-red-400"}>
                              {val >= 0 ? "+" : ""}{val.toFixed(4)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Module 2: Multi-Provider AI Forecast Assistant */}
        <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
                <Sparkles className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <h3 className="font-sans font-bold text-lg text-white">Konsultan Strategis Multi-Model AI</h3>
                <p className="text-xs text-slate-500 font-mono">Kombinasikan indikator teknis dan berita untuk perkiraan taktis AI.</p>
              </div>
            </div>

            {/* Slider parameters representing Indicators mock settings for LLM prompting */}
            <div className="space-y-3 bg-slate-950/40 p-4 rounded-xl border border-slate-800/40 text-xs">
              <div className="space-y-1">
                <label className="text-slate-400 font-mono">KOIN TARGET</label>
                <select
                  value={forecastSymbol}
                  onChange={(e) => setForecastSymbol(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 outline-none font-mono font-bold"
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

              {/* RSI indicator manual tweak */}
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] font-mono text-slate-400">
                  <span>INDIKATOR TEKNIS: RSI (14)</span>
                  <span className="text-slate-300">{rsi}</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="90"
                  value={rsi}
                  onChange={(e) => setRsi(parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-850 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              {/* News sentiment manual slider */}
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] font-mono text-slate-400">
                  <span>SKOR SENTIMEN BERITA</span>
                  <span className={sentimentVal >= 0 ? "text-emerald-400" : "text-red-400"}>
                    {sentimentVal >= 0 ? "+" : ""}{sentimentVal}
                  </span>
                </div>
                <input
                  type="range"
                  min="-1"
                  max="1"
                  step="0.05"
                  value={sentimentVal}
                  onChange={(e) => setSentimentVal(parseFloat(e.target.value))}
                  className="w-full h-1 bg-slate-850 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>
            </div>

            {/* AI Advisor Response panel */}
            <div className="min-h-36 bg-slate-950 border border-slate-850 rounded-2xl p-4 flex flex-col justify-center relative overflow-hidden group">
              {isConsultingAI ? (
                <div className="text-center space-y-2">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-400 mx-auto"></div>
                  <p className="text-xs text-slate-400 font-mono">Menyusun ringkasan analisis strategis melalui LLM API...</p>
                </div>
              ) : aiAdvisory ? (
                <div className="space-y-3">
                  <div className="flex flex-wrap justify-between items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                      aiAdvisory.signal.includes("BUY")
                        ? "text-emerald-400 bg-emerald-950/20 border-emerald-950"
                        : aiAdvisory.signal.includes("SELL")
                        ? "text-red-400 bg-red-950/20 border-red-950"
                        : "text-slate-400 bg-slate-900/40 border-slate-800"
                    }`}>
                      Rekomendasi: {aiAdvisory.signal}
                    </span>
                    <div className="text-[10px] font-mono text-slate-400 space-x-2">
                      <span>Target: <span className="text-emerald-400 font-bold">${aiAdvisory.priceTargetUSD.toLocaleString()}</span></span>
                      <span>SL: <span className="text-red-400 font-bold">${aiAdvisory.stopLossUSD.toLocaleString()}</span></span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed italic border-t border-slate-800/40 pt-2">
                    "{aiAdvisory.reasoning}"
                  </p>
                </div>
              ) : (
                <div className="text-center text-slate-500 py-6">
                  <ChevronRight className="h-8 w-8 text-slate-700 mx-auto mb-2" />
                  <p className="text-xs max-w-xs mx-auto">Atur parameter indikator dan klik tombol konsultasi untuk memicu analisis pakar AI.</p>
                </div>
              )}
            </div>
          </div>

          <button
            onClick={handleGetAIForecast}
            disabled={isConsultingAI}
            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:scale-[0.98] text-white text-xs font-mono font-bold py-2.5 px-4 rounded-xl flex items-center justify-center gap-1.5 shadow-md shadow-indigo-600/10 cursor-pointer border border-indigo-500/20 mt-4"
          >
            <Sparkles className="h-4 w-4" />
            {isConsultingAI ? "Berkonsultasi..." : "Minta Rekomendasi AI"}
          </button>
        </div>
      </div>

      {/* Historical List Models Trained */}
      <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/60 rounded-2xl p-6 shadow-2xl">
        <h4 className="font-sans font-bold text-white text-base mb-4">Daftar Model ML yang Dilatih di Server ({savedModels.length})</h4>
        {savedModels.length === 0 ? (
          <p className="text-xs text-slate-500 font-mono">Belum ada model lokal yang tersimpan dalam database server.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {savedModels.map((model) => (
              <div key={model.id} className="bg-slate-950/60 border border-slate-850 p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <h5 className="font-sans font-bold text-sm text-indigo-400">{model.name}</h5>
                  <p className="text-[10px] text-slate-500 font-mono">Dibuat: {new Date(model.trainedAt).toLocaleString()}</p>
                  <p className="text-xs text-slate-300 mt-2 font-mono">Akurasi R²: <span className="text-emerald-400 font-bold">{model.r2Score}</span></p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {model.features.map((f) => (
                      <span key={f} className="text-[9px] font-mono bg-slate-900 border border-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                        {f.toUpperCase()}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
