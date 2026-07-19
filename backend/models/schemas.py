from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class TriggerCrisisRequest(BaseModel):
    type: str
    headline: Optional[str] = None
    details: Optional[str] = None

class SaveTradeRequest(BaseModel):
    trade: Dict[str, Any]

class AIAnalyzeRequest(BaseModel):
    headline: str
    source: Optional[str] = None
    provider: Optional[str] = "gemini"
    customUrl: Optional[str] = None
    customKey: Optional[str] = None
    customModel: Optional[str] = None
    temperature: Optional[float] = None
    targetAsset: Optional[str] = None
    forecast: Optional[str] = ""
    previous: Optional[str] = ""

class EvaluateRequest(BaseModel):
    headline: str
    symbol: Optional[str] = "BTC"

class SaveAIConfigRequest(BaseModel):
    provider: str
    customUrl: Optional[str] = ""
    customKey: Optional[str] = ""
    customModel: Optional[str] = ""
    temperature: Optional[float] = None
    binanceApiKey: Optional[str] = ""
    binanceApiSecret: Optional[str] = ""
    dryRun: Optional[bool] = True
    maxDailyLoss: Optional[float] = 5.0
    maxTradesPerDay: Optional[int] = 5
    confidenceThreshold: Optional[int] = 75

class ExecuteOrderRequest(BaseModel):
    symbol: str
    side: str
    amountUsd: float
    leverage: int

class DownloadDataRequest(BaseModel):
    symbol: str
    startDate: str
    endDate: str

class MLTrainRequest(BaseModel):
    targetWindow: Optional[int] = 15
    thresholdPct: Optional[float] = 0.15
    modelType: Optional[str] = "xgboost"

class SaveEconomicEventRequest(BaseModel):
    id: str
    name: str
    datetime: str
    timestamp: int
    actual: Optional[str] = "N/A"
    forecast: Optional[str] = "N/A"
    impact: str
    symbol: str

class ScrapeHistoricalRequest(BaseModel):
    startDate: str
    endDate: str
    keywords: Optional[List[str]] = None

class RunDryRunRequest(BaseModel):
    headline: str
    timestamp: int
    symbol: str = "BTCUSDT"
    provider: Optional[str] = None
    customUrl: Optional[str] = None
    customKey: Optional[str] = None
    customModel: Optional[str] = None
