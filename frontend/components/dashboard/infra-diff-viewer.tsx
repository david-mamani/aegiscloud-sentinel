"use client";
import { motion } from "framer-motion";

interface DiffProps {
  diff: {
    resource_type?: string;
    resource_id?: string;
    before?: { display?: string; status?: string; [key: string]: any };
    after?: { display?: string; status?: string; [key: string]: any };
  };
}

export function InfraDiffViewer({ diff }: DiffProps) {
  return (
    <div className="glass-card overflow-hidden">
      <div
        className="px-5 py-3 flex items-center gap-3 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <span
          className="text-[10px] font-mono uppercase tracking-[0.1em]"
          style={{ color: "var(--muted-foreground)" }}
        >
          Infrastructure Diff — {diff.resource_type} / {diff.resource_id}
        </span>
      </div>

      <div className="grid grid-cols-2 divide-x" style={{ borderColor: "var(--border)" }}>
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="p-4"
        >
          <p
            className="text-[10px] font-mono uppercase tracking-[0.1em] mb-2"
            style={{ color: "var(--aegis-red)" }}
          >
            Before (Current)
          </p>
          <p className="text-[12px] font-mono" style={{ color: "var(--aegis-red)" }}>
            {diff.before?.display || JSON.stringify(diff.before)}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
          className="p-4"
        >
          <p
            className="text-[10px] font-mono uppercase tracking-[0.1em] mb-2"
            style={{ color: "var(--aegis-green)" }}
          >
            After (Proposed)
          </p>
          <p className="text-[12px] font-mono" style={{ color: "var(--aegis-green)" }}>
            {diff.after?.display || JSON.stringify(diff.after)}
          </p>
        </motion.div>
      </div>
    </div>
  );
}
