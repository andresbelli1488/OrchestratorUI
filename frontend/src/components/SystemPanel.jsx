import { Cpu, HardDrive, Wifi, Database, Activity, Clock } from "lucide-react";

export default function SystemPanel({ systemInfo }) {
  if (!systemInfo) {
    return (
      <div className="nexus-panel p-4" data-testid="system-panel">
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-4" style={{ color: "var(--nexus-green)" }}>
          System Monitor
        </h4>
        <div className="flex items-center justify-center py-8">
          <span className="font-mono text-xs animate-pulse" style={{ color: "var(--nexus-text-muted)" }}>Loading telemetry...</span>
        </div>
      </div>
    );
  }

  const getBarColor = (pct) => {
    if (pct > 80) return "var(--nexus-red)";
    if (pct > 50) return "var(--nexus-yellow)";
    return "var(--nexus-green)";
  };

  return (
    <div className="flex flex-col gap-4" data-testid="system-panel">
      {/* GPU Panel */}
      <div className="nexus-panel p-4 scanline-overlay">
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-4 flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
          <Cpu size={12} /> GPU Load
        </h4>
        <div className="space-y-3">
          {systemInfo.gpu_devices?.map((gpu, i) => (
            <div key={i} data-testid={`gpu-device-${i}`}>
              <div className="flex justify-between mb-1">
                <span className="font-mono text-[10px]" style={{ color: "var(--nexus-text-secondary)" }}>{gpu.name}</span>
                <span className="font-mono text-[10px] font-bold" style={{ color: getBarColor(gpu.load) }}>{gpu.load}%</span>
              </div>
              <div className="stat-bar">
                <div className="stat-bar-fill" style={{ width: `${gpu.load}%`, background: getBarColor(gpu.load) }} />
              </div>
              <div className="mt-0.5 font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>
                VRAM: {gpu.memory_used}GB / {gpu.memory_total}GB
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* RAM & Network */}
      <div className="nexus-panel p-4">
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-3 flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
          <HardDrive size={12} /> Memory
        </h4>
        <div className="flex justify-between mb-1">
          <span className="font-mono text-[10px]" style={{ color: "var(--nexus-text-secondary)" }}>RAM</span>
          <span className="font-mono text-[10px] font-bold" style={{ color: getBarColor((systemInfo.ram.used / systemInfo.ram.total) * 100) }}>
            {systemInfo.ram.used}GB / {systemInfo.ram.total}GB
          </span>
        </div>
        <div className="stat-bar">
          <div className="stat-bar-fill" style={{
            width: `${(systemInfo.ram.used / systemInfo.ram.total) * 100}%`,
            background: getBarColor((systemInfo.ram.used / systemInfo.ram.total) * 100)
          }} />
        </div>
      </div>

      {/* Network & MemPalace */}
      <div className="nexus-panel p-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between" data-testid="network-status">
            <div className="flex items-center gap-2">
              <Wifi size={12} style={{ color: "var(--nexus-green)" }} />
              <span className="font-mono text-[10px] uppercase" style={{ color: "var(--nexus-text-secondary)" }}>Network</span>
            </div>
            <span className="font-mono text-[10px] font-bold" style={{ color: systemInfo.network === "online" ? "var(--nexus-green)" : "var(--nexus-red)" }}>
              {systemInfo.network}
            </span>
          </div>
          <div className="flex items-center justify-between" data-testid="mempalace-size">
            <div className="flex items-center gap-2">
              <Database size={12} style={{ color: "var(--nexus-cyan)" }} />
              <span className="font-mono text-[10px] uppercase" style={{ color: "var(--nexus-text-secondary)" }}>MemPalace</span>
            </div>
            <span className="font-mono text-[10px] font-bold" style={{ color: "var(--nexus-cyan)" }}>
              {systemInfo.mempalace_size_mb} MB
            </span>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={12} style={{ color: "var(--nexus-yellow)" }} />
              <span className="font-mono text-[10px] uppercase" style={{ color: "var(--nexus-text-secondary)" }}>Dispatches</span>
            </div>
            <span className="font-mono text-[10px] font-bold" style={{ color: "var(--nexus-yellow)" }}>
              {systemInfo.dispatch_count}
            </span>
          </div>
        </div>
      </div>

      {/* Recent Ops */}
      <div className="nexus-panel p-4">
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-3 flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
          <Clock size={12} /> Last 5 Ops
        </h4>
        <div className="space-y-2">
          {systemInfo.recent_operations?.map((op, i) => (
            <div key={i} className="flex items-start gap-2 border-b pb-2" style={{ borderColor: "var(--nexus-border-dim)" }}>
              <span className="font-mono text-[9px] shrink-0 mt-0.5" style={{
                color: op.status === "SUCCESS" ? "var(--nexus-green)" : op.status === "ERROR" ? "var(--nexus-red)" : "var(--nexus-yellow)"
              }}>
                [{op.status?.slice(0, 3)}]
              </span>
              <div className="min-w-0 flex-1">
                <span className="font-mono text-[9px] block truncate" style={{ color: "var(--nexus-text-secondary)" }}>
                  {op.action}
                </span>
                <span className="font-mono text-[8px] block" style={{ color: "var(--nexus-text-muted)" }}>
                  {new Date(op.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))}
          {(!systemInfo.recent_operations || systemInfo.recent_operations.length === 0) && (
            <span className="font-mono text-[10px]" style={{ color: "var(--nexus-text-muted)" }}>No operations recorded</span>
          )}
        </div>
      </div>
    </div>
  );
}
