/**
 * Backend API Proxy — The Double-Blind Bridge.
 *
 * This Route Handler is the CRITICAL security component on the frontend side:
 * 1. It extracts the Auth0 Access Token from the server-side session
 * 2. Injects it as an Authorization: Bearer header
 * 3. Forwards the request to the FastAPI backend
 *
 * The browser NEVER sees the Access Token — it stays server-side.
 * This is the frontend half of the Double-Blind Pattern.
 */

import { NextRequest, NextResponse } from "next/server";
import { auth0 } from "@/lib/auth0";

const BACKEND = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

async function proxyRequest(
  req: NextRequest,
  params: { path: string[] }
) {
  try {
    // 1. Extract the Auth0 Access Token from server-side session
    const tokenData = await auth0.getAccessToken();
    const token = tokenData?.token;

    if (!token) {
      return NextResponse.json(
        { error: "Not authenticated" },
        { status: 401 }
      );
    }

    // 2. Reconstruct the backend URL from the catch-all path segments
    const backendPath = "/" + params.path.join("/");
    const queryString = req.nextUrl.search; // preserves ?key=value
    const backendUrl = `${BACKEND}${backendPath}${queryString}`;

    // 3. Build the proxied request with the Authorization header injected
    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
    };

    // Forward Content-Type for POST requests
    const contentType = req.headers.get("content-type");
    if (contentType) {
      headers["Content-Type"] = contentType;
    }

    const fetchOptions: RequestInit = {
      method: req.method,
      headers,
    };

    // Forward body for POST/PUT/PATCH requests
    if (req.method !== "GET" && req.method !== "HEAD") {
      try {
        const body = await req.text();
        if (body) {
          fetchOptions.body = body;
        }
      } catch {
        // No body — that's fine for some POST requests
      }
    }

    // 4. Forward to the FastAPI backend
    const backendRes = await fetch(backendUrl, fetchOptions);
    const data = await backendRes.json();

    return NextResponse.json(data, { status: backendRes.status });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Proxy error";
    console.error("[API Proxy Error]", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
