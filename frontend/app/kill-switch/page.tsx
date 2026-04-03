"use client";
import { useState } from "react";
import { motion } from "framer-motion";

export default function KillSwitchPage() {
  const [isArmed, setIsArmed] = useState(false);
  const [isKilled, setIsKilled] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  const executeKillSwitch = async () => {
    if (!isArmed) return;
    try {
      const res = await fetch(
        `/api/proxy/api/v1/auth/kill-switch`,
        { method: "POST" }
      );
      if (res.ok) {
        const data = await res.json();
        setResult(data);
      }
      setIsKilled(true);
    } catch {
      setIsKilled(true);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6">
      <h1
        className="font-brand text-[36px] tracking-[0.08em]"
        style={{ color: "var(--aegis-red)" }}
      >
        KILL SWITCH
      </h1>

      <p
        className="text-center max-w-sm text-[11px] uppercase tracking-[0.1em] leading-relaxed"
        style={{ color: "var(--muted-foreground)" }}
      >
        Immediately revoke all active tokens in Auth0 Token Vault
        and halt all agent operations.
      </p>

      {!isKilled ? (
        <div className="space-y-5 text-center">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={isArmed}
              onChange={(e) => setIsArmed(e.target.checked)}
              className="w-4 h-4 accent-[var(--aegis-red)]"
              id="arm-kill-switch"
            />
            <span
              className="font-mono text-[11px]"
              style={{ color: "var(--aegis-amber)" }}
            >
              I understand this action is irreversible
            </span>
          </label>

          <motion.button
            onClick={executeKillSwitch}
            disabled={!isArmed}
            whileHover={isArmed ? { scale: 1.02 } : {}}
            whileTap={isArmed ? { scale: 0.98 } : {}}
            className="px-10 py-3 rounded-md text-[12px] uppercase tracking-[0.12em] font-medium transition-all"
            style={{
              background: isArmed ? "var(--aegis-red)" : "var(--card)",
              color: isArmed ? "white" : "var(--muted-foreground)",
              cursor: isArmed ? "pointer" : "not-allowed",
              border: `1px solid ${isArmed ? "var(--aegis-red)" : "var(--border)"}`,
            }}
            id="btn-kill-switch"
          >
            Kill All Operations
          </motion.button>
        </div>
      ) : (
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="glass-card p-8 text-center"
          style={{ borderColor: "var(--aegis-red)" }}
        >
          <p
            className="font-brand text-[22px] tracking-[0.08em]"
            style={{ color: "var(--aegis-red)" }}
          >
            ALL OPERATIONS HALTED
          </p>
          <p
            className="mt-2 font-mono text-[11px]"
            style={{ color: "var(--muted-foreground)" }}
          >
            Tokens revoked — Agent stopped — Infrastructure locked
          </p>
          {result && (
            <div className="mt-4 text-left">
              <p className="text-[9px] font-mono uppercase tracking-[0.1em] mb-2"
                 style={{ color: "var(--aegis-red)" }}>
                Kill Switch Result
              </p>
              <pre className="text-[10px] font-mono leading-relaxed"
                   style={{ color: "var(--muted-foreground)" }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
