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
import { Terminal, Brain, Layers, Server, ScrollText, Cpu, Activity } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const NAV_ITEMS = [
  { id: "command", label: "Command", icon: Terminal },
  { id: "mempalace", label: "MemPalace", icon: Brain },
  { id: "forge", label: "Forge", icon: Layers },
  { id: "services", label: "Services", icon: Server },
  { id: "operations", label: "Ops Log", icon: ScrollText },
  { id: "models", label: "Models", icon: Cpu },
];

function App() {
  const [activeTab, setActiveTab] = useState("command");
  const [agents, setAgents] = useState([]);
  const [systemInfo, setSystemInfo] = useState(null);
  const [dispatches, setDispatches] = useState([]);

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

  useEffect(() => {
    fetchAgents();
    fetchSystem();
    fetchDispatches();
    const interval = setInterval(() => { fetchSystem(); fetchAgents(); }, 8000);
    return () => clearInterval(interval);
  }, [fetchAgents, fetchSystem, fetchDispatches]);

  const onDispatchComplete = () => {
    fetchDispatches();
    fetchAgents();
    fetchSystem();
  };

  const renderContent = () => {
    switch (activeTab) {
      case "command":
        return <CommandCenter agents={agents} systemInfo={systemInfo} dispatches={dispatches} onDispatchComplete={onDispatchComplete} />;
      case "mempalace":
        return <MemPalace />;
      case "forge":
        return <ForgeGallery />;
      case "services":
        return <ServiceRegistry agents={agents} onUpdate={fetchAgents} />;
      case "operations":
        return <OperationsLog />;
      case "models":
        return <ModelSwitcher agents={agents} onUpdate={fetchAgents} />;
      default:
        return <CommandCenter agents={agents} systemInfo={systemInfo} dispatches={dispatches} onDispatchComplete={onDispatchComplete} />;
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
            <div className="flex items-center gap-2">
              <Activity size={12} style={{ color: "var(--nexus-green)" }} />
              <span className="font-mono text-[10px] uppercase tracking-wider" style={{ color: "var(--nexus-text-secondary)" }}>
                {systemInfo?.network || "online"}
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
