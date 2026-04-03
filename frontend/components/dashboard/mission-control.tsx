"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import { InfraDiffViewer } from "./infra-diff-viewer";

type MissionStatus =
  | "idle"
  | "analyzing"
  | "awaiting_approval"
  | "completed"
  | "rejected"
  | "error";

interface MissionState {
  missionId: string | null;
  status: MissionStatus;
  analysis: string;
  vulnerabilityCount: number;
  proposedAction: any;
  interrupt: any;
  executionResult: any;
  error: string | null;
}

const SCENARIOS = [
  {
    id: "open-port-22",
    label: "SSH Port 22 Open",
    severity: "CRITICAL",
  },
  {
    id: "public-s3",
    label: "S3 Bucket Public",
    severity: "HIGH",
  },
  {
    id: "db-exposed",
    label: "Database Exposed",
    severity: "CRITICAL",
  },
];

export function MissionControl() {
  const [selectedScenario, setSelectedScenario] = useState("open-port-22");
  const [infraStats, setInfraStats] = useState<{
    total_vulnerabilities: number;
    security_groups: number;
    s3_buckets: number;
  } | null>(null);
  const [mission, setMission] = useState<MissionState>({
    missionId: null,
    status: "idle",
    analysis: "",
    vulnerabilityCount: 0,
    proposedAction: null,
    interrupt: null,
    executionResult: null,
    error: null,
  });

  useEffect(() => {
    fetch("/api/proxy/api/v1/infra/status")
      .then((r) => r.json())
      .then((data) =>
        setInfraStats({
          total_vulnerabilities: data.total_vulnerabilities || 0,
          security_groups: data.security_groups || 0,
          s3_buckets: data.s3_buckets || 0,
        })
      )
      .catch(() =>
        setInfraStats({ total_vulnerabilities: 4, security_groups: 2, s3_buckets: 2 })
      );
  }, []);

  const startMission = async () => {
    setMission((m) => ({ ...m, status: "analyzing", error: null }));
    try {
      const res: any = await api.missions.start(selectedScenario);
      setMission({
        missionId: res.mission_id,
        status:
          res.status === "awaiting_approval" ? "awaiting_approval" : "completed",
        analysis: res.details?.analysis || "",
        vulnerabilityCount: res.details?.vulnerability_count || 0,
        proposedAction: res.details?.proposed_action,
        interrupt: res.details?.interrupt,
        executionResult: null,
        error: null,
      });
    } catch (err: any) {
      setMission((m) => ({ ...m, status: "error", error: err.message }));
    }
  };

  const approveMission = async () => {
    if (!mission.missionId) return;
    try {
      const res: any = await api.missions.approve(mission.missionId);
      setMission((m) => ({
        ...m,
        status: "completed",
        executionResult: res.execution_result,
      }));
    } catch (err: any) {
      setMission((m) => ({ ...m, error: err.message }));
    }
  };

  const rejectMission = async () => {
    if (!mission.missionId) return;
    try {
      await api.missions.reject(mission.missionId);
      setMission((m) => ({ ...m, status: "rejected" }));
    } catch (err: any) {
      setMission((m) => ({ ...m, error: err.message }));
    }
  };

  return (
    <div className="space-y-8">
      {/* Security Posture Dashboard */}
      <div>
        <h1 className="font-brand text-[28px] tracking-[0.08em] mb-1">
          MISSION CONTROL
        </h1>
        <p
          className="text-[11px] uppercase tracking-[0.1em] mb-5"
          style={{ color: "var(--muted-foreground)" }}
        >
          AI-Powered DevSecOps — Zero-Trust Architecture
        </p>
        <div className="grid grid-cols-4 gap-3">
          <motion.div
            className="glass-card p-4 text-center"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0 }}
          >
            <p
              className="font-brand text-[24px]"
              style={{ color: "var(--aegis-red)" }}
            >
              {infraStats?.total_vulnerabilities ?? "—"}
            </p>
            <p
              className="text-[9px] uppercase tracking-[0.1em] mt-1"
              style={{ color: "var(--muted-foreground)" }}
            >
              Vulnerabilities
            </p>
          </motion.div>
          <motion.div
            className="glass-card p-4 text-center"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
          >
            <p className="font-brand text-[24px]">
              {infraStats?.security_groups ?? "—"}
            </p>
            <p
              className="text-[9px] uppercase tracking-[0.1em] mt-1"
              style={{ color: "var(--muted-foreground)" }}
            >
              Security Groups
            </p>
          </motion.div>
          <motion.div
            className="glass-card p-4 text-center"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <p className="font-brand text-[24px]">
              {infraStats?.s3_buckets ?? "—"}
            </p>
            <p
              className="text-[9px] uppercase tracking-[0.1em] mt-1"
              style={{ color: "var(--muted-foreground)" }}
            >
              S3 Buckets
            </p>
          </motion.div>
          <motion.div
            className="glass-card p-4 text-center"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <p
              className="font-brand text-[24px]"
              style={{ color: "var(--aegis-green)" }}
            >
              ✓
            </p>
            <p
              className="text-[9px] uppercase tracking-[0.1em] mt-1"
              style={{ color: "var(--muted-foreground)" }}
            >
              Double-Blind
            </p>
          </motion.div>
        </div>

        {/* Architecture Flow */}
        <div
          className="glass-card p-4 mt-3 flex items-center justify-center gap-2"
          style={{ borderColor: "var(--border)" }}
        >
          <span className="text-[10px] font-mono" style={{ color: "var(--aegis-blue)" }}>
            USER
          </span>
          <span className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>→</span>
          <span className="text-[10px] font-mono" style={{ color: "var(--muted-foreground)" }}>
            Auth0 JWT
          </span>
          <span className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>→</span>
          <span className="text-[10px] font-mono" style={{ color: "var(--aegis-amber)" }}>
            AI AGENT
          </span>
          <span className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>→</span>
          <span className="text-[10px] font-mono" style={{ color: "var(--aegis-red)" }}>
            CIBA APPROVAL
          </span>
          <span className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>→</span>
          <span className="text-[10px] font-mono" style={{ color: "var(--aegis-green)" }}>
            TOKEN VAULT
          </span>
          <span className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>→</span>
          <span className="text-[10px] font-mono" style={{ color: "var(--aegis-green)" }}>
            EXECUTE
          </span>
        </div>
      </div>

      {/* Scenario Selector */}
      <div>
        <h2 className="font-brand text-[22px] tracking-[0.08em] mb-1">
          THREAT SCENARIOS
        </h2>
        <p
          className="text-[11px] uppercase tracking-[0.1em] mb-5"
          style={{ color: "var(--muted-foreground)" }}
        >
          Select a scenario to analyze
        </p>
        <div className="grid grid-cols-3 gap-3">
          {SCENARIOS.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedScenario(s.id)}
              className="glass-card p-4 text-left transition-all duration-200"
              style={{
                borderColor:
                  selectedScenario === s.id
                    ? "var(--foreground)"
                    : "var(--border)",
              }}
              id={`scenario-${s.id}`}
            >
              <p className="text-[13px] font-medium">{s.label}</p>
              <span
                className="text-[10px] font-mono uppercase tracking-[0.08em] mt-1 inline-block"
                style={{
                  color:
                    s.severity === "CRITICAL"
                      ? "var(--aegis-red)"
                      : "var(--aegis-amber)",
                }}
              >
                {s.severity}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Launch Button */}
      <motion.button
        onClick={startMission}
        disabled={mission.status === "analyzing"}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        className="w-full py-3 rounded-md text-[12px] uppercase tracking-[0.12em] font-medium transition-all duration-200"
        style={{
          background:
            mission.status === "analyzing"
              ? "var(--card)"
              : "var(--foreground)",
          color:
            mission.status === "analyzing"
              ? "var(--muted-foreground)"
              : "var(--background)",
          border: "1px solid var(--border)",
        }}
        id="btn-start-mission"
      >
        {mission.status === "analyzing"
          ? "Analyzing..."
          : "Launch Security Scan"}
      </motion.button>

      {/* Error */}
      {mission.error && (
        <div
          className="glass-card p-4"
          style={{ borderColor: "var(--aegis-red)" }}
        >
          <p
            className="text-[11px] font-mono uppercase tracking-[0.08em]"
            style={{ color: "var(--aegis-red)" }}
          >
            Error: {mission.error}
          </p>
        </div>
      )}

      {/* Mission Status */}
      <AnimatePresence>
        {mission.status !== "idle" && mission.status !== "error" && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            {/* Status Header */}
            <div className="glass-card p-5">
              <div className="flex items-center justify-between mb-4">
                <p className="text-[11px] font-mono uppercase tracking-[0.08em]" style={{ color: "var(--muted-foreground)" }}>
                  Mission {mission.missionId || "..."}
                </p>
                <StatusBadge status={mission.status} />
              </div>

              {/* Analysis */}
              {mission.analysis && (
                <div className="pt-4 border-t" style={{ borderColor: "var(--border)" }}>
                  <p
                    className="text-[10px] font-mono uppercase tracking-[0.1em] mb-2"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    AI Analysis
                  </p>
                  <p className="text-[13px] leading-relaxed">
                    {typeof mission.analysis === "string"
                      ? mission.analysis.slice(0, 300)
                      : JSON.stringify(mission.analysis).slice(0, 300)}
                  </p>
                  {mission.vulnerabilityCount > 0 && (
                    <p
                      className="mt-3 text-[11px] font-mono"
                      style={{ color: "var(--aegis-red)" }}
                    >
                      {mission.vulnerabilityCount} vulnerabilit
                      {mission.vulnerabilityCount > 1 ? "ies" : "y"} detected
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Diff Viewer */}
            {mission.interrupt?.diff && (
              <InfraDiffViewer diff={mission.interrupt.diff} />
            )}

            {/* Approval Buttons */}
            {mission.status === "awaiting_approval" && (
              <div className="flex gap-3">
                <motion.button
                  onClick={approveMission}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className="flex-1 py-3 rounded-md text-[12px] uppercase tracking-[0.12em] font-medium"
                  style={{
                    background: "var(--foreground)",
                    color: "var(--background)",
                  }}
                  id="btn-approve"
                >
                  Approve Remediation
                </motion.button>
                <motion.button
                  onClick={rejectMission}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className="flex-1 py-3 rounded-md text-[12px] uppercase tracking-[0.12em] font-medium border"
                  style={{
                    borderColor: "var(--aegis-red)",
                    color: "var(--aegis-red)",
                    background: "transparent",
                  }}
                  id="btn-reject"
                >
                  Reject
                </motion.button>
              </div>
            )}

            {/* Execution Result */}
            {mission.executionResult && (
              <div className="glass-card p-5" style={{ borderColor: "var(--aegis-green)" }}>
                <p
                  className="text-[11px] font-mono uppercase tracking-[0.1em] mb-2"
                  style={{ color: "var(--aegis-green)" }}
                >
                  Remediation Complete
                </p>
                <p className="text-[12px] font-mono" style={{ color: "var(--muted-foreground)" }}>
                  Action: {mission.executionResult.action_taken}
                </p>
                <p className="text-[12px] font-mono" style={{ color: "var(--muted-foreground)" }}>
                  Resource: {mission.executionResult.resource_modified}
                </p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StatusBadge({ status }: { status: MissionStatus }) {
  const config: Record<MissionStatus, { color: string; label: string }> = {
    idle: { color: "var(--muted-foreground)", label: "IDLE" },
    analyzing: { color: "var(--aegis-blue)", label: "ANALYZING" },
    awaiting_approval: { color: "var(--aegis-amber)", label: "AWAITING APPROVAL" },
    completed: { color: "var(--aegis-green)", label: "COMPLETED" },
    rejected: { color: "var(--aegis-red)", label: "REJECTED" },
    error: { color: "var(--aegis-red)", label: "ERROR" },
  };
  const c = config[status];
  return (
    <span
      className="text-[10px] font-mono uppercase tracking-[0.1em]"
      style={{ color: c.color }}
    >
      {c.label}
    </span>
  );
}
