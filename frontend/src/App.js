import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import CommandCenter from "@/components/CommandCenter";
import MemPalace from "@/components/MemPalace";
import ForgeGallery from "@/components/ForgeGallery";
import ServiceRegistry from "@/components/ServiceRegistry";
import OperationsLog from "@/components/OperationsLog";
import ModelSwitcher from "@/components/ModelSwitcher";
import ChainBuilder from "@/components/ChainBuilder";
import PluginManager from "@/components/PluginManager";
import { Terminal, Brain, Layers, Server, ScrollText, Cpu, Activity, Link2, Puzzle, WifiOff, Wifi, ListTodo } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const NAV_ITEMS = [
  { id: "command", label: "Command", icon: Terminal },
  { id: "mempalace", label: "MemPalace", icon: Brain },
  { id: "forge", label: "Forge", icon: Layers },
  { id: "chains", label: "Chains", icon: Link2 },
  { id: "plugins", label: "Plugins", icon: Puzzle },
  { id: "services", label: "Services", icon: Server },
  { id: "operations", label: "Ops Log", icon: ScrollText },
  { id: "models", label: "Models", icon: Cpu },
];

function App() {
  const [activeTab, setActiveTab] = useState("command");
  const [agents, setAgents] = useState([]);
  const [systemInfo, setSystemInfo] = useState(null);
  const [dispatches, setDispatches] = useState([]);
  const [offlineMode, setOfflineMode] = useState(false);
  const [queueCount, setQueueCount] = useState(0);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/agents`);
      setAgents(res.data);
    } catch (e) { console.error("Failed to fetch agents", e); }
  }, []);

  const fetchSystem = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/system`);
      setSystemInfo(res.data);
    } catch (e) { console.error("Failed to fetch system info", e); }
  }, []);

  const fetchDispatches = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/dispatches?limit=20`);
      setDispatches(res.data);
    } catch (e) { console.error("Failed to fetch dispatches", e); }
  }, []);

  const fetchQueue = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/queue`);
      setQueueCount(res.data.length);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchSystem();
    fetchDispatches();
    fetchQueue();
    const interval = setInterval(() => { fetchSystem(); fetchAgents(); fetchQueue(); }, 8000);
    return () => clearInterval(interval);
  }, [fetchAgents, fetchSystem, fetchDispatches, fetchQueue]);

  const onDispatchComplete = () => {
    fetchDispatches();
    fetchAgents();
    fetchSystem();
    fetchQueue();
  };

  const handleFlushQueue = async () => {
    try {
      const res = await axios.post(`${API}/queue/flush`);
      const { toast } = await import("sonner");
      toast.success(`Flushed ${res.data.flushed} queued dispatches`);
      setOfflineMode(false);
      onDispatchComplete();
    } catch (e) { console.error(e); }
  };

  const renderContent = () => {
    switch (activeTab) {
      case "command":
        return <CommandCenter agents={agents} systemInfo={systemInfo} dispatches={dispatches} onDispatchComplete={onDispatchComplete} offlineMode={offlineMode} onQueueAdd={fetchQueue} />;
      case "mempalace":
        return <MemPalace />;
      case "forge":
        return <ForgeGallery />;
      case "chains":
        return <ChainBuilder agents={agents} onDispatchComplete={onDispatchComplete} />;
      case "plugins":
        return <PluginManager />;
      case "services":
        return <ServiceRegistry agents={agents} onUpdate={fetchAgents} />;
      case "operations":
        return <OperationsLog />;
      case "models":
        return <ModelSwitcher agents={agents} onUpdate={fetchAgents} />;
      default:
        return <CommandCenter agents={agents} systemInfo={systemInfo} dispatches={dispatches} onDispatchComplete={onDispatchComplete} offlineMode={offlineMode} onQueueAdd={fetchQueue} />;
    }
  };

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col" style={{ background: "var(--nexus-bg)" }} data-testid="app-root">
        {/* Top Bar */}
        <header className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: "var(--nexus-border)", background: "var(--nexus-surface)" }} data-testid="app-header">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-[#00FF41] animate-pulse-green" style={{ clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)" }} />
            <h1 className="font-mono text-sm font-bold tracking-[0.2em] uppercase" style={{ color: "var(--nexus-green)" }} data-testid="app-title">
              Hermes Command Nexus
            </h1>
          </div>
          <div className="flex items-center gap-4">
            {/* Offline Mode Toggle */}
            <button
              onClick={() => {
                if (offlineMode && queueCount > 0) { handleFlushQueue(); }
                else { setOfflineMode(!offlineMode); }
              }}
              className="flex items-center gap-1.5 px-2 py-1 font-mono text-[10px] uppercase tracking-wider border transition-all"
              style={{
                borderColor: offlineMode ? "rgba(255,204,0,0.3)" : "var(--nexus-border)",
                color: offlineMode ? "var(--nexus-yellow)" : "var(--nexus-text-muted)",
                background: offlineMode ? "rgba(255,204,0,0.05)" : "transparent"
              }}
              data-testid="offline-mode-toggle"
            >
              {offlineMode ? <WifiOff size={10} /> : <Wifi size={10} />}
              {offlineMode ? (queueCount > 0 ? `Flush Queue (${queueCount})` : "Offline") : "Online"}
            </button>
            <div className="flex items-center gap-2">
              <Activity size={12} style={{ color: offlineMode ? "var(--nexus-yellow)" : "var(--nexus-green)" }} />
              <span className="font-mono text-[10px] uppercase tracking-wider" style={{ color: "var(--nexus-text-secondary)" }}>
                {offlineMode ? "offline" : (systemInfo?.network || "online")}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="status-dot status-idle" />
              <span className="font-mono text-[10px] uppercase tracking-wider" style={{ color: "var(--nexus-text-secondary)" }}>
                {agents.length} agents
              </span>
            </div>
          </div>
        </header>

        {/* Navigation Tabs */}
        <nav className="flex border-b overflow-x-auto" style={{ borderColor: "var(--nexus-border)", background: "var(--nexus-bg)" }} data-testid="main-navigation">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`nav-tab flex items-center gap-2 ${activeTab === item.id ? "active" : ""}`}
                onClick={() => setActiveTab(item.id)}
                data-testid={`nav-tab-${item.id}`}
              >
                <Icon size={13} />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Main Content */}
        <main className="flex-1 p-4 overflow-auto" data-testid="main-content">
          {renderContent()}
        </main>

        <Toaster position="bottom-right" richColors />
      </div>
      <Routes>
        <Route path="*" element={null} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
