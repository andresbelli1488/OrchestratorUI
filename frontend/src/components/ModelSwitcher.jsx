import { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Cpu, Check, ArrowRight } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ModelSwitcher({ agents, onUpdate }) {
  const [models, setModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await axios.get(`${API}/models`);
        setModels(res.data);
      } catch (e) { console.error(e); }
      finally { setModelsLoading(false); }
    };
    fetchModels();
  }, []);

  useEffect(() => {
    if (agents.length > 0 && !selectedAgent) {
      setSelectedAgent(agents[0]);
    }
  }, [agents, selectedAgent]);

  const switchModel = async (provider, model) => {
    if (!selectedAgent) return;
    try {
      await axios.patch(`${API}/agents/${selectedAgent.id}`, {
        preferred_model: model,
        preferred_provider: provider,
      });
      toast.success(`${selectedAgent.name} now uses ${provider}/${model}`);
      onUpdate?.();
      setSelectedAgent((prev) => ({ ...prev, preferred_model: model, preferred_provider: provider }));
    } catch (e) { toast.error("Failed to switch model"); }
  };

  return (
    <div className="animate-fadeIn" data-testid="model-switcher-page">
      <div className="flex items-center gap-2 mb-4">
        <Cpu size={14} style={{ color: "var(--nexus-green)" }} />
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold" style={{ color: "var(--nexus-green)" }}>
          Model Switcher
        </h4>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Agent Selection */}
        <div className="lg:col-span-4">
          <div className="nexus-panel p-4" data-testid="model-agent-selector">
            <h5 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-3" style={{ color: "var(--nexus-text-secondary)" }}>
              Select Agent
            </h5>
            <div className="space-y-2">
              {agents.map((agent) => (
                <button
                  key={agent.id}
                  className={`w-full flex items-center justify-between p-3 border transition-all text-left ${
                    selectedAgent?.id === agent.id ? "border-[#00FF41]/50 glow-green" : "border-white/5 hover:border-[#00FF41]/20"
                  }`}
                  style={{ background: "var(--nexus-bg)" }}
                  onClick={() => setSelectedAgent(agent)}
                  data-testid={`model-agent-${agent.name.toLowerCase()}`}
                >
                  <div>
                    <span className="font-mono text-xs font-bold block" style={{ color: "var(--nexus-text)" }}>{agent.name}</span>
                    <span className="font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>
                      {agent.preferred_provider}/{agent.preferred_model}
                    </span>
                  </div>
                  {selectedAgent?.id === agent.id && <ArrowRight size={12} style={{ color: "var(--nexus-green)" }} />}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Model Grid */}
        <div className="lg:col-span-8">
          <div className="nexus-panel p-4" data-testid="model-grid">
            <h5 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-3" style={{ color: "var(--nexus-text-secondary)" }}>
              Available Models {selectedAgent && <span style={{ color: "var(--nexus-cyan)" }}>for {selectedAgent.name}</span>}
            </h5>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {modelsLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="p-3 border border-white/5 animate-pulse" style={{ background: "var(--nexus-bg)" }}>
                    <div className="h-4 w-32 bg-white/5 mb-2" />
                    <div className="h-3 w-20 bg-white/5" />
                  </div>
                ))
              ) : models.map((m, i) => {
                const isActive = selectedAgent?.preferred_model === m.model && selectedAgent?.preferred_provider === m.provider;
                return (
                  <button
                    key={i}
                    className={`flex items-center justify-between p-3 border transition-all text-left ${
                      isActive ? "border-[#00FF41]/50 glow-green" : "border-white/5 hover:border-[#00FF41]/20"
                    }`}
                    style={{ background: "var(--nexus-bg)" }}
                    onClick={() => switchModel(m.provider, m.model)}
                    data-testid={`model-option-${m.model}`}
                  >
                    <div>
                      <span className="font-mono text-xs font-bold block" style={{ color: isActive ? "var(--nexus-green)" : "var(--nexus-text)" }}>
                        {m.label}
                      </span>
                      <span className="font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>
                        {m.provider} / {m.model}
                      </span>
                    </div>
                    {isActive && <Check size={14} style={{ color: "var(--nexus-green)" }} />}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
