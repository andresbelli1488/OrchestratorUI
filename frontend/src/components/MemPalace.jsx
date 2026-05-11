import { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Brain, Plus, Search, Tag, Trash2, Edit3, Save, X } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function MemPalace() {
  const [notes, setNotes] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [newNote, setNewNote] = useState("");
  const [newTags, setNewTags] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editContent, setEditContent] = useState("");

  const fetchNotes = async () => {
    try {
      const res = await axios.get(`${API}/mempalace/notes`);
      setNotes(res.data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchNotes(); }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    try {
      const res = await axios.get(`${API}/mempalace/search?q=${encodeURIComponent(searchQuery)}`);
      setSearchResults(res.data);
    } catch (e) { console.error(e); }
  };

  const createNote = async () => {
    if (!newNote.trim()) return;
    try {
      await axios.post(`${API}/mempalace/notes`, {
        content: newNote.trim(),
        tags: newTags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      toast.success("Memory stored");
      setNewNote("");
      setNewTags("");
      setShowCreate(false);
      fetchNotes();
    } catch (e) { toast.error("Failed to store memory"); }
  };

  const deleteNote = async (id) => {
    try {
      await axios.delete(`${API}/mempalace/notes/${id}`);
      toast.success("Memory purged");
      fetchNotes();
    } catch (e) { toast.error("Failed to purge"); }
  };

  const saveEdit = async (id) => {
    try {
      await axios.patch(`${API}/mempalace/notes/${id}`, { content: editContent });
      toast.success("Memory updated");
      setEditingId(null);
      fetchNotes();
    } catch (e) { toast.error("Failed to update"); }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 animate-fadeIn" data-testid="mempalace-page">
      {/* Search & Create */}
      <div className="lg:col-span-4 flex flex-col gap-4">
        {/* Search */}
        <div className="nexus-panel p-4" data-testid="mempalace-search">
          <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-3 flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
            <Search size={12} /> Search MemPalace
          </h4>
          <div className="flex gap-2">
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search memories..."
              className="terminal-input flex-1 px-3 py-2 text-xs"
              data-testid="mempalace-search-input"
            />
            <button onClick={handleSearch} className="px-3 py-2 font-mono text-[10px] uppercase" style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }} data-testid="mempalace-search-button">
              <Search size={12} />
            </button>
          </div>
        </div>

        {/* Create Note */}
        <div className="nexus-panel p-4" data-testid="mempalace-create">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
              <Plus size={12} /> New Memory
            </h4>
            <button onClick={() => setShowCreate(!showCreate)} className="font-mono text-[10px]" style={{ color: "var(--nexus-cyan)" }} data-testid="toggle-create-note">
              {showCreate ? "Cancel" : "Create"}
            </button>
          </div>
          {showCreate && (
            <div className="space-y-2 animate-fadeIn">
              <textarea
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder="Remember: Hermes hates long JSON, prefers CSV..."
                className="terminal-input w-full px-3 py-2 text-xs resize-none"
                rows={4}
                data-testid="new-note-content"
              />
              <input
                value={newTags}
                onChange={(e) => setNewTags(e.target.value)}
                placeholder="Tags (comma-separated)"
                className="terminal-input w-full px-3 py-2 text-xs"
                data-testid="new-note-tags"
              />
              <button onClick={createNote} className="w-full py-2 font-mono text-xs uppercase tracking-wider" style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }} data-testid="save-note-button">
                Store Memory
              </button>
            </div>
          )}
        </div>

        {/* Search Results */}
        {searchResults && (
          <div className="nexus-panel p-4" data-testid="search-results">
            <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold mb-3" style={{ color: "var(--nexus-cyan)" }}>
              Search Results
            </h4>
            <div className="space-y-2">
              {searchResults.notes?.length > 0 && (
                <div>
                  <span className="font-mono text-[9px] uppercase" style={{ color: "var(--nexus-text-muted)" }}>Notes ({searchResults.notes.length})</span>
                  {searchResults.notes.map((n) => (
                    <div key={n.id} className="border p-2 mt-1 font-mono text-xs" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-text-secondary)" }}>
                      {n.content.slice(0, 100)}
                    </div>
                  ))}
                </div>
              )}
              {searchResults.transmissions?.length > 0 && (
                <div>
                  <span className="font-mono text-[9px] uppercase" style={{ color: "var(--nexus-text-muted)" }}>Transmissions ({searchResults.transmissions.length})</span>
                  {searchResults.transmissions.map((t) => (
                    <div key={t.id} className="border p-2 mt-1 font-mono text-xs" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-text-secondary)" }}>
                      <span style={{ color: "var(--nexus-green)" }}>{t.agent_name}:</span> {t.prompt.slice(0, 80)}
                    </div>
                  ))}
                </div>
              )}
              {searchResults.notes?.length === 0 && searchResults.transmissions?.length === 0 && (
                <span className="font-mono text-[10px]" style={{ color: "var(--nexus-text-muted)" }}>No results found</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Notes List */}
      <div className="lg:col-span-8">
        <div className="nexus-panel" data-testid="notes-list">
          <div className="p-4 border-b" style={{ borderColor: "var(--nexus-border)" }}>
            <div className="flex items-center justify-between">
              <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold flex items-center gap-2" style={{ color: "var(--nexus-green)" }}>
                <Brain size={12} /> Stored Memories
              </h4>
              <span className="font-mono text-[10px]" style={{ color: "var(--nexus-text-muted)" }}>
                {notes.length} entries
              </span>
            </div>
          </div>
          <ScrollArea className="max-h-[600px]">
            <div className="p-4 space-y-3">
              {notes.map((note) => (
                <div key={note.id} className="border p-3" style={{ borderColor: "var(--nexus-border)", background: "var(--nexus-bg)" }} data-testid={`note-${note.id}`}>
                  {editingId === note.id ? (
                    <div className="space-y-2">
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="terminal-input w-full px-3 py-2 text-xs resize-none"
                        rows={3}
                        data-testid="edit-note-input"
                      />
                      <div className="flex gap-2">
                        <button onClick={() => saveEdit(note.id)} className="px-3 py-1 font-mono text-[10px]" style={{ background: "var(--nexus-green)", color: "var(--nexus-bg)" }} data-testid="save-edit-button">
                          <Save size={10} />
                        </button>
                        <button onClick={() => setEditingId(null)} className="px-3 py-1 font-mono text-[10px]" style={{ background: "var(--nexus-red)", color: "#fff" }} data-testid="cancel-edit-button">
                          <X size={10} />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="font-mono text-xs whitespace-pre-wrap" style={{ color: "var(--nexus-text)" }}>
                        {note.content}
                      </p>
                      {note.tags?.length > 0 && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {note.tags.map((tag, i) => (
                            <span key={i} className="px-1.5 py-0.5 font-mono text-[9px] uppercase border" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-cyan)" }}>
                              <Tag size={8} className="inline mr-1" />{tag}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center justify-between mt-2">
                        <span className="font-mono text-[9px]" style={{ color: "var(--nexus-text-muted)" }}>
                          {new Date(note.created_at).toLocaleString()}
                        </span>
                        <div className="flex gap-2">
                          <button onClick={() => { setEditingId(note.id); setEditContent(note.content); }} className="p-1 transition-colors hover:bg-white/5" data-testid={`edit-note-${note.id}`}>
                            <Edit3 size={10} style={{ color: "var(--nexus-text-muted)" }} />
                          </button>
                          <button onClick={() => deleteNote(note.id)} className="p-1 transition-colors hover:bg-white/5" data-testid={`delete-note-${note.id}`}>
                            <Trash2 size={10} style={{ color: "var(--nexus-red)" }} />
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ))}
              {notes.length === 0 && (
                <div className="text-center py-12">
                  <Brain size={24} style={{ color: "var(--nexus-text-muted)", margin: "0 auto 8px" }} />
                  <p className="font-mono text-xs" style={{ color: "var(--nexus-text-muted)" }}>MemPalace is empty. Store your first memory.</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  );
}
