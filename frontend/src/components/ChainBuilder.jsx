import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Link2, Plus, Play, Trash2, ArrowRight, ArrowDown, Loader2, ChevronDown, ChevronUp, GripVertical } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ChainBuilder({ agents, onDispatchComplete }) {
  const [chains, setChains] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [chainName, setChainName] = useState("");
  const [chainDesc, setChainDesc] = useState("");
  const [steps, setSteps] = useState([]);
  const [executing, setExecuting] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);
  const [chainInput, setChainInput] = useState("");
  const [expandedChain, setExpandedChain] = useState(null);
  const [dragIdx, setDragIdx] = useState(null);
  const [dragOverIdx, setDragOverIdx] = useState(null);

  useEffect(() => {
    if (agents.length > 0 && steps.length === 0) {
      setSteps([{ agent_id: agents[0].id, prompt_template: "" }]);
    }
  }, [agents, steps.length]);

  const fetchChains = async () => {
    try { const res = await axios.get(`${API}/chains`); setChains(res.data); } catch (e) { console.error(e); }
  };
  useEffect(() => { fetchChains(); }, []);

  const addStep = () => setSteps([...steps, { agent_id: agents.length > 0 ? agents[0].id : "", prompt_template: "" }]);
  const removeStep = (i) => { if (steps.length > 1) setSteps(steps.filter((_, idx) => idx !== i)); };
  const updateStep = (i, field, value) => { const u = [...steps]; u[i] = { ...u[i], [field]: value }; setSteps(u); };

  // Drag & Drop handlers
  const handleDragStart = (i) => setDragIdx(i);
  const handleDragOver = (e, i) => { e.preventDefault(); setDragOverIdx(i); };
  const handleDrop = (i) => {
    if (dragIdx === null || dragIdx === i) { setDragIdx(null); setDragOverIdx(null); return; }
    const newSteps = [...steps];
    const [moved] = newSteps.splice(dragIdx, 1);
    newSteps.splice(i, 0, moved);
    setSteps(newSteps);
    setDragIdx(null);
    setDragOverIdx(null);
  };
  const handleDragEnd = () => { setDragIdx(null); setDragOverIdx(null); };

  const createChain = async () => {
    if (!chainName.trim() || steps.some((s) => !s.agent_id || !s.prompt_template)) { toast.error("Fill in all fields"); return; }
    try {
      await axios.post(`${API}/chains`, { name: chainName, description: chainDesc, steps });
      toast.success("Chain created");
      setChainName(""); setChainDesc(""); setSteps([{ agent_id: agents[0]?.id || "", prompt_template: "" }]); setShowCreate(false);
      fetchChains();
    } catch (e) { toast.error("Failed to create chain"); }
  };

  const executeChain = async (chainId) => {
    setExecuting(chainId); setExecutionResult(null);
    try {
      const res = await axios.post(`${API}/chains/${chainId}/execute`, { input: chainInput }, { timeout: 120000 });
      setExecutionResult(res.data);
      toast.success("Chain execution complete");
      onDispatchComplete?.(); fetchChains();
    } catch (e) { toast.error("Chain execution failed"); }
    finally { setExecuting(null); }
  };

  const deleteChain = async (id) => {
    try { await axios.delete(`${API}/chains/${id}`); toast.success("Chain deleted"); fetchChains(); } catch (e) { toast.error("Failed to delete chain"); }
  };

  const getAgentName = (id) => agents.find((a) => a.id === id)?.name || "Unknown";
  const getAgentColor = (id) => {
    const idx = agents.findIndex((a) => a.id === id);
    const colors = ["var(--nexus-green)", "var(--nexus-cyan)", "var(--nexus-yellow)", "#FF6B6B", "#C084FC"];
    return colors[idx % colors.length];
  };

  return (
    <div className="animate-fadeIn" data-testid="chain-builder-page">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
          <Link2 size={14} /> Dispatch Chains
        </h4>
        <button onClick={() => setShowCreate(!showCreate)} className="flex items-center gap-1.5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider border transition-all hover:bg-[#00FF41]/5" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-green)" }} data-testid="create-chain-button">
          <Plus size={12} /> New Chain
        </button>
      </div>

      {/* Visual Chain Builder */}
      {showCreate && (
        <div className="nexus-panel p-4 mb-4 animate-fadeIn" data-testid="chain-create-form">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <input value={chainName} onChange={(e) => setChainName(e.target.value)} placeholder="Chain Name" className="terminal-input px-3 py-2 text-xs" data-testid="chain-name-input" />
            <input value={chainDesc} onChange={(e) => setChainDesc(e.target.value)} placeholder="Description" className="terminal-input px-3 py-2 text-xs" data-testid="chain-desc-input" />
          </div>

          <span className="font-mono text-[9px] uppercase tracking-wider block mb-3" style={{ color: "var(--nexus-text-muted)" }}>
            Drag steps to reorder. Use &#123;input&#125; for previous step output.
          </span>

          {/* Draggable steps */}
          <div className="space-y-1 mb-3">
            {steps.map((step, i) => (
              <div key={i}>
                <div
                  draggable
                  onDragStart={() => handleDragStart(i)}
                  onDragOver={(e) => handleDragOver(e, i)}
                  onDrop={() => handleDrop(i)}
                  onDragEnd={handleDragEnd}
                  className={`flex items-center gap-2 p-2 border transition-all ${dragOverIdx === i ? "border-[#00FF41]/50" : "border-white/5"} ${dragIdx === i ? "opacity-40" : "opacity-100"}`}
                  style={{ background: "var(--nexus-bg)", cursor: "grab" }}
                  data-testid={`chain-step-${i}`}
                >
                  <GripVertical size={14} style={{ color: "var(--nexus-text-muted)", cursor: "grab" }} className="shrink-0" />
                  <span className="font-mono text-[10px] font-bold shrink-0 w-6 h-6 flex items-center justify-center" style={{ color: getAgentColor(step.agent_id), border: `1px solid ${getAgentColor(step.agent_id)}40` }}>
                    {i + 1}
                  </span>
                  <select value={step.agent_id} onChange={(e) => updateStep(i, "agent_id", e.target.value)} className="terminal-input px-2 py-1.5 text-xs w-32 shrink-0" style={{ background: "var(--nexus-bg)" }} data-testid={`chain-step-agent-${i}`}>
                    <option value="">Agent</option>
                    {agents.map((a) => (<option key={a.id} value={a.id}>{a.name}</option>))}
                  </select>
                  <input value={step.prompt_template} onChange={(e) => updateStep(i, "prompt_template", e.target.value)} placeholder="Prompt... use {input} for chaining" className="terminal-input flex-1 px-2 py-1.5 text-xs" data-testid={`chain-step-prompt-${i}`} />
                  {steps.length > 1 && (
                    <button onClick={() => removeStep(i)} className="p-1 hover:bg-white/5 shrink-0" data-testid={`chain-remove-step-${i}`}>
                      <Trash2 size={12} style={{ color: "var(--nexus-red)" }} />
                    </button>
                  )}
                </div>
                {i < steps.length - 1 && (
                  <div className="flex justify-center py-0.5">
                    <ArrowDown size={14} style={{ color: "var(--nexus-text-muted)" }} />
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <button onClick={addStep} className="font-mono text-[10px] px-2 py-1 border border-white/10 hover:border-[#00FF41]/20 transition-all" style={{ color: "var(--nexus-text-muted)" }} data-testid="chain-add-step">+ Add Step</button>
            <button onClick={createChain} className="px-4 py-2 font-mono text-xs uppercase tracking-wider" style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }} data-testid="chain-save-button">Create Chain</button>
          </div>

          {/* Visual preview */}
          {steps.length > 0 && steps[0].agent_id && (
            <div className="mt-4 pt-3 border-t" style={{ borderColor: "var(--nexus-border)" }}>
              <span className="font-mono text-[9px] uppercase block mb-2" style={{ color: "var(--nexus-text-muted)" }}>Flow Preview</span>
              <div className="flex items-center gap-1 flex-wrap">
                <span className="font-mono text-[9px] px-2 py-1 border" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-text-muted)" }}>INPUT</span>
                {steps.filter(s => s.agent_id).map((step, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <ArrowRight size={10} style={{ color: "var(--nexus-text-muted)" }} />
                    <span className="font-mono text-[9px] px-2 py-1 border font-bold" style={{ borderColor: `${getAgentColor(step.agent_id)}40`, color: getAgentColor(step.agent_id) }}>
                      {getAgentName(step.agent_id)}
                    </span>
                  </div>
                ))}
                <ArrowRight size={10} style={{ color: "var(--nexus-text-muted)" }} />
                <span className="font-mono text-[9px] px-2 py-1 border" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-text-muted)" }}>OUTPUT</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Chain Input */}
      <div className="nexus-panel p-4 mb-4" data-testid="chain-input-panel">
        <span className="font-mono text-[9px] uppercase tracking-wider block mb-2" style={{ color: "var(--nexus-text-muted)" }}>Chain Input (initial data for first step)</span>
        <textarea value={chainInput} onChange={(e) => setChainInput(e.target.value)} placeholder="Enter initial input for the chain..." className="terminal-input w-full px-3 py-2 text-xs resize-none" rows={2} data-testid="chain-initial-input" />
      </div>

      {/* Chains List */}
      <div className="space-y-3" data-testid="chains-list">
        {chains.map((chain) => (
          <div key={chain.id} className="nexus-panel" data-testid={`chain-card-${chain.id}`}>
            <div className="p-4 flex items-center justify-between">
              <button className="flex items-center gap-3 flex-1 text-left" onClick={() => setExpandedChain(expandedChain === chain.id ? null : chain.id)}>
                <Link2 size={14} style={{ color: "var(--nexus-cyan)" }} />
                <div className="flex-1 min-w-0">
                  <span className="font-mono text-xs font-bold block" style={{ color: "var(--nexus-text)" }}>{chain.name}</span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>{chain.steps?.length} steps | {chain.run_count || 0} runs</span>
                    {/* Inline flow preview */}
                    <div className="flex items-center gap-0.5">
                      {chain.steps?.map((step, i) => (
                        <div key={i} className="flex items-center gap-0.5">
                          <span className="font-mono text-[8px] px-1 py-0.5" style={{ color: getAgentColor(step.agent_id), background: `${getAgentColor(step.agent_id)}10` }}>
                            {getAgentName(step.agent_id)}
                          </span>
                          {i < chain.steps.length - 1 && <ArrowRight size={8} style={{ color: "var(--nexus-text-muted)" }} />}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                {expandedChain === chain.id ? <ChevronUp size={12} style={{ color: "var(--nexus-text-muted)" }} /> : <ChevronDown size={12} style={{ color: "var(--nexus-text-muted)" }} />}
              </button>
              <div className="flex items-center gap-2">
                <button onClick={() => executeChain(chain.id)} disabled={executing === chain.id} className="flex items-center gap-1 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider transition-all disabled:opacity-50" style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }} data-testid={`chain-execute-${chain.id}`}>
                  {executing === chain.id ? <Loader2 size={10} className="animate-spin" /> : <Play size={10} />} Run
                </button>
                <button onClick={() => deleteChain(chain.id)} className="p-1.5 hover:bg-white/5" data-testid={`chain-delete-${chain.id}`}>
                  <Trash2 size={12} style={{ color: "var(--nexus-red)" }} />
                </button>
              </div>
            </div>
            {expandedChain === chain.id && (
              <div className="px-4 pb-4 border-t animate-fadeIn" style={{ borderColor: "var(--nexus-border)" }}>
                <div className="mt-3 space-y-1">
                  {chain.steps?.map((step, i) => (
                    <div key={i}>
                      <div className="flex items-center gap-2 p-2" style={{ background: "var(--nexus-bg)" }}>
                        <span className="font-mono text-[9px] shrink-0 w-5 h-5 flex items-center justify-center border" style={{ borderColor: `${getAgentColor(step.agent_id)}40`, color: getAgentColor(step.agent_id) }}>{i + 1}</span>
                        <span className="font-mono text-[10px] font-bold" style={{ color: getAgentColor(step.agent_id) }}>{getAgentName(step.agent_id)}</span>
                        <ArrowRight size={10} style={{ color: "var(--nexus-text-muted)" }} />
                        <span className="font-mono text-[10px] truncate flex-1" style={{ color: "var(--nexus-text-secondary)" }}>{step.prompt_template}</span>
                      </div>
                      {i < chain.steps.length - 1 && <div className="flex justify-center"><ArrowDown size={10} style={{ color: "var(--nexus-text-muted)" }} /></div>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
        {chains.length === 0 && (
          <div className="text-center py-16">
            <Link2 size={32} style={{ color: "var(--nexus-text-muted)", margin: "0 auto 8px" }} />
            <p className="font-mono text-xs" style={{ color: "var(--nexus-text-muted)" }}>No chains yet. Create a multi-agent workflow.</p>
          </div>
        )}
      </div>

      {/* Execution Result */}
      {executionResult && (
        <div className="nexus-panel p-4 mt-4 animate-fadeIn" data-testid="chain-execution-result">
          <h5 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-3" style={{ color: "var(--nexus-cyan)" }}>
            Chain Result: {executionResult.chain_name}
          </h5>
          <ScrollArea className="max-h-[400px]">
            <div className="space-y-2">
              {executionResult.steps?.map((step, i) => (
                <div key={i} className="border p-3" style={{ borderColor: step.status === "completed" ? "rgba(0,255,65,0.15)" : "rgba(255,51,51,0.15)", background: "var(--nexus-bg)" }}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-mono text-[9px] w-5 h-5 flex items-center justify-center border" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-cyan)" }}>{step.step + 1}</span>
                    <span className="font-mono text-[10px] font-bold" style={{ color: "var(--nexus-green)" }}>{step.agent}</span>
                    <span className="font-mono text-[9px]" style={{ color: step.status === "completed" ? "var(--nexus-green)" : "var(--nexus-red)" }}>[{step.status}]</span>
                  </div>
                  <div className="font-mono text-[10px] mb-1" style={{ color: "var(--nexus-text-muted)" }}>&gt; {step.prompt?.slice(0, 100)}{step.prompt?.length > 100 ? "..." : ""}</div>
                  {step.response && (
                    <div className="font-mono text-xs p-2 mt-1 border-l-2 whitespace-pre-wrap" style={{ borderColor: "var(--nexus-green)", color: "var(--nexus-text)", background: "rgba(0,255,65,0.02)" }}>
                      {step.response.length > 400 ? step.response.slice(0, 400) + "..." : step.response}
                    </div>
                  )}
                  {step.error && <div className="font-mono text-xs p-2 mt-1 border-l-2" style={{ borderColor: "var(--nexus-red)", color: "var(--nexus-red)" }}>{step.error}</div>}
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
