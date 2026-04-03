"use client";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";

interface Mission {
  mission_id: string;
  scenario: string;
  status: string;
  started_at: string;
  token_source?: string;
  execution_result?: {
    success: boolean;
    action_taken: string;
    resource_modified: string;
    executed_at: string;
  };
}

export default function AuditPage() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(
      `/api/proxy/api/v1/missions/active`
    )
      .then((r) => r.json())
      .then((data) => {
        setMissions(data.missions || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "var(--aegis-green)";
      case "rejected":
        return "var(--aegis-red)";
      case "awaiting_approval":
        return "var(--aegis-amber)";
      case "killed":
        return "var(--aegis-red)";
      default:
        return "var(--muted-foreground)";
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-brand text-[28px] tracking-[0.08em]">AUDIT LOG</h1>
        <p
          className="text-[11px] uppercase tracking-[0.1em]"
          style={{ color: "var(--muted-foreground)" }}
        >
          Mission History and Compliance Trail
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Total Missions", value: missions.length },
          {
            label: "Completed",
            value: missions.filter((m) => m.status === "completed").length,
          },
          {
            label: "Rejected",
            value: missions.filter((m) => m.status === "rejected").length,
          },
          {
            label: "Token Vault Used",
            value: missions.filter((m) => m.token_source === "token-vault")
              .length,
          },
        ].map((stat) => (
          <div key={stat.label} className="glass-card p-4 text-center">
            <p className="font-brand text-[24px]">{stat.value}</p>
            <p
              className="text-[9px] uppercase tracking-[0.1em] mt-1"
              style={{ color: "var(--muted-foreground)" }}
            >
              {stat.label}
            </p>
          </div>
        ))}
      </div>

      {/* Mission timeline */}
      <div className="space-y-2">
        {loading ? (
          <p
            className="text-[11px] font-mono"
            style={{ color: "var(--muted-foreground)" }}
          >
            Loading audit trail...
          </p>
        ) : missions.length === 0 ? (
          <div className="glass-card p-8 text-center space-y-4">
            <div className="flex items-center justify-center gap-2">
              <div
                className="status-dot"
                style={{
                  background: "var(--muted-foreground)",
                  animation: "pulse 2s ease-in-out infinite",
                }}
              />
              <span
                className="text-[10px] font-mono uppercase tracking-[0.1em]"
                style={{ color: "var(--muted-foreground)" }}
              >
                Awaiting First Mission
              </span>
            </div>
            <p
              className="text-[12px]"
              style={{ color: "var(--muted-foreground)" }}
            >
              Launch a security scan from Mission Control to generate your first
              audit entry. Every agent action, approval, and rejection is
              recorded here.
            </p>
            <div className="flex items-center justify-center gap-4 pt-2">
              {["Token Vault Tracking", "CIBA Decisions", "Remediation Log"].map(
                (label) => (
                  <span
                    key={label}
                    className="text-[9px] font-mono uppercase tracking-[0.08em] px-2 py-1 glass-card"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    {label}
                  </span>
                )
              )}
            </div>
          </div>
        ) : (
          missions.map((m, i) => (
            <motion.div
              key={m.mission_id}
              className="glass-card p-4"
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-mono uppercase tracking-[0.06em]">
                    {m.mission_id}
                  </p>
                  <p
                    className="text-[10px] font-mono mt-1"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    Scenario: {m.scenario} —{" "}
                    {m.started_at?.split("T")[0] || "N/A"}
                  </p>
                </div>
                <div className="text-right">
                  <span
                    className="text-[10px] font-mono uppercase tracking-[0.08em]"
                    style={{ color: getStatusColor(m.status) }}
                  >
                    {m.status}
                  </span>
                  {m.token_source && (
                    <p
                      className="text-[9px] font-mono mt-1"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      via {m.token_source}
                    </p>
                  )}
                </div>
              </div>
              {m.execution_result && (
                <div
                  className="mt-3 pt-3 border-t"
                  style={{ borderColor: "var(--border)" }}
                >
                  <p
                    className="text-[10px] font-mono"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    Action: {m.execution_result.action_taken} on{" "}
                    {m.execution_result.resource_modified}
                  </p>
                </div>
              )}
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
}
