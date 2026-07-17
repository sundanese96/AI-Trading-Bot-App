import React, { Component, ErrorInfo, ReactNode } from "react";
import { ShieldAlert, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  private handleRetry = () => {
    if (this.props.onReset) {
      this.props.onReset();
    }
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="bg-slate-900/90 border border-red-500/30 rounded-2xl p-6 my-4 shadow-xl">
          <div className="flex flex-col items-center text-center py-6">
            <div className="p-3 bg-red-500/10 text-red-400 rounded-full border border-red-500/20 mb-4 animate-bounce">
              <ShieldAlert className="h-8 w-8" />
            </div>
            <h3 className="font-sans font-extrabold text-lg text-white tracking-tight">
              {this.props.fallbackTitle || "Komponen Gagal Memuat"}
            </h3>
            <p className="text-xs text-slate-400 mt-2 max-w-md leading-relaxed">
              Sistem mendeteksi anomali render (kemungkinan 'Rendered more hooks than previous render' atau update state tidak sinkron). Error Boundary berhasil melindungi dasbor dari kehancuran total.
            </p>
            {this.state.error && (
              <pre className="mt-4 p-3 bg-black/60 border border-slate-800 rounded-xl font-mono text-[10px] text-rose-400 max-w-lg overflow-x-auto text-left w-full whitespace-pre-wrap">
                {this.state.error.toString()}
              </pre>
            )}
            <button
              onClick={this.handleRetry}
              className="mt-6 flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl active:scale-95 transition cursor-pointer shadow-lg shadow-indigo-600/15"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Reset & Muat Ulang Komponen
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
