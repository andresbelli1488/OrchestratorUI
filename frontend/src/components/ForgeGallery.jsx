import { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Layers, Plus, Trash2, ExternalLink, Tag, Image, Code, FileText, Sparkles, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TYPE_ICONS = { image: Image, code: Code, document: FileText, design: Layers };

export default function ForgeGallery() {
  const [items, setItems] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);
  const [form, setForm] = useState({ title: "", type: "image", url: "", tags: "", source_agent: "", description: "" });
  const [genForm, setGenForm] = useState({ prompt: "", provider: "openai", title: "", tags: "" });
  const [generating, setGenerating] = useState(false);

  const fetchItems = async () => {
    try { const res = await axios.get(`${API}/forge`); setItems(res.data); } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchItems(); }, []);

  const createItem = async () => {
    if (!form.title.trim()) return;
    try {
      await axios.post(`${API}/forge`, { ...form, tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean) });
      toast.success("Output added to Forge");
      setForm({ title: "", type: "image", url: "", tags: "", source_agent: "", description: "" });
      setShowCreate(false);
      fetchItems();
    } catch (e) { toast.error("Failed to add to Forge"); }
  };

  const generateImage = async () => {
    if (!genForm.prompt.trim()) { toast.error("Enter a prompt"); return; }
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/forge/generate`, {
        prompt: genForm.prompt,
        provider: genForm.provider,
        title: genForm.title || undefined,
        tags: genForm.tags.split(",").map((t) => t.trim()).filter(Boolean),
      }, { timeout: 120000 });
      toast.success(`Image generated via ${genForm.provider}`);
      setGenForm({ prompt: "", provider: "openai", title: "", tags: "" });
      setShowGenerate(false);
      fetchItems();
    } catch (e) { toast.error("Generation failed: " + (e.response?.data?.detail || e.message)); }
    finally { setGenerating(false); }
  };

  const deleteItem = async (id) => {
    try { await axios.delete(`${API}/forge/${id}`); toast.success("Item removed"); fetchItems(); } catch (e) { toast.error("Failed to remove"); }
  };

  return (
    <div className="animate-fadeIn" data-testid="forge-gallery-page">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
          <Layers size={14} /> Forge Output Gallery
        </h4>
        <div className="flex gap-2">
          <button onClick={() => { setShowGenerate(!showGenerate); setShowCreate(false); }} className="flex items-center gap-1.5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider border transition-all hover:bg-[#0EA5E9]/5" style={{ borderColor: showGenerate ? "rgba(14,165,233,0.5)" : "var(--nexus-border)", color: "var(--nexus-cyan)" }} data-testid="forge-generate-button">
            <Sparkles size={12} /> Generate Image
          </button>
          <button onClick={() => { setShowCreate(!showCreate); setShowGenerate(false); }} className="flex items-center gap-1.5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider border transition-all hover:bg-[#00FF41]/5" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-green)" }} data-testid="forge-add-button">
            <Plus size={12} /> Add Output
          </button>
        </div>
      </div>

      {/* Image Generation Form */}
      {showGenerate && (
        <div className="nexus-panel p-4 mb-4 animate-fadeIn" style={{ borderColor: "rgba(14,165,233,0.3)" }} data-testid="forge-generate-form">
          <h5 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-3 flex items-center gap-2" style={{ color: "var(--nexus-cyan)" }}>
            <Sparkles size={12} /> AI Image Generation
          </h5>
          <textarea value={genForm.prompt} onChange={(e) => setGenForm({ ...genForm, prompt: e.target.value })} placeholder="Describe the image you want to generate..." className="terminal-input w-full px-3 py-2 text-xs resize-none mb-3" rows={3} data-testid="forge-gen-prompt" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
            <div>
              <span className="font-mono text-[9px] uppercase block mb-1" style={{ color: "var(--nexus-text-muted)" }}>Provider</span>
              <div className="flex gap-2">
                {[
                  { id: "openai", label: "GPT Image 1" },
                  { id: "gemini", label: "Nano Banana" }
                ].map((p) => (
                  <button key={p.id} type="button" onClick={() => setGenForm({ ...genForm, provider: p.id })} className={`flex-1 py-2 px-2 font-mono text-[10px] border transition-all ${genForm.provider === p.id ? "border-[#0EA5E9]/50 glow-cyan" : "border-white/5 hover:border-white/10"}`} style={{ background: "var(--nexus-bg)", color: genForm.provider === p.id ? "var(--nexus-cyan)" : "var(--nexus-text-muted)" }} data-testid={`forge-gen-provider-${p.id}`}>
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <input value={genForm.title} onChange={(e) => setGenForm({ ...genForm, title: e.target.value })} placeholder="Title (optional)" className="terminal-input px-3 py-2 text-xs" data-testid="forge-gen-title" />
            <input value={genForm.tags} onChange={(e) => setGenForm({ ...genForm, tags: e.target.value })} placeholder="Tags (comma-separated)" className="terminal-input px-3 py-2 text-xs" data-testid="forge-gen-tags" />
          </div>
          <button onClick={generateImage} disabled={generating || !genForm.prompt.trim()} className="flex items-center gap-2 px-4 py-2 font-mono text-xs uppercase tracking-wider transition-all disabled:opacity-50" style={{ background: "var(--nexus-cyan)", color: "var(--nexus-bg)" }} data-testid="forge-gen-submit">
            {generating ? <><Loader2 size={12} className="animate-spin" /> Generating...</> : <><Sparkles size={12} /> Generate</>}
          </button>
          {generating && (
            <div className="mt-2 flex items-center gap-2">
              <div className="status-dot status-busy" />
              <span className="font-mono text-[10px]" style={{ color: "var(--nexus-yellow)" }}>AI is generating your image... this may take up to 60 seconds</span>
            </div>
          )}
        </div>
      )}

      {/* Manual Create Form */}
      {showCreate && (
        <div className="nexus-panel p-4 mb-4 animate-fadeIn" data-testid="forge-create-form">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Title" className="terminal-input px-3 py-2 text-xs" data-testid="forge-title-input" />
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="terminal-input px-3 py-2 text-xs" style={{ background: "var(--nexus-bg)" }} data-testid="forge-type-select">
              <option value="image">Image</option><option value="code">Code</option><option value="document">Document</option><option value="design">Design</option>
            </select>
            <input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="URL (optional)" className="terminal-input px-3 py-2 text-xs" data-testid="forge-url-input" />
            <input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="Tags" className="terminal-input px-3 py-2 text-xs" data-testid="forge-tags-input" />
            <input value={form.source_agent} onChange={(e) => setForm({ ...form, source_agent: e.target.value })} placeholder="Source Agent" className="terminal-input px-3 py-2 text-xs" data-testid="forge-agent-input" />
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Description" className="terminal-input px-3 py-2 text-xs" data-testid="forge-description-input" />
          </div>
          <button onClick={createItem} className="mt-3 px-4 py-2 font-mono text-xs uppercase tracking-wider" style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }} data-testid="forge-save-button">Add to Forge</button>
        </div>
      )}

      {/* Gallery Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" data-testid="forge-grid">
        {items.map((item) => {
          const TypeIcon = TYPE_ICONS[item.type] || FileText;
          const isGenerated = item.tags?.includes("ai-generated");
          return (
            <div key={item.id} className="nexus-panel forge-item overflow-hidden" data-testid={`forge-item-${item.id}`}>
              {item.url && item.type === "image" ? (
                <div className="aspect-video overflow-hidden" style={{ background: "var(--nexus-bg)" }}>
                  <img src={item.url} alt={item.title} className="w-full h-full object-cover opacity-80 hover:opacity-100 transition-opacity" loading="lazy" />
                </div>
              ) : (
                <div className="aspect-video flex items-center justify-center" style={{ background: "var(--nexus-bg)" }}>
                  <TypeIcon size={32} style={{ color: "var(--nexus-text-muted)" }} />
                </div>
              )}
              <div className="p-3">
                <div className="flex items-center justify-between mb-1">
                  <h5 className="font-mono text-xs font-bold truncate" style={{ color: "var(--nexus-text)" }}>{item.title}</h5>
                  <div className="flex gap-1">
                    {item.url && (
                      <a href={item.url} target="_blank" rel="noopener noreferrer" className="p-1 hover:bg-white/5"><ExternalLink size={10} style={{ color: "var(--nexus-cyan)" }} /></a>
                    )}
                    <button onClick={() => deleteItem(item.id)} className="p-1 hover:bg-white/5" data-testid={`forge-delete-${item.id}`}>
                      <Trash2 size={10} style={{ color: "var(--nexus-red)" }} />
                    </button>
                  </div>
                </div>
                {item.description && <p className="font-mono text-[10px] mb-1 truncate" style={{ color: "var(--nexus-text-secondary)" }}>{item.description}</p>}
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span className="font-mono text-[9px] uppercase px-1.5 py-0.5 border" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-cyan)" }}>{item.type}</span>
                  {isGenerated && <span className="font-mono text-[8px] uppercase px-1 py-0.5 border" style={{ borderColor: "rgba(14,165,233,0.2)", color: "var(--nexus-cyan)" }}>AI</span>}
                  {item.source_agent && <span className="font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>via {item.source_agent}</span>}
                </div>
                {item.tags?.length > 0 && (
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {item.tags.filter(t => t !== "ai-generated").map((tag, i) => (
                      <span key={i} className="font-mono text-[8px] px-1 py-0.5 border" style={{ borderColor: "var(--nexus-border-dim)", color: "var(--nexus-text-muted)" }}>{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {items.length === 0 && (
          <div className="col-span-full text-center py-16">
            <Layers size={32} style={{ color: "var(--nexus-text-muted)", margin: "0 auto 8px" }} />
            <p className="font-mono text-xs" style={{ color: "var(--nexus-text-muted)" }}>Forge is empty. Generate images or add outputs.</p>
          </div>
        )}
      </div>
    </div>
  );
}
