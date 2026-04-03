"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Mission Control", id: "nav-missions" },
  { href: "/scopes", label: "Scopes Radar", id: "nav-scopes" },
  { href: "/audit", label: "Audit Log", id: "nav-audit" },
  { href: "/infra", label: "Infrastructure", id: "nav-infra" },
  { href: "/kill-switch", label: "Kill Switch", id: "nav-kill" },
  { href: "/settings", label: "Connected Accounts", id: "nav-settings" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-52 h-screen flex flex-col pt-8 pb-6 pl-6 pr-4">
      {/* Brand — pure typography */}
      <div className="mb-12">
        <span className="font-brand text-[22px] text-[var(--foreground)] tracking-[0.08em]">
          AEGISCLOUD
        </span>
      </div>

      {/* Navigation — text only */}
      <nav className="flex-1 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              id={item.id}
              className={`block py-1.5 text-[12px] uppercase tracking-[0.1em] transition-colors duration-200 ${
                isActive
                  ? "text-[var(--foreground)]"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Agent Status */}
      <div className="flex items-center gap-2.5">
        <span
          className="text-[8px]"
          style={{
            color: "var(--aegis-green)",
            animation: "pulse 2s ease-in-out infinite",
          }}
        >
          ●
        </span>
        <span className="text-[11px] tracking-[0.12em] text-[var(--muted-foreground)]">
          ONLINE
        </span>
      </div>
    </aside>
  );
}
