import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Send, Loader2, Mic, MicOff, Volume2, VolumeX } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function DispatchConsole({ agent, onComplete }) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const inputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const lastResponseRef = useRef("");

  useEffect(() => {
    if (inputRef.current && !isRecording) inputRef.current.focus();
  }, [agent, isRecording]);

  const handleStreamDispatch = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || !agent) return;

    setLoading(true);
    setIsStreaming(true);
    setStreamingText("");
    lastResponseRef.current = "";

    try {
      const response = await fetch(`${API}/dispatches/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_id: agent.id, prompt: prompt.trim() }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === "chunk") {
                fullText += data.content;
                setStreamingText(fullText);
              } else if (data.type === "complete") {
                toast.success(`Dispatch to ${agent.name} completed`);
                lastResponseRef.current = fullText;
              } else if (data.type === "error") {
                toast.error(`Dispatch error: ${data.message}`);
              }
            } catch (parseErr) {
              // skip malformed SSE
            }
          }
        }
      }

      setPrompt("");
      onComplete?.();
    } catch (err) {
      toast.error("Dispatch failed: " + err.message);
    } finally {
      setLoading(false);
      setTimeout(() => {
        setIsStreaming(false);
        setStreamingText("");
      }, 500);
    }
  };

  // Voice recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      audioChunksRef.current = [];
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        await transcribeAudio(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      toast.info("Recording... click mic again to stop");
    } catch (err) {
      toast.error("Microphone access denied");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const transcribeAudio = async (blob) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("audio_file", blob, "recording.webm");
      const res = await axios.post(`${API}/voice/transcribe`, formData);
      if (res.data.text) {
        setPrompt(res.data.text);
        toast.success("Voice transcribed");
      }
    } catch (err) {
      toast.error("Transcription failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // Text-to-speech for last response
  const speakResponse = async () => {
    const text = lastResponseRef.current || streamingText;
    if (!text) { toast.error("No response to speak"); return; }
    setIsSpeaking(true);
    try {
      const res = await axios.post(`${API}/voice/speak`, { text: text.slice(0, 2000) });
      if (res.data.audio) {
        const audio = new Audio(res.data.audio);
        audio.onended = () => setIsSpeaking(false);
        audio.onerror = () => setIsSpeaking(false);
        audio.play();
      }
    } catch (err) {
      toast.error("TTS failed: " + (err.response?.data?.detail || err.message));
      setIsSpeaking(false);
    }
  };

  return (
    <div className="nexus-panel nexus-panel-active" data-testid="dispatch-console">
      <div className="p-4 border-b" style={{ borderColor: "var(--nexus-border)" }}>
        <div className="flex items-center justify-between">
          <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] font-bold" style={{ color: "var(--nexus-green)", textShadow: "0 0 8px rgba(0,255,65,0.5)" }}>
            Dispatch Console
          </h4>
          <div className="flex items-center gap-2">
            {agent && (
              <span className="font-mono text-[10px] px-2 py-0.5 border" style={{ borderColor: "var(--nexus-border)", color: "var(--nexus-cyan)" }}>
                TARGET: {agent.name}
              </span>
            )}
            <span className="font-mono text-[9px] px-1.5 py-0.5 border" style={{ borderColor: "rgba(0,255,65,0.2)", color: "var(--nexus-green)" }}>
              SSE
            </span>
          </div>
        </div>
      </div>

      <form onSubmit={handleStreamDispatch} className="p-4">
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
          {/* Voice button */}
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={loading && !isRecording}
            className="p-3 transition-all"
            style={{ color: isRecording ? "var(--nexus-red)" : "var(--nexus-text-muted)", background: isRecording ? "rgba(255,51,51,0.1)" : "transparent" }}
            data-testid="voice-record-button"
          >
            {isRecording ? <MicOff size={14} /> : <Mic size={14} />}
          </button>
          {/* TTS button */}
          <button
            type="button"
            onClick={speakResponse}
            disabled={isSpeaking || (!lastResponseRef.current && !streamingText)}
            className="p-3 transition-all disabled:opacity-30"
            style={{ color: isSpeaking ? "var(--nexus-yellow)" : "var(--nexus-cyan)" }}
            data-testid="voice-speak-button"
          >
            {isSpeaking ? <VolumeX size={14} className="animate-pulse" /> : <Volume2 size={14} />}
          </button>
          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !prompt.trim() || !agent}
            className="p-3 font-mono text-xs uppercase tracking-wider transition-all disabled:opacity-30"
            style={{ color: "var(--nexus-bg)", background: loading ? "var(--nexus-yellow)" : "var(--nexus-green)" }}
            data-testid="dispatch-submit-button"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
          </button>
        </div>

        {/* Streaming output */}
        {(isStreaming || loading) && (
          <div className="mt-3 animate-fadeIn">
            <div className="flex items-center gap-2 mb-2">
              <div className="status-dot status-busy" />
              <span className="font-mono text-[10px]" style={{ color: "var(--nexus-yellow)" }}>
                {streamingText ? "Streaming transmission..." : "Processing dispatch... awaiting transmission"}
              </span>
            </div>
            {streamingText && (
              <div className="p-3 border-l-2 font-mono text-xs whitespace-pre-wrap max-h-60 overflow-y-auto" style={{ borderColor: "var(--nexus-green)", color: "var(--nexus-text)", background: "rgba(0,255,65,0.02)" }} data-testid="streaming-output">
                {streamingText}
                <span className="animate-blink" style={{ color: "var(--nexus-green)" }}>_</span>
              </div>
            )}
          </div>
        )}
      </form>
    </div>
  );
}
