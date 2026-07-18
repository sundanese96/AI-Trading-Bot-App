import React, { useState } from "react";
import { NotificationLog } from "../../types";
import { CheckCircle, AlertTriangle } from "lucide-react";

interface Props {
  logs: NotificationLog[];
}

export function NotificationLogTable({ logs }: Props) {
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const totalPages = Math.max(1, Math.ceil(logs.length / rowsPerPage));
  const startIndex = (currentPage - 1) * rowsPerPage;
  const sortedLogs = [...logs].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  const currentLogs = sortedLogs.slice(startIndex, startIndex + rowsPerPage);

  return (
    <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/60 rounded-2xl p-6 shadow-2xl">
      <div className="flex justify-between items-center mb-4">
        <h4 className="font-sans font-bold text-white text-base">Log Pengiriman Aktivitas Notifikasi ({logs.length})</h4>
        
        {logs.length > 0 && (
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Tampilkan:</span>
            <select
              value={rowsPerPage}
              onChange={(e) => {
                setRowsPerPage(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 outline-none focus:border-indigo-500"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
        )}
      </div>

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
              {currentLogs.map((log) => {
                const isSuccess = log.status === "SUCCESS";
                const isSimulated = log.status === "SIMULATED";
                return (
                  <tr key={log.id} className="hover:bg-slate-800/20 transition">
                    <td className="py-3.5 px-4 text-slate-500">
                      {new Date(log.timestamp).toLocaleString("id-ID", { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}
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

      {/* Pagination Controls */}
      {logs.length > 0 && (
        <div className="flex justify-between items-center mt-4 pt-4 border-t border-slate-800/60 text-xs font-mono">
          <span className="text-slate-500">
            Menampilkan {startIndex + 1} - {Math.min(startIndex + rowsPerPage, logs.length)} dari {logs.length}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 bg-slate-800 text-slate-300 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700 transition"
            >
              Prev
            </button>
            <span className="text-slate-400 font-bold px-2">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 bg-slate-800 text-slate-300 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700 transition"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
