import { useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";
import AgentAvatar from "./AgentAvatar";
import { Server, Plus, Shield, Zap } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ServiceRegistry({ agents, onUpdate }) {
  const [showRegister, setShowRegister] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", operations: "", preferred_model: "gpt-5.2", preferred_provider: "openai" });

  const registerAgent = async () => {
    if (!form.name.trim()) return;
    try {
      await axios.post(`${API}/agents`, {
        ...form,
        operations: form.operations.split(",").map((o) => o.trim()).filter(Boolean),
      });
      toast.success(`${form.name} registered as service`);
      setForm({ name: "", description: "", operations: "", preferred_model: "gpt-5.2", preferred_provider: "openai" });
      setShowRegister(false);
      onUpdate?.();
    } catch (e) { toast.error("Registration failed"); }
  };

  return (
    <div className="animate-fadeIn" data-testid="service-registry-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
          <Server size={14} /> Service Registry
        </h4>
        <button
          onClick={() => setShowRegister(!showRegister)}
          className="flex items-center gap-1.5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider border transition-all hover:bg-[#00FF41]/5"
          style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-green)" }}
          data-testid="register-service-button"
        >
          <Plus size={12} /> Register Service
        </button>
      </div>

      {/* Registration Form */}
      {showRegister && (
        <div className="nexus-panel p-4 mb-4 animate-fadeIn" data-testid="register-form">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Service Name (e.g. Atlas)"
              className="terminal-input px-3 py-2 text-xs"
              data-testid="register-name-input"
            />
            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Description"
              className="terminal-input px-3 py-2 text-xs"
              data-testid="register-description-input"
            />
            <input
              value={form.operations}
              onChange={(e) => setForm({ ...form, operations: e.target.value })}
              placeholder="Operations (comma-separated)"
              className="terminal-input px-3 py-2 text-xs"
              data-testid="register-operations-input"
            />
            <select
              value={form.preferred_provider}
              onChange={(e) => setForm({ ...form, preferred_provider: e.target.value })}
              className="terminal-input px-3 py-2 text-xs"
              style={{ background: "var(--nexus-bg)" }}
              data-testid="register-provider-select"
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="gemini">Gemini</option>
            </select>
          </div>
          <button
            onClick={registerAgent}
            className="mt-3 px-4 py-2 font-mono text-xs uppercase tracking-wider"
            style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }}
            data-testid="register-submit-button"
          >
            Register
          </button>
        </div>
      )}

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="services-grid">
        {agents.map((agent) => (
          <div key={agent.id} className="nexus-panel p-4" data-testid={`service-card-${agent.name.toLowerCase()}`}>
            <div className="flex items-center gap-3 mb-3">
              <AgentAvatar status={agent.status} size={36} />
              <div>
                <h5 className="font-mono text-sm font-bold" style={{ color: "var(--nexus-text)" }}>{agent.name}</h5>
                <div className="flex items-center gap-1.5">
                  <div className={`status-dot status-${agent.status}`} />
                  <span className="font-mono text-[10px] uppercase" style={{ color: agent.status === "idle" ? "var(--nexus-green)" : agent.status === "busy" ? "var(--nexus-yellow)" : "var(--nexus-red)" }}>
                    {agent.status}
                  </span>
                </div>
              </div>
            </div>

            <p className="font-mono text-[10px] mb-3" style={{ color: "var(--nexus-text-secondary)" }}>
              {agent.description}
            </p>

            {/* Operations */}
            {agent.operations?.length > 0 && (
              <div className="mb-3">
                <span className="font-mono text-[9px] uppercase block mb-1" style={{ color: "var(--nexus-text-muted)" }}>Operations</span>
                <div className="flex flex-wrap gap-1">
                  {agent.operations.map((op, i) => (
                    <span key={i} className="flex items-center gap-1 px-1.5 py-0.5 border font-mono text-[9px]" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-cyan)" }}>
                      <Zap size={8} />{op}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Model Info */}
            <div className="flex items-center justify-between pt-2 border-t" style={{ borderColor: "var(--nexus-border-dim)" }}>
              <div className="flex items-center gap-1">
                <Shield size={10} style={{ color: "var(--nexus-text-muted)" }} />
                <span className="font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>
                  {agent.preferred_provider}/{agent.preferred_model}
                </span>
              </div>
              <span className="font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>
                {agent.dispatch_count} dispatches
              </span>
            </div>
          </div>
        ))}
        {agents.length === 0 && (
          <div className="col-span-full text-center py-16">
            <Server size={32} style={{ color: "var(--nexus-text-muted)", margin: "0 auto 8px" }} />
            <p className="font-mono text-xs" style={{ color: "var(--nexus-text-muted)" }}>No services registered.</p>
          </div>
        )}
      </div>
    </div>
  );
}
