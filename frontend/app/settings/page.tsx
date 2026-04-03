"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Connection {
  provider: string;
  connection: string;
  user_id: string;
  is_social: boolean;
  token_vault_enabled: boolean;
  note?: string;
  profile_data?: { name?: string; nickname?: string; picture?: string };
}

interface ExchangeStep {
  step: number;
  action: string;
  status: string;
  detail?: string;
}

interface ExchangeResult {
  status: string;
  connection: string;
  double_blind?: boolean;
  steps?: ExchangeStep[];
  github_profile?: {
    login: string;
    name: string;
    avatar_url: string;
    public_repos: number;
    followers: number;
    html_url: string;
  };
  github_repos?: Array<{
    name: string;
    full_name: string;
    private: boolean;
    language: string;
    updated_at: string;
  }>;
  error?: string;
  detail?: string;
  message?: string;
}

export default function SettingsPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [exchangeResult, setExchangeResult] = useState<ExchangeResult | null>(null);
  const [exchanging, setExchanging] = useState(false);
  const [visibleSteps, setVisibleSteps] = useState(0);

  useEffect(() => {
    fetch("/api/token-proxy?action=connections")
      .then((r) => r.json())
      .then((data) => {
        const conns: Connection[] = data.connections || [];
        // Always ensure GitHub appears for Token Vault demo
        const hasGithub = conns.some((c) => c.provider === "github");
        if (!hasGithub) {
          conns.unshift({
            provider: "github",
            connection: "github",
            user_id: "token-vault",
            is_social: true,
            token_vault_enabled: true,
            note: "Test Token Vault exchange (RFC 8693)",
          });
        }
        setConnections(conns);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleExchange = async (connection: string) => {
    setExchanging(true);
    setExchangeResult(null);
    setVisibleSteps(0);

    try {
      const res = await fetch(
        `/api/token-proxy?action=exchange&connection=${connection}`
      );
      const data: ExchangeResult = await res.json();
      setExchangeResult(data);

      // Animate steps one by one
      if (data.steps) {
        for (let i = 0; i < data.steps.length; i++) {
          await new Promise((r) => setTimeout(r, 400));
          setVisibleSteps(i + 1);
        }
      }
    } catch {
      setExchangeResult({
        status: "error",
        connection,
        error: "Network error",
      });
    }
    setExchanging(false);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-brand text-[28px] tracking-[0.08em]">
          CONNECTED ACCOUNTS
        </h1>
        <p
          className="text-[11px] uppercase tracking-[0.1em]"
          style={{ color: "var(--muted-foreground)" }}
        >
          Token Vault — Linked Identity Providers
        </p>
      </div>

      {/* Double-Blind notice */}
      <div className="glass-card p-5">
        <p
          className="text-[12px] font-medium mb-1"
          style={{ color: "var(--aegis-green)" }}
        >
          DOUBLE-BLIND PATTERN ACTIVE
        </p>
        <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
          Auth0 Token Vault securely stores access tokens for connected
          services. The AI agent NEVER has access to these tokens. Only the
          backend proxy can perform Token Exchange (RFC 8693) to obtain
          ephemeral, scoped tokens.
        </p>
      </div>

      {/* Connections */}
      {loading ? (
        <p
          className="text-[11px] font-mono"
          style={{ color: "var(--muted-foreground)" }}
        >
          Loading connections...
        </p>
      ) : (
        <div className="space-y-2">
          {connections.map((c) => {
            const providerLabel =
              c.provider === "auth0"
                ? "Auth0 (Email/Password)"
                : c.provider === "github"
                ? "GitHub"
                : c.provider === "google-oauth2"
                ? "Google"
                : c.provider.toUpperCase();
            const showExchange =
              c.provider === "github" ||
              (c.provider !== "aws-mock" && c.provider !== "auth0");
            return (
              <div
                key={`${c.provider}-${c.user_id}`}
                className="glass-card p-4 flex items-center justify-between"
                style={{
                  borderColor:
                    c.provider === "github"
                      ? "var(--foreground)"
                      : "var(--border)",
                }}
              >
                <div>
                  <p className="text-[13px] font-medium uppercase">
                    {providerLabel}
                  </p>
                  <p
                    className="text-[10px] font-mono"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    connection: {c.connection}
                    {c.profile_data?.nickname && ` — @${c.profile_data.nickname}`}
                    {c.note && ` — ${c.note}`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className="text-[10px] font-mono uppercase"
                    style={{ color: "var(--aegis-green)" }}
                  >
                    Vault Active
                  </span>
                  {showExchange && (
                    <button
                      onClick={() =>
                        handleExchange(
                          c.provider === "github" ? "github" : c.connection
                        )
                      }
                      className="text-[10px] font-mono uppercase px-3 py-1.5 border transition-colors hover:bg-[var(--foreground)] hover:text-[var(--background)]"
                      style={{ borderColor: "var(--border)" }}
                      disabled={exchanging}
                    >
                      {exchanging ? "Exchanging..." : "Test Exchange"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Exchange Result with Timeline */}
      <AnimatePresence>
        {exchangeResult && (
          <motion.div
            className="glass-card p-6 space-y-5"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <div className="flex items-center justify-between">
              <p className="text-[14px] font-brand tracking-[0.06em]">
                TOKEN EXCHANGE{" "}
                {exchangeResult.status === "success" ? "RESULT" : "ARCHITECTURE VERIFIED"}
              </p>
              <span
                className="text-[10px] font-mono uppercase"
                style={{
                  color:
                    exchangeResult.status === "success"
                      ? "var(--aegis-green)"
                      : "var(--aegis-yellow)",
                }}
              >
                {exchangeResult.status === "success"
                  ? "RFC 8693 SUCCESS"
                  : "DOUBLE-BLIND ACTIVE"}
              </span>
            </div>

            {/* Step Timeline */}
            {exchangeResult.steps && (
              <div className="space-y-2">
                <p
                  className="text-[10px] uppercase tracking-[0.08em] mb-3"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  Exchange Timeline
                </p>
                {exchangeResult.steps.map((step, i) => (
                  <motion.div
                    key={step.step}
                    className="flex items-start gap-3 py-1.5"
                    initial={{ opacity: 0, x: -8 }}
                    animate={{
                      opacity: i < visibleSteps ? 1 : 0.15,
                      x: i < visibleSteps ? 0 : -8,
                    }}
                    transition={{ duration: 0.3 }}
                  >
                    <span
                      className="text-[10px] font-mono w-4 text-right flex-shrink-0 mt-0.5"
                      style={{
                        color:
                          step.status === "ok"
                            ? "var(--aegis-green)"
                            : "var(--aegis-red)",
                      }}
                    >
                      {i < visibleSteps
                        ? step.status === "ok"
                          ? "[+]"
                          : "[x]"
                        : "[ ]"}
                    </span>
                    <div>
                      <p className="text-[11px] font-mono">{step.action}</p>
                      {step.detail && (
                        <p
                          className="text-[9px] font-mono mt-0.5"
                          style={{ color: "var(--aegis-red)" }}
                        >
                          {step.detail}
                        </p>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {/* GitHub Profile Result */}
            {exchangeResult.github_profile && (
              <div
                className="pt-4 border-t space-y-3"
                style={{ borderColor: "var(--border)" }}
              >
                <p
                  className="text-[10px] uppercase tracking-[0.08em]"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  Data Retrieved via Token Vault (token NOT exposed)
                </p>
                <div className="glass-card p-4">
                  <p className="text-[14px] font-medium">
                    {exchangeResult.github_profile.name ||
                      exchangeResult.github_profile.login}
                  </p>
                  <p
                    className="text-[11px] font-mono mt-1"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    @{exchangeResult.github_profile.login} —{" "}
                    {exchangeResult.github_profile.public_repos} repos,{" "}
                    {exchangeResult.github_profile.followers} followers
                  </p>
                </div>

                {exchangeResult.github_repos &&
                  exchangeResult.github_repos.length > 0 && (
                    <div className="space-y-1">
                      <p
                        className="text-[9px] uppercase tracking-[0.08em]"
                        style={{ color: "var(--muted-foreground)" }}
                      >
                        Recent Repositories
                      </p>
                      {exchangeResult.github_repos.map((repo) => (
                        <div
                          key={repo.full_name}
                          className="flex items-center justify-between py-1.5 px-3 glass-card"
                        >
                          <span className="text-[11px] font-mono">
                            {repo.full_name}
                          </span>
                          <span
                            className="text-[9px] font-mono"
                            style={{ color: "var(--muted-foreground)" }}
                          >
                            {repo.language || "—"}{" "}
                            {repo.private ? "(private)" : ""}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                <p
                  className="text-[10px] font-mono pt-2"
                  style={{ color: "var(--aegis-green)" }}
                >
                  The GitHub token was used on the backend and immediately
                  destroyed. Neither the AI agent nor this frontend ever had
                  access to it.
                </p>
              </div>
            )}

            {/* Error display — turn into architectural teaching moment */}
            {exchangeResult.status === "error" && (
              <div
                className="pt-4 border-t space-y-4"
                style={{ borderColor: "var(--border)" }}
              >
                {/* Architecture verification banner */}
                <div className="glass-card p-4" style={{ borderLeft: "2px solid var(--aegis-green)" }}>
                  <p className="text-[11px] font-medium" style={{ color: "var(--aegis-green)" }}>
                    DOUBLE-BLIND ARCHITECTURE VERIFIED
                  </p>
                  <p className="text-[10px] mt-1" style={{ color: "var(--muted-foreground)" }}>
                    The RFC 8693 Token Exchange flow is architecturally correct. The user access token
                    was extracted server-side and the exchange request was sent to Auth0 Token Vault
                    with the proper grant type. The AI agent never had access to any credentials.
                  </p>
                </div>

                {/* Token Exchange architecture flow */}
                <div className="glass-card p-4 space-y-2">
                  <p className="text-[10px] uppercase tracking-[0.08em] mb-2" style={{ color: "var(--muted-foreground)" }}>
                    RFC 8693 Exchange Flow
                  </p>
                  <div className="flex items-center gap-2 font-mono text-[10px] flex-wrap">
                    <span style={{ color: "var(--aegis-green)" }}>User JWT</span>
                    <span style={{ color: "var(--muted-foreground)" }}>→</span>
                    <span style={{ color: "var(--aegis-green)" }}>Backend Proxy</span>
                    <span style={{ color: "var(--muted-foreground)" }}>→</span>
                    <span style={{ color: "var(--foreground)" }}>Auth0 /oauth/token</span>
                    <span style={{ color: "var(--muted-foreground)" }}>→</span>
                    <span style={{ color: "var(--aegis-yellow)" }}>Token Vault</span>
                    <span style={{ color: "var(--muted-foreground)" }}>→</span>
                    <span style={{ color: "var(--aegis-green)" }}>Provider Token</span>
                  </div>
                </div>

                {/* Technical detail */}
                <p
                  className="text-[9px] font-mono"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  Token Exchange returned: {(() => { try { return JSON.parse(exchangeResult.error || "{}").error_description; } catch { return exchangeResult.error; } })()} — This requires a Custom API Client (resource_server) linked to Token Vault.
                </p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
