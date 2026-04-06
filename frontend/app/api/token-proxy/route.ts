/**
 * Token Proxy — Extracts the user's Auth0 access token from the session
 * and forwards requests to the backend with it.
 *
 * This is the key to the Double-Blind Pattern:
 * - Frontend never sees the provider token
 * - Backend never stores the user session
 * - Token Vault bridges the gap via RFC 8693
 */

import { NextRequest, NextResponse } from "next/server";
import { auth0 } from "@/lib/auth0";

const BACKEND = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  try {
    const tokenData = await auth0.getAccessToken();
    const token = tokenData?.token;

    if (!token) {
      return NextResponse.json(
        { error: "No access token in session" },
        { status: 401 }
      );
    }

    const action = req.nextUrl.searchParams.get("action");
    const connection = req.nextUrl.searchParams.get("connection") || "github";

    if (action === "connections") {
      const resp = await fetch(`${BACKEND}/api/v1/auth/connections`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) {
        console.error(`[token-proxy] connections failed: ${resp.status} ${await resp.text().catch(() => '')}`);
      }
      const data = await resp.json().catch(() => ({ connections: [], error: `Backend returned ${resp.status}` }));
      return NextResponse.json(data);
    }

    if (action === "exchange") {
      const resp = await fetch(
        `${BACKEND}/api/v1/auth/token-vault/exchange-real`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ connection }),
        }
      );
      const data = await resp.json();
      return NextResponse.json(data);
    }

    return NextResponse.json({ error: "Invalid action" }, { status: 400 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Token proxy error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
