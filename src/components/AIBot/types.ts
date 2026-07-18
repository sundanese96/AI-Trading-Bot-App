export interface AiBotSettings {
  enabled: boolean;
  symbol: string;
  strategy: "SCALPING" | "SWING" | "CONSERVATIVE" | "AGGRESSIVE" | "MARTINGALE" | "HEDGING";
  leverage: number;
  llmWeight: number;
  mlWeight: number;
  minConfidence: number;
  stopLossPct: number;
  takeProfitPct: number;
  trailingStopPct: number;
  allocationPerTrade: number;
  mlModelId: string;
  sentimentThreshold: number;
  riskLevel: "LOW" | "MEDIUM" | "HIGH";
  tpMultiplier: number;
  slMultiplier: number;
  runIntervalSeconds?: number;
  isCustom?: boolean;
  modelType?: string;
  timeframeMinutes?: number;
}

export const PRESETS = {
  safe: {
    strategy: "CONSERVATIVE" as const,
    leverage: 2,
    llmWeight: 0.7,
    mlWeight: 0.3,
    minConfidence: 75,
    takeProfitPct: 1.5,
    stopLossPct: 0.8,
    trailingStopPct: 0.2,
    sentimentThreshold: 0.20,
    riskLevel: "LOW" as const,
    tpMultiplier: 1.0,
    slMultiplier: 1.0,
  },
  medium: {
    strategy: "CONSERVATIVE" as const,
    leverage: 10,
    llmWeight: 0.5,
    mlWeight: 0.5,
    minConfidence: 65,
    takeProfitPct: 3.0,
    stopLossPct: 1.5,
    trailingStopPct: 0.5,
    sentimentThreshold: 0.15,
    riskLevel: "MEDIUM" as const,
    tpMultiplier: 1.0,
    slMultiplier: 1.0,
  },
  high_risk: {
    strategy: "AGGRESSIVE" as const,
    leverage: 25,
    llmWeight: 0.3,
    mlWeight: 0.7,
    minConfidence: 55,
    takeProfitPct: 6.0,
    stopLossPct: 3.0,
    trailingStopPct: 1.0,
    sentimentThreshold: 0.10,
    riskLevel: "HIGH" as const,
    tpMultiplier: 1.2,
    slMultiplier: 0.8,
  }
};

export const getPresetName = (s: AiBotSettings) => {
  for (const [name, p] of Object.entries(PRESETS)) {
    if (
      s.strategy === p.strategy &&
      Number(s.leverage) === p.leverage &&
      Math.abs(Number(s.llmWeight) - p.llmWeight) < 0.01 &&
      Math.abs(Number(s.mlWeight) - p.mlWeight) < 0.01 &&
      Number(s.minConfidence) === p.minConfidence &&
      Number(s.takeProfitPct) === p.takeProfitPct &&
      Number(s.stopLossPct) === p.stopLossPct &&
      Number(s.trailingStopPct) === p.trailingStopPct &&
      Math.abs((Number(s.sentimentThreshold) ?? 0.15) - p.sentimentThreshold) < 0.01 &&
      (s.riskLevel ?? "MEDIUM") === p.riskLevel &&
      Number(s.tpMultiplier ?? 1.0) === p.tpMultiplier &&
      Number(s.slMultiplier ?? 1.0) === p.slMultiplier
    ) {
      return name;
    }
  }
  return "custom";
};

export interface AiBotLog {
  id: string;
  timestamp: number;
  action: "BUY" | "SELL" | "CLOSE" | "HOLD" | "INFO" | "WARNING";
  symbol: string;
  price: number;
  confidence: number;
  message: string;
}

export interface BotStatusData {
  automationEnabled: boolean;
  activeTrades: any[];
  currentConfidence: number;
  logs: AiBotLog[];
  symbol: string;
  currentPrices?: { [symbol: string]: number };
  activatedAt?: number;
}
