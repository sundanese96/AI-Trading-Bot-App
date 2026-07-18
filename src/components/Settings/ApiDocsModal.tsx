import React from "react";
import { X, Server, Zap, Shield, BookOpen, Code } from "lucide-react";

interface ApiDocsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ApiDocsModal({ isOpen, onClose }: ApiDocsModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" 
        onClick={onClose}
      />
      
      {/* Modal Container */}
      <div className="relative bg-slate-900 border border-slate-700 shadow-2xl rounded-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-400">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">9Router API Gateway Documentation</h2>
              <p className="text-xs text-slate-400 mt-1">Intelligent middleware for LLM requests</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="p-6 overflow-y-auto custom-scrollbar space-y-8">
          
          {/* System Overview */}
          <section className="space-y-4">
            <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2">
              <Server className="w-5 h-5 text-indigo-400" />
              System Overview
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              This API Gateway acts as an intelligent middleware routing Large Language Model (LLM) requests between two distinct backend servers: a synchronous local bridge (<code className="text-indigo-300">http://semburat.online</code>) and an asynchronous remote Anthropic proxy.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  <span className="font-bold text-slate-300 text-sm">Synchronous Local Routing</span>
                </div>
                <p className="text-xs text-slate-400">Automatically detects models supported by the Main Bridge and executes standard blocking requests, returning AI responses instantly.</p>
              </div>
              <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="w-4 h-4 text-emerald-400" />
                  <span className="font-bold text-slate-300 text-sm">Cloudflare Timeout Bypass</span>
                </div>
                <p className="text-xs text-slate-400">Spawns a detached background worker for heavy Anthropic models, returning a session ID immediately to prevent HTTP gateway timeouts.</p>
              </div>
            </div>
          </section>

          {/* Request & Routing Flow */}
          <section className="space-y-4">
            <h3 className="text-lg font-bold text-slate-200">Request & Routing Flow</h3>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 overflow-x-auto">
              <pre className="text-xs text-slate-300 font-mono leading-relaxed">
{`[ Frontend / Client ]
       │
       ├─► GET ?action=models ──► Aggregates models from Local (8783) & Remote (8080)
       │
       ├─► POST ?action=submit (JSON Payload: { model, prompt/messages })
       │      │
       │      ├─► Model in Local Bridge? ──► [Sync Request to 127.0.0.1:8000] ──► Returns AI Response
       │      │
       │      └─► Model in Remote Proxy? ──► Saves task to \`proxy_task_{id}.json\`
       │                                     Triggers Background Worker (\`?action=worker\`)
       │                                     Returns instantly: { "session_id": "anth_..." }
       │
       └─► GET ?action=status&id=anth_... ─► Polls \`proxy_status_{id}.json\` until status is "ready"`}
              </pre>
            </div>
          </section>

          {/* API Endpoints */}
          <section className="space-y-4">
            <h3 className="text-lg font-bold text-slate-200">API Endpoints Reference</h3>
            <p className="text-xs text-slate-400">All requests should be directed to your main router script with the action query parameter.</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left text-slate-300 border-collapse">
                <thead className="text-xs uppercase bg-slate-800/50 text-slate-400">
                  <tr>
                    <th className="px-4 py-3 border-b border-slate-700">Action</th>
                    <th className="px-4 py-3 border-b border-slate-700">Method</th>
                    <th className="px-4 py-3 border-b border-slate-700">Parameters</th>
                    <th className="px-4 py-3 border-b border-slate-700">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  <tr className="bg-slate-900/30">
                    <td className="px-4 py-3 font-mono text-indigo-400">models</td>
                    <td className="px-4 py-3"><span className="px-2 py-1 text-[10px] bg-blue-500/20 text-blue-400 rounded font-bold">GET</span></td>
                    <td className="px-4 py-3 text-xs">None</td>
                    <td className="px-4 py-3 text-xs text-slate-400">Returns a merged, deduplicated array of all available model IDs from both backends.</td>
                  </tr>
                  <tr className="bg-slate-900/30">
                    <td className="px-4 py-3 font-mono text-indigo-400">submit</td>
                    <td className="px-4 py-3"><span className="px-2 py-1 text-[10px] bg-emerald-500/20 text-emerald-400 rounded font-bold">POST</span></td>
                    <td className="px-4 py-3 text-xs">JSON Body</td>
                    <td className="px-4 py-3 text-xs text-slate-400">Submits a generation prompt. Returns raw text (Sync) or a session ID (Async).</td>
                  </tr>
                  <tr className="bg-slate-900/30">
                    <td className="px-4 py-3 font-mono text-indigo-400">status</td>
                    <td className="px-4 py-3"><span className="px-2 py-1 text-[10px] bg-blue-500/20 text-blue-400 rounded font-bold">GET</span></td>
                    <td className="px-4 py-3 text-xs">id={"{session_id}"}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">Checks generation status. Automatically deletes state files from disk once complete.</td>
                  </tr>
                  <tr className="bg-slate-900/30">
                    <td className="px-4 py-3 font-mono text-indigo-400">cleanup</td>
                    <td className="px-4 py-3"><span className="px-2 py-1 text-[10px] bg-red-500/20 text-red-400 rounded font-bold">DELETE</span></td>
                    <td className="px-4 py-3 text-xs">id={"{session_id}"}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">Manually cancels a task and deletes temporary session/status files from disk.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Code Example */}
          <section className="space-y-4">
            <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2">
              <Code className="w-5 h-5 text-indigo-400" />
              Integration & Usage Guide
            </h3>
            
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-bold text-slate-300 mb-2">1. Submit a Prompt (POST ?action=submit)</h4>
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                  <pre className="text-xs text-slate-300 font-mono">
{`{
  "model": "claude-3-5-sonnet-20241022",
  "prompt": "Explain quantum computing in three bullet points.",
  "max_tokens": 1024
}`}
                  </pre>
                </div>
              </div>
              
              <div>
                <h4 className="text-sm font-bold text-slate-300 mb-2">2. Frontend Implementation Helper (JavaScript)</h4>
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                  <pre className="text-[11px] text-slate-300 font-mono overflow-x-auto">
{`async function generateAIResponse(modelId, userPrompt) {
  const apiUrl = '/your_router_script.php'; 
  
  const submitResponse = await fetch(\`\${apiUrl}?action=submit\`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: modelId, prompt: userPrompt, max_tokens: 4096 })
  });
  
  const data = await submitResponse.json();
  
  if (data.session_id) {
    console.log(\`Async task started. Session: \${data.session_id}. Polling...\`);
    return await pollForCompletion(apiUrl, data.session_id);
  }
  
  return data; // Sync Response
}

async function pollForCompletion(apiUrl, sessionId) {
  const maxAttempts = 60; // 3 minutes total timeout
  const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    await delay(3000); 
    
    const statusRes = await fetch(\`\${apiUrl}?action=status&id=\${sessionId}\`);
    const statusData = await statusRes.json();
    
    if (statusData.status === 'ready') return statusData.result; 
    if (statusData.status === 'failed') throw new Error(statusData.result || "Failed");
    
    console.log(\`Polling \${attempt}/\${maxAttempts}: Still processing...\`);
  }
  
  await fetch(\`\${apiUrl}?action=cleanup&id=\${sessionId}\`, { method: 'DELETE' });
  throw new Error("Request timed out");
}`}
                  </pre>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/50 text-center">
          <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
            Generated by Jupris Semburat AI © 2026
          </p>
        </div>
      </div>
    </div>
  );
}
