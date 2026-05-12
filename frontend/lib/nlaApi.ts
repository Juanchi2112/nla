export type Severity = "low" | "medium" | "high";
export type DivergenceCategory =
  | "harmful_intent"
  | "jailbreak_compliance"
  | "tool_misreport"
  | "deception_general"
  | string;
export type VerdictAction = "PASS" | "FLAG" | "STEER";

export type Divergence = {
  pos: number;
  verbal_claim: string;
  internal_thought: string;
  severity: Severity;
  category: DivergenceCategory;
};

export type TurnVerdict = {
  trust_score: number;
  summary: string;
  divergences: Divergence[];
  action: VerdictAction;
  correction_prompt: string | null;
  reasoning: string;
  provenance?: Record<string, unknown> | null;
};

export type TokenEvent = { type: "token"; step: number; text: string };
export type NlaTraceEvent = {
  type: "nla_trace";
  step: number;
  mode: "A" | "B";
  monologue: string;
  verdict: unknown;
};
export type JudgeSummaryEvent = {
  type: "judge_summary";
  phase: "original" | "steered";
  verdict: TurnVerdict;
};
export type SteeringProposedEvent = {
  type: "steering_proposed";
  correction_prompt: string;
  reason: string;
  timeout_seconds: number;
};
export type SteeringStartedEvent = {
  type: "steering_started";
  correction_prompt: string;
  reason: string;
};
export type SteeringRejectedEvent = {
  type: "steering_rejected";
  reason: "rejected_by_user" | "timeout" | string;
};
export type SteeringCompleteEvent = {
  type: "steering_complete";
  original_trust: number;
  steered_trust: number;
  delta: number;
};
export type DoneEvent = { type: "done"; total_tokens: number; reason: string };
export type ErrorEventPayload = { type: "error"; detail: string; step?: number };

export type GenerateResponse = { session_id: string; status: string };

export type StartGenerateOpts = {
  sessionId: string;
  prompt?: string;
  scenarioId?: string;
  systemPrompt?: string;
  sniffEveryK?: number;
};

export async function startGenerate(opts: StartGenerateOpts): Promise<GenerateResponse> {
  const body: Record<string, unknown> = {
    session_id: opts.sessionId,
    sniff_every_k: opts.sniffEveryK ?? 4,
  };
  if (opts.scenarioId) {
    body.scenario_id = opts.scenarioId;
  } else {
    body.prompt = opts.prompt ?? "";
    if (opts.systemPrompt !== undefined) body.system_prompt = opts.systemPrompt;
  }
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
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
  onJudgeSummary: (e: JudgeSummaryEvent) => void;
  onSteeringProposed: (e: SteeringProposedEvent) => void;
  onSteeringStarted: (e: SteeringStartedEvent) => void;
  onSteeringRejected: (e: SteeringRejectedEvent) => void;
  onSteeringComplete: (e: SteeringCompleteEvent) => void;
  onDone: (e: DoneEvent) => void;
  onError: (e: ErrorEventPayload | Event) => void;
};

const parseEvent = <T>(name: string, e: MessageEvent, handler: (v: T) => void) => {
  try {
    handler(JSON.parse(e.data) as T);
  } catch (err) {
    console.warn(`[nla] bad ${name} event`, err);
  }
};

export function openStream(sessionId: string, h: StreamHandlers): EventSource {
  const es = new EventSource(`/api/stream/${encodeURIComponent(sessionId)}`);

  es.addEventListener("token", (e: MessageEvent) => parseEvent("token", e, h.onToken));
  es.addEventListener("nla_trace", (e: MessageEvent) => parseEvent("nla_trace", e, h.onTrace));
  es.addEventListener("judge_summary", (e: MessageEvent) =>
    parseEvent("judge_summary", e, h.onJudgeSummary)
  );
  es.addEventListener("steering_proposed", (e: MessageEvent) =>
    parseEvent("steering_proposed", e, h.onSteeringProposed)
  );
  es.addEventListener("steering_started", (e: MessageEvent) =>
    parseEvent("steering_started", e, h.onSteeringStarted)
  );
  es.addEventListener("steering_rejected", (e: MessageEvent) =>
    parseEvent("steering_rejected", e, h.onSteeringRejected)
  );
  es.addEventListener("steering_complete", (e: MessageEvent) =>
    parseEvent("steering_complete", e, h.onSteeringComplete)
  );

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

export async function confirmSteer(sessionId: string): Promise<void> {
  const res = await fetch(`/api/confirm-steer/${encodeURIComponent(sessionId)}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`confirm-steer failed: ${res.status}`);
}

export async function rejectSteer(sessionId: string): Promise<void> {
  const res = await fetch(`/api/reject-steer/${encodeURIComponent(sessionId)}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`reject-steer failed: ${res.status}`);
}

export async function cancelGeneration(sessionId: string): Promise<void> {
  const res = await fetch(`/api/cancel/${encodeURIComponent(sessionId)}`, { method: "POST" });
  if (!res.ok) throw new Error(`cancel failed: ${res.status}`);
}
