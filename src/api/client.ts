import { NotificationSettings, LlmSettings } from "../types";

// ==========================================
// Base Fetcher (with error handling / interceptor logic if needed)
// ==========================================
async function fetchBase(url: string, options?: RequestInit) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    // Let the global fetch interceptor handle 401 redirect to login
  }
  return response;
}

// ==========================================
// Settings & Config APIs
// ==========================================
export const apiConfig = {
  getAIConfig: async () => {
    const res = await fetchBase("/api/ai/config");
    if (!res.ok) throw new Error("Failed to fetch AI Config");
    return await res.json();
  },
  
  saveBinanceConfig: async (payload: any) => {
    const res = await fetchBase("/api/ai/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || "Failed to save Binance config");
    }
    return await res.json();
  },
  
  getNotificationSettings: async () => {
    const res = await fetchBase("/api/notifications/settings");
    if (!res.ok) throw new Error("Failed to fetch Notification settings");
    return await res.json();
  },

  saveNotificationSettings: async (settings: NotificationSettings) => {
    const res = await fetchBase("/api/notifications/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    return res.ok;
  },

  testNotification: async () => {
    const res = await fetchBase("/api/notifications/test", { method: "POST" });
    return res.ok;
  },

  getLlmSettings: async () => {
    const res = await fetchBase("/api/llm/settings");
    if (!res.ok) throw new Error("Failed to fetch LLM settings");
    return await res.json();
  },

  saveLlmSettings: async (settings: LlmSettings) => {
    const res = await fetchBase("/api/llm/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    return res.ok;
  },
};

// ==========================================
// AI Bot APIs
// ==========================================
export const apiBot = {
  getSettings: async () => {
    const res = await fetchBase("/api/ai-bot/settings");
    if (!res.ok) throw new Error("Failed to fetch Bot settings");
    const data = await res.json();
    return data.settings;
  },
  
  saveSettings: async (settings: any) => {
    const res = await fetchBase("/api/ai-bot/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    if (!res.ok) throw new Error("Failed to save Bot settings");
    return await res.json();
  },

  getStatus: async () => {
    const res = await fetchBase("/api/ai-bot/status");
    if (!res.ok) throw new Error("Failed to fetch Bot status");
    return await res.json();
  },
  
  triggerSimulation: async () => {
    const res = await fetchBase("/api/ai-bot/trigger", { method: "POST" });
    if (!res.ok) throw new Error("Failed to trigger simulation");
    return await res.json();
  },
  
  clearLogs: async () => {
    const res = await fetchBase("/api/ai-bot/logs/clear", { method: "POST" });
    if (!res.ok) throw new Error("Failed to clear logs");
    return await res.json();
  }
};
