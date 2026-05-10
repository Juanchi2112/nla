import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return NextResponse.json({ error: "BACKEND_URL not set" }, { status: 500 });
  }
  const { sessionId } = await params;
  if (!sessionId) {
    return NextResponse.json({ error: "sessionId required" }, { status: 400 });
  }
  try {
    const upstream = await fetch(
      `${backendUrl}/api/reject-steer/${encodeURIComponent(sessionId)}`,
      { method: "POST" }
    );
    const text = await upstream.text();
    if (!upstream.ok) {
      return NextResponse.json(
        { error: "upstream error", status: upstream.status, detail: text },
        { status: 502 }
      );
    }
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "fetch failed";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
