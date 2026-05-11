import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Send, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function DispatchConsole({ agent, onComplete }) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (inputRef.current) inputRef.current.focus();
  }, [agent]);

  const handleDispatch = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || !agent) return;

    setLoading(true);
    try {
      const res = await axios.post(`${API}/dispatches`, {
        agent_id: agent.id,
        prompt: prompt.trim(),
      });
      toast.success(`Dispatch to ${agent.name} ${res.data.status === "completed" ? "completed" : "sent"}`);
      setPrompt("");
      onComplete?.();
    } catch (err) {
      toast.error("Dispatch failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="nexus-panel nexus-panel-active" data-testid="dispatch-console">
      <div className="p-4 border-b" style={{ borderColor: "var(--nexus-border)" }}>
        <div className="flex items-center justify-between">
          <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold" style={{ color: "var(--nexus-green)", textShadow: "0 0 8px rgba(0,255,65,0.5)" }}>
            Dispatch Console
          </h4>
          {agent && (
            <span className="font-mono text-[10px] px-2 py-0.5 border" style={{
              borderColor: "var(--nexus-border)",
              color: "var(--nexus-cyan)",
            }}>
              TARGET: {agent.name}
            </span>
          )}
        </div>
      </div>

      <form onSubmit={handleDispatch} className="p-4">
        <div className="flex items-center gap-2" style={{ background: "var(--nexus-bg)" }}>
          <span className="font-mono text-xs shrink-0 pl-3" style={{ color: "var(--nexus-green)" }}>
            {agent ? `${agent.name.toLowerCase()}@nexus` : "user@nexus"}:~$
          </span>
          <input
            ref={inputRef}
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={loading || !agent}
            placeholder={agent ? `Dispatch task to ${agent.name}...` : "Select an agent first"}
            className="terminal-input flex-1 py-3 pr-3 text-sm border-0 bg-transparent"
            style={{ outline: "none", boxShadow: "none" }}
            data-testid="dispatch-input"
          />
          <button
            type="submit"
            disabled={loading || !prompt.trim() || !agent}
            className="p-3 font-mono text-xs uppercase tracking-wider transition-all disabled:opacity-30"
            style={{
              color: "var(--nexus-bg)",
              background: loading ? "var(--nexus-yellow)" : "var(--nexus-green)",
            }}
            data-testid="dispatch-submit-button"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
          </button>
        </div>
        {loading && (
          <div className="mt-2 flex items-center gap-2">
            <div className="status-dot status-busy" />
            <span className="font-mono text-[10px]" style={{ color: "var(--nexus-yellow)" }}>
              Processing dispatch... awaiting transmission
            </span>
          </div>
        )}
      </form>
    </div>
  );
}
