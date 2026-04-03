"use client";
import { useUser } from "@auth0/nextjs-auth0/client";

export function Header() {
  const { user, isLoading } = useUser();

  return (
    <header className="h-12 flex items-center justify-between px-8">
      <span className="text-[11px] uppercase tracking-[0.12em] text-[var(--muted-foreground)]">
        Command Center
      </span>

      <div className="flex items-center gap-5">
        {/* Auth */}
        {!isLoading && user ? (
          <div className="flex items-center gap-5">
            <span className="text-[11px] uppercase tracking-[0.1em] text-[var(--muted-foreground)]">
              {user.name || user.email}
            </span>
            <a
              href="/auth/logout"
              className="text-[11px] uppercase tracking-[0.1em] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
              id="btn-logout"
            >
              [ Sign Out ]
            </a>
          </div>
        ) : (
          <a
            href="/auth/login"
            className="text-[11px] uppercase tracking-[0.1em] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
            id="btn-login"
          >
            [ Sign In ]
          </a>
        )}
      </div>
    </header>
  );
}
