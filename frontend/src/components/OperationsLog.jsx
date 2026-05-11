import { useState, useEffect } from "react";
import axios from "axios";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ScrollText, AlertCircle, CheckCircle, Info, Clock } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_STYLES = {
  SUCCESS: { color: "var(--nexus-green)", icon: CheckCircle, label: "SUC" },
  ERROR: { color: "var(--nexus-red)", icon: AlertCircle, label: "ERR" },
  PROCESSING: { color: "var(--nexus-yellow)", icon: Clock, label: "PRC" },
  INFO: { color: "var(--nexus-cyan)", icon: Info, label: "INF" },
};

export default function OperationsLog() {
  const [operations, setOperations] = useState([]);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchOps = async () => {
    try {
      const res = await axios.get(`${API}/operations?limit=100`);
      setOperations(res.data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchOps();
    if (autoRefresh) {
      const interval = setInterval(fetchOps, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  return (
    <div className="animate-fadeIn" data-testid="operations-log-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
          <ScrollText size={14} /> Operations Log
        </h4>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className="flex items-center gap-1.5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider border transition-all"
            style={{
              borderColor: autoRefresh ? "rgba(0,255,65,0.3)" : "var(--nexus-border)",
              color: autoRefresh ? "var(--nexus-green)" : "var(--nexus-text-muted)",
              background: autoRefresh ? "rgba(0,255,65,0.05)" : "transparent"
            }}
            data-testid="auto-refresh-toggle"
          >
            <div className={`w-1.5 h-1.5 rounded-full ${autoRefresh ? "bg-[#00FF41] animate-pulse" : "bg-gray-600"}`} />
            Live {autoRefresh ? "ON" : "OFF"}
          </button>
          <span className="font-mono text-[10px]" style={{ color: "var(--nexus-text-muted)" }}>
            {operations.length} entries
          </span>
        </div>
      </div>

      {/* Log Table */}
      <div className="nexus-panel scanline-overlay" data-testid="operations-table">
        <div className="grid grid-cols-[70px_120px_120px_1fr_140px] gap-2 p-3 border-b font-mono text-[9px] uppercase tracking-wider" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-text-muted)" }}>
          <span>Status</span>
          <span>Action</span>
          <span>Agent</span>
          <span>Details</span>
          <span>Timestamp</span>
        </div>
        <ScrollArea className="max-h-[600px]">
          <div className="divide-y" style={{ borderColor: "var(--nexus-border-dim)" }}>
            {operations.map((op, i) => {
              const style = STATUS_STYLES[op.status] || STATUS_STYLES.INFO;
              const Icon = style.icon;
              return (
                <div
                  key={op.id || i}
                  className="grid grid-cols-[70px_120px_120px_1fr_140px] gap-2 p-3 items-center transition-colors hover:bg-white/[0.02] animate-fadeIn"
                  style={{ animationDelay: `${i * 0.02}s`, borderColor: "var(--nexus-border-dim)" }}
                  data-testid={`operation-row-${i}`}
                >
                  <span className="flex items-center gap-1.5">
                    <Icon size={10} style={{ color: style.color }} />
                    <span className="font-mono text-[9px] font-bold" style={{ color: style.color }}>{style.label}</span>
                  </span>
                  <span className="font-mono text-[10px] truncate" style={{ color: "var(--nexus-text-secondary)" }}>{op.action}</span>
                  <span className="font-mono text-[10px] truncate" style={{ color: "var(--nexus-cyan)" }}>{op.agent || "-"}</span>
                  <span className="font-mono text-[10px] truncate" style={{ color: "var(--nexus-text-secondary)" }}>{op.details}</span>
                  <span className="font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>
                    {new Date(op.timestamp).toLocaleString()}
                  </span>
                </div>
              );
            })}
            {operations.length === 0 && (
              <div className="text-center py-16">
                <ScrollText size={32} style={{ color: "var(--nexus-text-muted)", margin: "0 auto 8px" }} />
                <p className="font-mono text-xs" style={{ color: "var(--nexus-text-muted)" }}>No operations logged yet.</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
