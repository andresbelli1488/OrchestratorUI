import { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Link2, Plus, Play, Trash2, ArrowRight, Loader2, ChevronDown, ChevronUp } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ChainBuilder({ agents, onDispatchComplete }) {
  const [chains, setChains] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [chainName, setChainName] = useState("");
  const [chainDesc, setChainDesc] = useState("");
  const [steps, setSteps] = useState([{ agent_id: "", prompt_template: "" }]);
  const [executing, setExecuting] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);
  const [chainInput, setChainInput] = useState("");
  const [expandedChain, setExpandedChain] = useState(null);

  const fetchChains = async () => {
    try {
      const res = await axios.get(`${API}/chains`);
      setChains(res.data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchChains(); }, []);

  const addStep = () => setSteps([...steps, { agent_id: "", prompt_template: "" }]);
  const removeStep = (i) => setSteps(steps.filter((_, idx) => idx !== i));
  const updateStep = (i, field, value) => {
    const updated = [...steps];
    updated[i] = { ...updated[i], [field]: value };
    setSteps(updated);
  };

  const createChain = async () => {
    if (!chainName.trim() || steps.some((s) => !s.agent_id || !s.prompt_template)) {
      toast.error("Fill in all fields"); return;
    }
    try {
      await axios.post(`${API}/chains`, { name: chainName, description: chainDesc, steps });
      toast.success("Chain created");
      setChainName(""); setChainDesc(""); setSteps([{ agent_id: "", prompt_template: "" }]);
      setShowCreate(false);
      fetchChains();
    } catch (e) { toast.error("Failed to create chain"); }
  };

  const executeChain = async (chainId) => {
    setExecuting(chainId);
    setExecutionResult(null);
    try {
      const res = await axios.post(`${API}/chains/${chainId}/execute`, { input: chainInput });
      setExecutionResult(res.data);
      toast.success("Chain execution complete");
      onDispatchComplete?.();
      fetchChains();
    } catch (e) { toast.error("Chain execution failed"); }
    finally { setExecuting(null); }
  };

  const deleteChain = async (id) => {
    try {
      await axios.delete(`${API}/chains/${id}`);
      toast.success("Chain deleted");
      fetchChains();
    } catch (e) { toast.error("Failed to delete chain"); }
  };

  const getAgentName = (id) => agents.find((a) => a.id === id)?.name || "Unknown";

  return (
    <div className="animate-fadeIn" data-testid="chain-builder-page">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
          <Link2 size={14} /> Dispatch Chains
        </h4>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1.5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider border transition-all hover:bg-[#00FF41]/5"
          style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-green)" }}
          data-testid="create-chain-button"
        >
          <Plus size={12} /> New Chain
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="nexus-panel p-4 mb-4 animate-fadeIn" data-testid="chain-create-form">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <input value={chainName} onChange={(e) => setChainName(e.target.value)} placeholder="Chain Name" className="terminal-input px-3 py-2 text-xs" data-testid="chain-name-input" />
            <input value={chainDesc} onChange={(e) => setChainDesc(e.target.value)} placeholder="Description" className="terminal-input px-3 py-2 text-xs" data-testid="chain-desc-input" />
          </div>

          <div className="mb-3">
            <span className="font-mono text-[9px] uppercase tracking-wider block mb-2" style={{ color: "var(--nexus-text-muted)" }}>
              Steps (use &#123;input&#125; as placeholder for previous step output)
            </span>
            {steps.map((step, i) => (
              <div key={i} className="flex items-center gap-2 mb-2 animate-fadeIn">
                <span className="font-mono text-[10px] shrink-0 w-6 text-center" style={{ color: "var(--nexus-cyan)" }}>{i + 1}</span>
                <select
                  value={step.agent_id}
                  onChange={(e) => updateStep(i, "agent_id", e.target.value)}
                  className="terminal-input px-2 py-2 text-xs w-40"
                  style={{ background: "var(--nexus-bg)" }}
                  data-testid={`chain-step-agent-${i}`}
                >
                  <option value="">Select Agent</option>
                  {agents.map((a) => (<option key={a.id} value={a.id}>{a.name}</option>))}
                </select>
                <input
                  value={step.prompt_template}
                  onChange={(e) => updateStep(i, "prompt_template", e.target.value)}
                  placeholder="Prompt template... use {input} for chaining"
                  className="terminal-input flex-1 px-3 py-2 text-xs"
                  data-testid={`chain-step-prompt-${i}`}
                />
                {steps.length > 1 && (
                  <button onClick={() => removeStep(i)} className="p-1 hover:bg-white/5" data-testid={`chain-remove-step-${i}`}>
                    <Trash2 size={12} style={{ color: "var(--nexus-red)" }} />
                  </button>
                )}
                {i < steps.length - 1 && <ArrowRight size={14} style={{ color: "var(--nexus-green)" }} className="shrink-0" />}
              </div>
            ))}
            <button onClick={addStep} className="font-mono text-[10px] mt-1 px-2 py-1 border border-white/10 hover:border-[#00FF41]/20 transition-all" style={{ color: "var(--nexus-text-muted)" }} data-testid="chain-add-step">
              + Add Step
            </button>
          </div>

          <button onClick={createChain} className="px-4 py-2 font-mono text-xs uppercase tracking-wider" style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }} data-testid="chain-save-button">
            Create Chain
          </button>
        </div>
      )}

      {/* Chain Input */}
      <div className="nexus-panel p-4 mb-4" data-testid="chain-input-panel">
        <span className="font-mono text-[9px] uppercase tracking-wider block mb-2" style={{ color: "var(--nexus-text-muted)" }}>Chain Input (initial data fed to first step)</span>
        <textarea
          value={chainInput}
          onChange={(e) => setChainInput(e.target.value)}
          placeholder="Enter initial input for the chain..."
          className="terminal-input w-full px-3 py-2 text-xs resize-none"
          rows={2}
          data-testid="chain-initial-input"
        />
      </div>

      {/* Chains List */}
      <div className="space-y-3" data-testid="chains-list">
        {chains.map((chain) => (
          <div key={chain.id} className="nexus-panel" data-testid={`chain-card-${chain.id}`}>
            <div className="p-4 flex items-center justify-between">
              <button className="flex items-center gap-3 flex-1 text-left" onClick={() => setExpandedChain(expandedChain === chain.id ? null : chain.id)}>
                <Link2 size={14} style={{ color: "var(--nexus-cyan)" }} />
                <div>
                  <span className="font-mono text-xs font-bold block" style={{ color: "var(--nexus-text)" }}>{chain.name}</span>
                  <span className="font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>
                    {chain.steps?.length} steps | {chain.run_count || 0} runs
                  </span>
                </div>
                {expandedChain === chain.id ? <ChevronUp size={12} style={{ color: "var(--nexus-text-muted)" }} /> : <ChevronDown size={12} style={{ color: "var(--nexus-text-muted)" }} />}
              </button>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => executeChain(chain.id)}
                  disabled={executing === chain.id}
                  className="flex items-center gap-1 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider transition-all disabled:opacity-50"
                  style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }}
                  data-testid={`chain-execute-${chain.id}`}
                >
                  {executing === chain.id ? <Loader2 size={10} className="animate-spin" /> : <Play size={10} />}
                  Run
                </button>
                <button onClick={() => deleteChain(chain.id)} className="p-1.5 hover:bg-white/5" data-testid={`chain-delete-${chain.id}`}>
                  <Trash2 size={12} style={{ color: "var(--nexus-red)" }} />
                </button>
              </div>
            </div>

            {/* Expanded steps */}
            {expandedChain === chain.id && (
              <div className="px-4 pb-4 border-t animate-fadeIn" style={{ borderColor: "var(--nexus-border)" }}>
                <div className="mt-3 space-y-2">
                  {chain.steps?.map((step, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="font-mono text-[9px] shrink-0 w-5 h-5 flex items-center justify-center border" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-cyan)" }}>{i + 1}</span>
                      <span className="font-mono text-[10px] font-bold" style={{ color: "var(--nexus-green)" }}>{getAgentName(step.agent_id)}</span>
                      <ArrowRight size={10} style={{ color: "var(--nexus-text-muted)" }} />
                      <span className="font-mono text-[10px] truncate flex-1" style={{ color: "var(--nexus-text-secondary)" }}>{step.prompt_template}</span>
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
            Chain Execution Result: {executionResult.chain_name}
          </h5>
          <ScrollArea className="max-h-[400px]">
            <div className="space-y-3">
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
                  {step.error && (
                    <div className="font-mono text-xs p-2 mt-1 border-l-2" style={{ borderColor: "var(--nexus-red)", color: "var(--nexus-red)" }}>{step.error}</div>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
