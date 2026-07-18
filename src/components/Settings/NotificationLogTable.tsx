import React from "react";
import { NotificationLog } from "../../types";
import { CheckCircle, AlertTriangle } from "lucide-react";

interface Props {
  logs: NotificationLog[];
}

export function NotificationLogTable({ logs }: Props) {
  return (
    <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/60 rounded-2xl p-6 shadow-2xl">
      <h4 className="font-sans font-bold text-white text-base mb-4">Log Pengiriman Aktivitas Notifikasi ({logs.length})</h4>
      {logs.length === 0 ? (
        <p className="text-xs text-slate-500 font-mono">Belum ada aktivitas pengiriman notifikasi dari server.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300 border-collapse">
            <thead>
              <tr className="border-b border-slate-800/80 text-slate-400 uppercase text-[10px] font-mono">
                <th className="py-3 px-4">Waktu</th>
                <th className="py-3 px-4">Saluran</th>
                <th className="py-3 px-4">Penerima</th>
                <th className="py-3 px-4">Ringkasan Pesan</th>
                <th className="py-3 px-4">Status Dispatch</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/30 font-mono">
              {logs.map((log) => {
                const isSuccess = log.status === "SUCCESS";
                const isSimulated = log.status === "SIMULATED";
                return (
                  <tr key={log.id} className="hover:bg-slate-800/20 transition">
                    <td className="py-3.5 px-4 text-slate-500">
                      {new Date(log.timestamp).toLocaleTimeString("id-ID")}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded font-bold text-[9px] ${
                        log.type === "TELEGRAM" ? "text-sky-400 bg-sky-500/10" : "text-emerald-400 bg-emerald-500/10"
                      }`}>
                        {log.type}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 max-w-[120px] truncate" title={log.recipient}>
                      {log.recipient}
                    </td>
                    <td className="py-3.5 px-4 max-w-sm truncate text-slate-400" title={log.message}>
                      {log.message}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 w-fit ${
                        isSuccess
                          ? "bg-emerald-500/10 text-emerald-400"
                          : isSimulated
                          ? "bg-slate-800 text-slate-400"
                          : "bg-red-500/10 text-red-400"
                      }`}>
                        {isSuccess && <CheckCircle className="h-3 w-3" />}
                        {!isSuccess && !isSimulated && <AlertTriangle className="h-3 w-3" />}
                        {log.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
