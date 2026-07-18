import React from "react";
import { DollarSign, Coins, Percent, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { PortfolioData } from "../../types";

interface Props {
  portfolio: PortfolioData;
  accountNetWorthUSD: number;
  totalUnrealizedPnlUSD: number;
  netWorthReturnPct: number;
}

export function PortfolioWidget({
  portfolio,
  accountNetWorthUSD,
  totalUnrealizedPnlUSD,
  netWorthReturnPct
}: Props) {
  return (
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
  );
}
