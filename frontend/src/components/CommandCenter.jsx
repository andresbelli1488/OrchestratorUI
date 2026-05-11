import { useState } from "react";
import axios from "axios";
import AgentAvatar from "./AgentAvatar";
import DispatchConsole from "./DispatchConsole";
import SystemPanel from "./SystemPanel";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Zap, Terminal } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function CommandCenter({ agents, systemInfo, dispatches, onDispatchComplete }) {
  const [selectedAgent, setSelectedAgent] = useState(null);

  const agentForDispatch = selectedAgent || (agents.length > 0 ? agents[0] : null);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-full animate-fadeIn" data-testid="command-center">
      {/* Left Column: Agent Status */}
      <div className="lg:col-span-3 flex flex-col gap-4">
        <div className="nexus-panel p-4 scanline-overlay" data-testid="agent-status-panel">
          <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-4" style={{ color: "var(--nexus-green)" }}>
            Agent Status
          </h4>
          <div className="flex flex-col gap-3">
            {agents.map((agent) => (
              <button
                key={agent.id}
                className={`flex items-center gap-3 p-3 border transition-all cursor-pointer ${
                  agentForDispatch?.id === agent.id
                    ? "border-[#00FF41]/50 glow-green"
                    : "border-white/5 hover:border-[#00FF41]/20"
                }`}
                style={{ background: "var(--nexus-bg)" }}
                onClick={() => setSelectedAgent(agent)}
                data-testid={`agent-card-${agent.name.toLowerCase()}`}
              >
                <AgentAvatar status={agent.status} size={40} />
                <div className="text-left flex-1 min-w-0">
                  <div className="font-mono text-xs font-bold truncate" style={{ color: "var(--nexus-text)" }}>{agent.name}</div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <div className={`status-dot status-${agent.status}`} />
                    <span className="font-mono text-[10px] uppercase" style={{ color: agent.status === "idle" ? "var(--nexus-green)" : agent.status === "busy" ? "var(--nexus-yellow)" : "var(--nexus-red)" }}>
                      {agent.status}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="font-mono text-[10px]" style={{ color: "var(--nexus-text-muted)" }}>{agent.dispatch_count} ops</span>
                </div>
              </button>
            ))}
            {agents.length === 0 && (
              <div className="text-center py-6">
                <span className="font-mono text-xs" style={{ color: "var(--nexus-text-muted)" }}>No agents registered</span>
              </div>
            )}
          </div>
        </div>

        {/* Quick Dispatch Buttons */}
        {agents.length > 0 && (
          <div className="nexus-panel p-4" data-testid="quick-dispatch-panel">
            <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-3" style={{ color: "var(--nexus-green)" }}>
              Quick Dispatch
            </h4>
            {agents.slice(0, 2).map((agent) => (
              <button
                key={agent.id}
                className="w-full flex items-center gap-2 p-2.5 mb-2 border border-white/5 font-mono text-xs transition-all hover:border-[#00FF41]/30 hover:bg-[#00FF41]/5"
                style={{ background: "var(--nexus-bg)", color: "var(--nexus-green)" }}
                onClick={() => setSelectedAgent(agent)}
                data-testid={`quick-dispatch-${agent.name.toLowerCase()}`}
              >
                <Send size={12} />
                <span>Dispatch to {agent.name}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Center Column: Dispatch Console + Transmissions */}
      <div className="lg:col-span-6 flex flex-col gap-4">
        <DispatchConsole agent={agentForDispatch} onComplete={onDispatchComplete} />

        {/* Recent Transmissions */}
        <div className="nexus-panel flex-1 flex flex-col min-h-0" data-testid="transmissions-panel">
          <div className="p-4 border-b" style={{ borderColor: "var(--nexus-border)" }}>
            <div className="flex items-center justify-between">
              <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold" style={{ color: "var(--nexus-cyan)", textShadow: "0 0 8px rgba(14,165,233,0.5)" }}>
                Transmissions
              </h4>
              <span className="font-mono text-[10px]" style={{ color: "var(--nexus-text-muted)" }}>
                {dispatches.length} records
              </span>
            </div>
          </div>
          <ScrollArea className="flex-1 max-h-[400px]">
            <div className="p-4 space-y-3">
              {dispatches.map((d, i) => (
                <div
                  key={d.id}
                  className="border p-3 animate-fadeIn"
                  style={{
                    borderColor: d.status === "completed" ? "rgba(0,255,65,0.15)" : d.status === "failed" ? "rgba(255,51,51,0.15)" : "rgba(255,204,0,0.15)",
                    background: "var(--nexus-bg)",
                    animationDelay: `${i * 0.05}s`
                  }}
                  data-testid={`transmission-${d.id}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Zap size={10} style={{ color: d.status === "completed" ? "var(--nexus-green)" : d.status === "failed" ? "var(--nexus-red)" : "var(--nexus-yellow)" }} />
                      <span className="font-mono text-[10px] font-bold uppercase" style={{ color: "var(--nexus-text-secondary)" }}>
                        {d.agent_name}
                      </span>
                      <span className="font-mono text-[10px]" style={{ color: "var(--nexus-text-muted)" }}>
                        [{d.model}]
                      </span>
                    </div>
                    <span className="font-mono text-[10px]" style={{
                      color: d.status === "completed" ? "var(--nexus-green)" : d.status === "failed" ? "var(--nexus-red)" : "var(--nexus-yellow)"
                    }}>
                      {d.status}
                    </span>
                  </div>
                  <div className="font-mono text-xs mb-2" style={{ color: "var(--nexus-text-secondary)" }}>
                    <span style={{ color: "var(--nexus-text-muted)" }}>&gt; </span>{d.prompt}
                  </div>
                  {d.response && (
                    <div className="font-mono text-xs p-2 mt-1 border-l-2 whitespace-pre-wrap" style={{
                      borderColor: d.status === "completed" ? "var(--nexus-green)" : "var(--nexus-red)",
                      color: "var(--nexus-text)",
                      background: "rgba(0,255,65,0.02)"
                    }}>
                      {d.response.length > 600 ? d.response.slice(0, 600) + "..." : d.response}
                    </div>
                  )}
                  <div className="mt-2 font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>
                    {new Date(d.created_at).toLocaleString()}
                  </div>
                </div>
              ))}
              {dispatches.length === 0 && (
                <div className="text-center py-12">
                  <Terminal size={24} style={{ color: "var(--nexus-text-muted)", margin: "0 auto 8px" }} />
                  <p className="font-mono text-xs" style={{ color: "var(--nexus-text-muted)" }}>No transmissions yet. Dispatch your first task.</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </div>

      {/* Right Column: System Panel */}
      <div className="lg:col-span-3">
        <SystemPanel systemInfo={systemInfo} />
      </div>
    </div>
  );
}
