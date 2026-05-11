import { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Puzzle, Plus, Play, Trash2, Code, Loader2, Terminal, ChevronDown, ChevronUp } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PluginManager() {
  const [plugins, setPlugins] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", script: "" });
  const [executing, setExecuting] = useState(null);
  const [inputData, setInputData] = useState({});
  const [results, setResults] = useState({});
  const [expandedPlugin, setExpandedPlugin] = useState(null);

  const fetchPlugins = async () => {
    try {
      const res = await axios.get(`${API}/plugins`);
      setPlugins(res.data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchPlugins(); }, []);

  const createPlugin = async () => {
    if (!form.name.trim() || !form.script.trim()) { toast.error("Name and script required"); return; }
    try {
      await axios.post(`${API}/plugins`, { ...form, input_schema: "text", output_schema: "text" });
      toast.success("Plugin registered");
      setForm({ name: "", description: "", script: "" });
      setShowCreate(false);
      fetchPlugins();
    } catch (e) { toast.error("Failed to create plugin"); }
  };

  const executePlugin = async (pluginId) => {
    setExecuting(pluginId);
    setResults((prev) => ({ ...prev, [pluginId]: null }));
    try {
      const res = await axios.post(`${API}/plugins/${pluginId}/execute`, { input_data: inputData[pluginId] || "" });
      setResults((prev) => ({ ...prev, [pluginId]: res.data }));
      toast.success(res.data.status === "success" ? "Plugin executed" : "Plugin had errors");
      fetchPlugins();
    } catch (e) { toast.error("Execution failed"); }
    finally { setExecuting(null); }
  };

  const deletePlugin = async (id) => {
    try {
      await axios.delete(`${API}/plugins/${id}`);
      toast.success("Plugin deleted");
      fetchPlugins();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed to delete"); }
  };

  return (
    <div className="animate-fadeIn" data-testid="plugin-manager-page">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
          <Puzzle size={14} /> Plugin System
        </h4>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1.5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider border transition-all hover:bg-[#00FF41]/5"
          style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-green)" }}
          data-testid="create-plugin-button"
        >
          <Plus size={12} /> New Plugin
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="nexus-panel p-4 mb-4 animate-fadeIn" data-testid="plugin-create-form">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Plugin Name" className="terminal-input px-3 py-2 text-xs" data-testid="plugin-name-input" />
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Description" className="terminal-input px-3 py-2 text-xs" data-testid="plugin-desc-input" />
          </div>
          <div className="mb-3">
            <span className="font-mono text-[9px] uppercase tracking-wider block mb-1" style={{ color: "var(--nexus-text-muted)" }}>
              Python Script (use INPUT variable for input data, print() for output)
            </span>
            <textarea
              value={form.script}
              onChange={(e) => setForm({ ...form, script: e.target.value })}
              placeholder={'# Example:\ntext = INPUT\nwords = text.split()\nprint(f"Word count: {len(words)}")'}
              className="terminal-input w-full px-3 py-2 text-xs resize-none font-mono"
              rows={8}
              style={{ tabSize: 4 }}
              data-testid="plugin-script-input"
            />
          </div>
          <button onClick={createPlugin} className="px-4 py-2 font-mono text-xs uppercase tracking-wider" style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }} data-testid="plugin-save-button">
            Register Plugin
          </button>
        </div>
      )}

      {/* Plugin Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="plugins-grid">
        {plugins.map((plugin) => (
          <div key={plugin.id} className="nexus-panel" data-testid={`plugin-card-${plugin.id}`}>
            {/* Header */}
            <div className="p-4 flex items-center justify-between">
              <button className="flex items-center gap-3 flex-1 text-left" onClick={() => setExpandedPlugin(expandedPlugin === plugin.id ? null : plugin.id)}>
                <div className="w-8 h-8 flex items-center justify-center border" style={{ borderColor: plugin.is_builtin ? "rgba(14,165,233,0.3)" : "var(--nexus-border)" }}>
                  {plugin.is_builtin ? <Code size={14} style={{ color: "var(--nexus-cyan)" }} /> : <Puzzle size={14} style={{ color: "var(--nexus-green)" }} />}
                </div>
                <div className="min-w-0 flex-1">
                  <span className="font-mono text-xs font-bold block truncate" style={{ color: "var(--nexus-text)" }}>{plugin.name}</span>
                  <span className="font-mono text-[9px] block truncate" style={{ color: "var(--nexus-text-muted)" }}>{plugin.description}</span>
                </div>
                {expandedPlugin === plugin.id ? <ChevronUp size={12} style={{ color: "var(--nexus-text-muted)" }} /> : <ChevronDown size={12} style={{ color: "var(--nexus-text-muted)" }} />}
              </button>
              <div className="flex items-center gap-1 ml-2">
                {plugin.is_builtin && (
                  <span className="font-mono text-[8px] uppercase px-1.5 py-0.5 border" style={{ borderColor: "rgba(14,165,233,0.2)", color: "var(--nexus-cyan)" }}>built-in</span>
                )}
                <span className="font-mono text-[8px] px-1.5 py-0.5" style={{ color: "var(--nexus-text-muted)" }}>{plugin.run_count} runs</span>
              </div>
            </div>

            {/* Expanded: Input, Execute, Results */}
            {expandedPlugin === plugin.id && (
              <div className="px-4 pb-4 border-t animate-fadeIn" style={{ borderColor: "var(--nexus-border)" }}>
                {/* Script preview */}
                <div className="mt-3 mb-3">
                  <span className="font-mono text-[9px] uppercase block mb-1" style={{ color: "var(--nexus-text-muted)" }}>Script</span>
                  <pre className="p-2 font-mono text-[10px] max-h-32 overflow-auto" style={{ background: "var(--nexus-bg)", color: "var(--nexus-text-secondary)", border: "1px solid var(--nexus-border-dim)" }}>
                    {plugin.script}
                  </pre>
                </div>

                {/* Input */}
                <textarea
                  value={inputData[plugin.id] || ""}
                  onChange={(e) => setInputData((prev) => ({ ...prev, [plugin.id]: e.target.value }))}
                  placeholder="Input data..."
                  className="terminal-input w-full px-3 py-2 text-xs resize-none mb-2"
                  rows={2}
                  data-testid={`plugin-input-${plugin.id}`}
                />

                <div className="flex items-center gap-2 mb-3">
                  <button
                    onClick={() => executePlugin(plugin.id)}
                    disabled={executing === plugin.id}
                    className="flex items-center gap-1 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider transition-all disabled:opacity-50"
                    style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }}
                    data-testid={`plugin-execute-${plugin.id}`}
                  >
                    {executing === plugin.id ? <Loader2 size={10} className="animate-spin" /> : <Play size={10} />}
                    Execute
                  </button>
                  {!plugin.is_builtin && (
                    <button onClick={() => deletePlugin(plugin.id)} className="p-1.5 hover:bg-white/5" data-testid={`plugin-delete-${plugin.id}`}>
                      <Trash2 size={12} style={{ color: "var(--nexus-red)" }} />
                    </button>
                  )}
                </div>

                {/* Result */}
                {results[plugin.id] && (
                  <div className="animate-fadeIn" data-testid={`plugin-result-${plugin.id}`}>
                    <span className="font-mono text-[9px] uppercase block mb-1" style={{ color: results[plugin.id].status === "success" ? "var(--nexus-green)" : "var(--nexus-red)" }}>
                      Output [{results[plugin.id].status}]
                    </span>
                    {results[plugin.id].output && (
                      <pre className="p-2 font-mono text-[10px] max-h-40 overflow-auto whitespace-pre-wrap" style={{ background: "var(--nexus-bg)", color: "var(--nexus-green)", border: "1px solid rgba(0,255,65,0.15)" }}>
                        {results[plugin.id].output}
                      </pre>
                    )}
                    {results[plugin.id].error && (
                      <pre className="p-2 font-mono text-[10px] max-h-40 overflow-auto whitespace-pre-wrap mt-1" style={{ background: "var(--nexus-bg)", color: "var(--nexus-red)", border: "1px solid rgba(255,51,51,0.15)" }}>
                        {results[plugin.id].error}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {plugins.length === 0 && (
          <div className="col-span-full text-center py-16">
            <Puzzle size={32} style={{ color: "var(--nexus-text-muted)", margin: "0 auto 8px" }} />
            <p className="font-mono text-xs" style={{ color: "var(--nexus-text-muted)" }}>No plugins registered.</p>
          </div>
        )}
      </div>
    </div>
  );
}
