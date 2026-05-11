export default function AgentAvatar({ status = "idle", size = 48 }) {
  const colors = {
    idle: { core: "#00FF41", ring: "rgba(0,255,65,0.3)", anim: "animate-breathe" },
    busy: { core: "#FFCC00", ring: "rgba(255,204,0,0.3)", anim: "animate-busy" },
    error: { core: "#FF3333", ring: "rgba(255,51,51,0.3)", anim: "" },
    offline: { core: "#52525B", ring: "rgba(82,82,91,0.3)", anim: "" },
  };

  const cfg = colors[status] || colors.idle;

  return (
    <div
      className={`relative flex items-center justify-center ${cfg.anim}`}
      style={{ width: size, height: size }}
      data-testid={`agent-avatar-${status}`}
    >
      {/* Outer ring */}
      <div
        className="absolute inset-0"
        style={{
          border: `1px solid ${cfg.ring}`,
          clipPath: "polygon(50% 0%, 93% 25%, 93% 75%, 50% 100%, 7% 75%, 7% 25%)",
        }}
      />
      {/* Inner core */}
      <div
        className="absolute"
        style={{
          width: size * 0.45,
          height: size * 0.45,
          background: cfg.core,
          clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)",
          filter: `drop-shadow(0 0 6px ${cfg.core})`,
        }}
      />
      {/* Eye indicator for idle/waiting */}
      {status === "idle" && (
        <div
          className="absolute animate-glowPulse"
          style={{
            width: size * 0.15,
            height: size * 0.15,
            background: "#fff",
            borderRadius: "50%",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
          }}
        />
      )}
    </div>
  );
}
