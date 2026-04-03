"use client";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";

interface VulnerabilityItem {
  resource_type: string;
  resource_id: string;
  resource_name: string;
  severity: string;
  risk_score: number;
  cis_benchmark: string;
  description: string;
}

interface InfraStatus {
  security_groups: number;
  s3_buckets: number;
  iam_policies: number;
  vulnerabilities: VulnerabilityItem[];
  total_vulnerabilities: number;
  scan_timestamp: string;
  region: string;
}

export default function InfraPage() {
  const [infra, setInfra] = useState<InfraStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(
      `/api/proxy/api/v1/infra/status`
    )
      .then((r) => r.json())
      .then((data) => {
        setInfra(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "var(--aegis-red)";
      case "HIGH":
        return "var(--aegis-amber)";
      case "MEDIUM":
        return "var(--aegis-blue)";
      default:
        return "var(--muted-foreground)";
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-brand text-[28px] tracking-[0.08em]">
          INFRASTRUCTURE
        </h1>
        <p
          className="text-[11px] uppercase tracking-[0.1em]"
          style={{ color: "var(--muted-foreground)" }}
        >
          Live Resource Monitoring — AWS Mock Environment
        </p>
      </div>

      {loading ? (
        <p
          className="text-[11px] font-mono"
          style={{ color: "var(--muted-foreground)" }}
        >
          Scanning infrastructure...
        </p>
      ) : infra ? (
        <>
          {/* Resource counts */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "Security Groups", value: infra.security_groups },
              { label: "S3 Buckets", value: infra.s3_buckets },
              { label: "IAM Policies", value: infra.iam_policies },
            ].map((r) => (
              <div key={r.label} className="glass-card p-4 text-center">
                <p className="font-brand text-[24px]">{r.value}</p>
                <p
                  className="text-[9px] uppercase tracking-[0.1em] mt-1"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  {r.label}
                </p>
              </div>
            ))}
          </div>

          {/* Vulnerabilities list */}
          <div>
            <h2 className="font-brand text-[18px] tracking-[0.08em] mb-4">
              ACTIVE VULNERABILITIES ({infra.total_vulnerabilities || 0})
            </h2>
            <div className="space-y-2">
              {(infra.vulnerabilities || []).map((v, i) => (
                <motion.div
                  key={`${v.resource_id}-${i}`}
                  className="glass-card p-4"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-[12px] font-medium">
                        {v.resource_name || v.resource_id}
                      </p>
                      <p
                        className="text-[10px] font-mono mt-1"
                        style={{ color: "var(--muted-foreground)" }}
                      >
                        {v.resource_type} / {v.resource_id}
                      </p>
                      {v.cis_benchmark && (
                        <p
                          className="text-[9px] font-mono mt-1"
                          style={{ color: "var(--aegis-blue)" }}
                        >
                          {v.cis_benchmark}
                        </p>
                      )}
                      <p
                        className="text-[10px] mt-2"
                        style={{ color: "var(--muted-foreground)" }}
                      >
                        {v.description}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0 ml-4">
                      <span
                        className="text-[10px] font-mono uppercase tracking-[0.08em]"
                        style={{ color: getSeverityColor(v.severity) }}
                      >
                        {v.severity}
                      </span>
                      <p
                        className="text-[9px] font-mono mt-1"
                        style={{ color: "var(--muted-foreground)" }}
                      >
                        Risk: {v.risk_score}/10
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <p
          className="text-[11px] font-mono"
          style={{ color: "var(--aegis-red)" }}
        >
          Failed to load infrastructure status
        </p>
      )}
    </div>
  );
}
