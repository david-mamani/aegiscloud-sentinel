"use client";
import { useState, useEffect } from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

interface ScopeItem {
  name: string;
  level: number;
  connection: string;
  granted_via: string;
}

export default function ScopesPage() {
  const [scopesData, setScopesData] = useState<ScopeItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/proxy/api/v1/scopes/`)
      .then((r) => r.json())
      .then((data) => {
        setScopesData(data.scopes || []);
        setLoading(false);
      })
      .catch(() => {
        // Fallback to hardcoded if backend unavailable
        setScopesData([
          { name: "EC2:Read", level: 90, connection: "aws-mock", granted_via: "Token Vault" },
          { name: "EC2:Write", level: 85, connection: "aws-mock", granted_via: "Token Vault + CIBA" },
          { name: "S3:Read", level: 70, connection: "aws-mock", granted_via: "Token Vault" },
          { name: "S3:Write", level: 60, connection: "aws-mock", granted_via: "Token Vault + CIBA" },
          { name: "IAM:Read", level: 80, connection: "aws-mock", granted_via: "Token Vault" },
          { name: "IAM:Write", level: 40, connection: "aws-mock", granted_via: "Token Vault + CIBA" },
          { name: "VPC:Read", level: 75, connection: "aws-mock", granted_via: "Token Vault" },
          { name: "GitHub:Read", level: 95, connection: "github", granted_via: "Token Vault" },
        ]);
        setLoading(false);
      });
  }, []);

  const chartData = scopesData.map((s) => ({
    scope: s.name,
    level: s.level,
    fullMark: 100,
  }));

  if (loading) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="font-brand text-[28px] tracking-[0.08em]">SCOPES RADAR</h1>
          <p className="text-[11px] uppercase tracking-[0.1em]"
             style={{ color: "var(--muted-foreground)" }}>
            Loading agent permissions...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-brand text-[28px] tracking-[0.08em]">
          SCOPES RADAR
        </h1>
        <p
          className="text-[11px] uppercase tracking-[0.1em]"
          style={{ color: "var(--muted-foreground)" }}
        >
          Agent Permission Boundaries
        </p>
      </div>

      <div className="glass-card p-8">
        <ResponsiveContainer width="100%" height={380}>
          <RadarChart data={chartData}>
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis
              dataKey="scope"
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
            />
            <PolarRadiusAxis
              tick={{ fill: "var(--muted-foreground)", fontSize: 9 }}
            />
            <Radar
              name="Active Scopes"
              dataKey="level"
              stroke="var(--foreground)"
              fill="var(--foreground)"
              fillOpacity={0.08}
              strokeWidth={1.5}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div>
        <h2 className="font-brand text-[18px] tracking-[0.08em] mb-4">
          ACTIVE SCOPES
        </h2>
        <div className="space-y-1">
          {scopesData.map((s) => (
            <div
              key={s.name}
              className="flex items-center justify-between py-2.5 px-4 glass-card"
            >
              <div>
                <span className="font-mono text-[12px]">{s.name}</span>
                <span className="font-mono text-[9px] ml-3"
                      style={{ color: "var(--muted-foreground)" }}>
                  via {s.granted_via}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div
                  className="w-28 h-[3px] rounded-full"
                  style={{ background: "var(--border)" }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${s.level}%`,
                      background: "var(--foreground)",
                      opacity: s.level > 80 ? 1 : s.level > 50 ? 0.6 : 0.3,
                    }}
                  />
                </div>
                <span
                  className="font-mono text-[10px] w-7 text-right"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  {s.level}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
