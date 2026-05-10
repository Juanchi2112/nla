import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type ClientBody = {
  session_id: string;
  prompt?: string;
  scenario_id?: string;
  system_prompt?: string;
  sniff_every_k?: number;
  model?: string;
};

export async function POST(req: NextRequest) {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return NextResponse.json({ error: "BACKEND_URL not set" }, { status: 500 });
  }

  let body: ClientBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  if (!body.session_id || (!body.prompt && !body.scenario_id)) {
    return NextResponse.json(
      { error: "session_id and (prompt or scenario_id) required" },
      { status: 400 }
    );
  }

  const payload: Record<string, unknown> = {
    session_id: body.session_id,
    sniff_every_k: body.sniff_every_k ?? 4,
  };
  if (body.scenario_id) {
    payload.scenario_id = body.scenario_id;
  } else {
    payload.prompt = body.prompt;
    if (body.system_prompt !== undefined) payload.system_prompt = body.system_prompt;
  }
  if (body.model) payload.model = body.model;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);

  try {
    const upstream = await fetch(`${backendUrl}/api/generate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timeout);

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
    clearTimeout(timeout);
    const msg = e instanceof Error ? e.message : "fetch failed";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
