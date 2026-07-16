export interface PortfolioData {
  balanceUSD: number;
  assets: { [symbol: string]: number };
  initialBalance: number;
}

export interface TradePosition {
  id: string;
  symbol: string;
  type: "BUY" | "SELL";
  size: number;
  leverage: number;
  entryPrice: number;
  exitPrice: number | null;
  pnl: number | null;
  sl: number | null;
  tp: number | null;
  trailingStopPct: number | null;
highestPriceReached?: number;
  lowestPriceReached?: number;
  status: "OPEN" | "CLOSED";
  timestamp: number;
  exitTimestamp: number | null;
  reason: string | null;
}

export interface NewsArticle {
  id: string;
  title: string;
  source: string;
  url: string;
  content: string;
  summary: string;
  sentimentScore: number;
  sentimentLabel: "BULLISH" | "BEARISH" | "NEUTRAL";
  impactFactor: string;
  timestamp: number;
}

export interface MLModel {
  id: string;
  name: string;
  symbol: string;
  learningRate: number;
  epochs: number;
  features: string[];
  lossHistory: number[];
  r2Score: number;
  trainedAt: number;
  weights: { [key: string]: number };
  bias: number;
}

export interface NotificationSettings {
  telegramToken: string;
  telegramChatId: string;
  emailAddress: string;
  tradeExecuted: boolean;
  riskTriggered: boolean;
  highSentimentAlert: boolean;
}

export interface LlmSettings {
  provider: "openai" | "anthropic" | "deepseek" | "custom" | "simulated";
  apiKey: string;
  baseUrl: string;
  modelName: string;
}

export interface MacroEvent {
  id: string;
  title: string;
  country: string;
  date: string;
  time: string;
  impact: string; // "Low" | "Medium" | "High"
  forecast: string;
  previous: string;
}

export interface NotificationLog {
  id: string;
  type: "TELEGRAM" | "EMAIL";
  recipient: string;
  subject: string;
  message: string;
  status: "SUCCESS" | "FAILED" | "SIMULATED";
  timestamp: number;
}

export interface Candlestick {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BacktestParams {
  symbol: string;
  strategy: "SMA_CROSS" | "RSI_REVERSAL" | "MACD_CROSS" | "BOLLINGER_REVERSION";
  interval: "1h" | "1d";
  startingBalance: number;
  leverage: number;
  stopLossPct: number;
  takeProfitPct: number;
  smaShort?: number;
  smaLong?: number;
  rsiOversold?: number;
  rsiOverbought?: number;
}

export interface BacktestTrade {
  id: string;
  type: "LONG" | "SHORT";
  entryPrice: number;
  exitPrice: number;
  entryTimestamp: number;
  exitTimestamp: number;
  pnlUSD: number;
  pnlPct: number;
  exitReason: "SIGNAL" | "STOP_LOSS" | "TAKE_PROFIT" | "END_OF_SERIES";
}

export interface BacktestResult {
  params: BacktestParams;
  initialBalance: number;
  finalBalance: number;
  totalProfitUSD: number;
  totalProfitPct: number;
  totalTrades: number;
  winningTrades: number;
  winRate: number;
  maxDrawdown: number;
  profitFactor: number;
  trades: BacktestTrade[];
  equityCurve: { time: string; balance: number; price: number }[];
}
