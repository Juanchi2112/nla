import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type ClientBody = {
  text: string;
  skip_first?: number;
  score?: boolean;
  temperature?: number;
  max_new_tokens?: number;
};

export async function POST(req: NextRequest) {
  const gpuUrl = process.env.GPU_URL;
  if (!gpuUrl) {
    return NextResponse.json({ error: "GPU_URL not set" }, { status: 500 });
  }

  let body: ClientBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  if (!body.text || typeof body.text !== "string") {
    return NextResponse.json({ error: "text required" }, { status: 400 });
  }

  const skipFirstDefault = parseInt(process.env.GPU_SKIP_FIRST ?? "10", 10);
  const payload = {
    text: body.text,
    skip_first: body.skip_first ?? skipFirstDefault,
    score: body.score ?? false,
    temperature: body.temperature ?? 0.7,
    max_new_tokens: body.max_new_tokens ?? 200,
  };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60_000);

  try {
    const upstream = await fetch(`${gpuUrl}/decode`, {
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
      status: 200,
      headers: { "content-type": "application/json" },
    });
  } catch (e: unknown) {
    clearTimeout(timeout);
    const msg = e instanceof Error ? e.message : "fetch failed";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
