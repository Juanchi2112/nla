import type { NlaTrace } from "./mockData";

export type Verdict = {
  is_flagged: boolean;
  fired_rubric: string | null;
  severity: number;
  evidence: string | null;
  scores: Record<string, number>;
};

export type TokenEvent = { type: "token"; step: number; text: string };
export type NlaTraceEvent = {
  type: "nla_trace";
  step: number;
  mode: "A" | "B";
  monologue: string;
  verdict: Verdict | null;
};
export type DoneEvent = { type: "done"; total_tokens: number; reason: string };
export type ErrorEventPayload = { type: "error"; detail: string; step?: number };

export type GenerateResponse = { session_id: string; status: string };

export async function startGenerate(
  sessionId: string,
  prompt: string,
  sniffEveryK = 4
): Promise<GenerateResponse> {
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, prompt, sniff_every_k: sniffEveryK }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`generate failed: ${res.status} ${detail}`);
  }
  return (await res.json()) as GenerateResponse;
}

export type StreamHandlers = {
  onToken: (e: TokenEvent) => void;
  onTrace: (e: NlaTraceEvent) => void;
  onDone: (e: DoneEvent) => void;
  onError: (e: ErrorEventPayload | Event) => void;
  onSteer?: (data: unknown) => void;
};

export function openStream(sessionId: string, h: StreamHandlers): EventSource {
  const es = new EventSource(`/api/stream/${encodeURIComponent(sessionId)}`);

  es.addEventListener("token", (e: MessageEvent) => {
    try {
      h.onToken(JSON.parse(e.data) as TokenEvent);
    } catch (err) {
      console.warn("[nla] bad token event", err);
    }
  });

  es.addEventListener("nla_trace", (e: MessageEvent) => {
    try {
      h.onTrace(JSON.parse(e.data) as NlaTraceEvent);
    } catch (err) {
      console.warn("[nla] bad trace event", err);
    }
  });

  es.addEventListener("steer_applied", (e: MessageEvent) => {
    try {
      h.onSteer?.(JSON.parse(e.data));
    } catch {}
  });

  es.addEventListener("done", (e: MessageEvent) => {
    try {
      h.onDone(JSON.parse(e.data) as DoneEvent);
    } catch (err) {
      console.warn("[nla] bad done event", err);
    } finally {
      es.close();
    }
  });

  es.addEventListener("error", (e: MessageEvent | Event) => {
    if (e instanceof MessageEvent && typeof e.data === "string") {
      try {
        h.onError(JSON.parse(e.data) as ErrorEventPayload);
        return;
      } catch {}
    }
    h.onError(e);
  });

  return es;
}

export function verdictToTrace(verdict: Verdict | null, monologue: string): NlaTrace {
  if (!verdict) {
    return { judge_score: 0, category: "neutral", internal_monologue: monologue };
  }
  const score = verdict.is_flagged
    ? Math.min(0.55 + verdict.severity * 0.15, 1.0)
    : Math.min(verdict.severity * 0.12, 0.49);
  const category = verdict.fired_rubric?.replace(/_/g, " ") ?? "neutral";
  return { judge_score: score, category, internal_monologue: monologue };
}
