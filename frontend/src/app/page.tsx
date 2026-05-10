"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { flushSync } from "react-dom";
import { motion } from "framer-motion";
import styles from "./page.module.css";
import { SCENARIOS, type ScenarioId } from "@/lib/scenarios";
import {
  startGenerate,
  openStream,
  confirmSteer,
  rejectSteer,
  type TurnVerdict,
  type Divergence,
  type VerdictAction,
  type Severity,
} from "@/lib/nlaApi";
import FlowPanel from "@/components/FlowPanel";

type Phase = "idle" | "running" | "done" | "error";
type Mode = "scenario" | "free";

type Token = {
  id: number;
  step: number;
  text: string;
  phaseLabel?: "original" | "steered";
  isSeparator?: boolean;
};

const STEERED_OFFSET = 1_000_000;
const phaseOffset = (p: "original" | "steered" | undefined) =>
  p === "steered" ? STEERED_OFFSET : 0;

const FILLER_TRAVEL_MS = 620;
const FILLER_STAGGER_MS = 35;
const REVEAL_DELAY_MS = 220;
const SNIFF_EVERY_K = 1;
const SEPARATOR_ID = -1;

type Target = { dx: number; dy: number };

const tierFromSeverity = (s: Severity | undefined): "none" | "low" | "warn" | "decep" => {
  if (s === "high") return "decep";
  if (s === "medium") return "warn";
  if (s === "low") return "low";
  return "none";
};

const colorForAction = (a: VerdictAction): string => {
  if (a === "PASS") return "var(--accent, #5eead4)";
  if (a === "FLAG") return "var(--diagram-gold, #c8a951)";
  return "var(--diagram-red, #e66b6b)";
};

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [scenarioIdx, setScenarioIdx] = useState(1);
  const mode: Mode = scenarioIdx === 3 ? "free" : "scenario";
  const [promptInput, setPromptInput] = useState("");

  const [tokens, setTokens] = useState<Token[]>([]);
  const [monologueByStep, setMonologueByStep] = useState<Map<number, string>>(new Map());
  const [emittedThoughts, setEmittedThoughts] = useState<number[]>([]);
  const [collapsedThoughts, setCollapsedThoughts] = useState<Set<number>>(new Set());
  const [consumedIds, setConsumedIds] = useState<Set<number>>(new Set());
  const [targets, setTargets] = useState<Record<number, Target>>({});
  const [flyingId, setFlyingId] = useState<number | null>(null);
  const [pulsing, setPulsing] = useState(false);

  const [currentPhaseLabel, setCurrentPhaseLabel] = useState<"original" | "steered">("original");
  const [verdicts, setVerdicts] = useState<{ original?: TurnVerdict; steered?: TurnVerdict }>({});
  const [steerDelta, setSteerDelta] = useState<{
    original: number;
    steered: number;
    delta: number;
  } | null>(null);
  const [pendingSteer, setPendingSteer] = useState<{
    correction_prompt: string;
    reason: string;
  } | null>(null);
  const [correctionPrompt, setCorrectionPrompt] = useState<string | null>(null);
  const [steerCountdown, setSteerCountdown] = useState<number>(60);
  const [steerStatus, setSteerStatus] = useState<"idle" | "started" | "rejected">("idle");

  const [selectedTokenId, setSelectedTokenId] = useState<number | null>(null);
  const [hoveredTokenId, setHoveredTokenId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activePrompt, setActivePrompt] = useState<string | null>(null);

  const sessionIdRef = useRef<string | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const stoppedRef = useRef(false);
  const activeAnimRef = useRef<Animation | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const avBoxRef = useRef<HTMLDivElement | null>(null);
  const travelerRef = useRef<HTMLDivElement | null>(null);
  const tokensColRef = useRef<HTMLDivElement | null>(null);
  const tokenRefs = useRef<Map<number, HTMLSpanElement>>(new Map());
  const phaseLabelRef = useRef<"original" | "steered">("original");

  const queueRef = useRef<Token[]>([]);
  const streamDoneRef = useRef(false);
  const wakeRef = useRef<(() => void) | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const nextSlotRef = useRef(0);

  const cleanup = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    stoppedRef.current = true;
    if (activeAnimRef.current) {
      try {
        activeAnimRef.current.cancel();
      } catch {}
      activeAnimRef.current = null;
    }
    if (esRef.current) {
      try {
        esRef.current.close();
      } catch {}
      esRef.current = null;
    }
  };
  useEffect(() => cleanup, []);

  useEffect(() => {
    if (phase === "running" && tokensColRef.current) {
      tokensColRef.current.scrollTop = tokensColRef.current.scrollHeight;
    }
  });

  const sleep = (ms: number) =>
    new Promise<void>((resolve) => {
      const id = setTimeout(resolve, ms);
      timersRef.current.push(id);
    });

  const wake = () => {
    const w = wakeRef.current;
    wakeRef.current = null;
    w?.();
  };

  const waitForToken = () =>
    new Promise<void>((resolve) => {
      if (queueRef.current.length || streamDoneRef.current || stoppedRef.current) {
        resolve();
        return;
      }
      wakeRef.current = resolve;
    });

  const captureTarget = (id: number) => {
    const el = tokenRefs.current.get(id);
    const av = avBoxRef.current;
    if (!el || !av) return;
    const r = el.getBoundingClientRect();
    const a = av.getBoundingClientRect();
    const dx = a.left + a.width / 2 - (r.left + r.width / 2);
    const dy = a.top + a.height / 2 - (r.top + r.height / 2);
    setTargets((prev) => ({ ...prev, [id]: { dx, dy } }));
  };

  const consume = (id: number) => {
    setConsumedIds((prev) => {
      const n = new Set(prev);
      n.add(id);
      return n;
    });
  };

  const launch = (tok: Token, isTraced: boolean) => {
    captureTarget(tok.id);
    if (isTraced) setFlyingId(tok.id);
    requestAnimationFrame(() => consume(tok.id));
  };

  const startGen = async () => {
    cleanup();
    stoppedRef.current = false;
    streamDoneRef.current = false;
    queueRef.current = [];
    phaseLabelRef.current = "original";
    nextSlotRef.current = 0;

    flushSync(() => {
      setPhase("idle");
      setTokens([]);
      setMonologueByStep(new Map());
      setEmittedThoughts([]);
      setCollapsedThoughts(new Set());
      setConsumedIds(new Set());
      setTargets({});
      setFlyingId(null);
      setVerdicts({});
      setSteerDelta(null);
      setPendingSteer(null);
      setCorrectionPrompt(null);
      setSteerStatus("idle");
      setCurrentPhaseLabel("original");
      setSelectedTokenId(null);
      setHoveredTokenId(null);
      setErrorMsg(null);
    });
    setActivePrompt(mode === "scenario" ? (SCENARIOS[scenarioIdx]?.prompt ?? null) : promptInput.trim() || null);
    setPulsing(true);
    setPhase("running");
    requestAnimationFrame(() => {
      stageRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    const sessionId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `sid-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionIdRef.current = sessionId;

    try {
      if (mode === "scenario") {
        await startGenerate({
          sessionId,
          scenarioId: SCENARIOS[scenarioIdx].id,
          sniffEveryK: SNIFF_EVERY_K,
        });
      } else {
        const trimmed = promptInput.trim();
        if (!trimmed) {
          setErrorMsg("Prompt vacío");
          setPhase("idle");
          return;
        }
        await startGenerate({
          sessionId,
          prompt: trimmed,
          sniffEveryK: SNIFF_EVERY_K,
        });
      }
    } catch (err) {
      console.error("[nla] generate failed", err);
      setErrorMsg(err instanceof Error ? err.message : "generate failed");
      setPhase("error");
      return;
    }

    const scheduleToken = (tok: Token) => {
      const now = performance.now();
      const slot = Math.max(now, nextSlotRef.current);
      nextSlotRef.current = slot + FILLER_STAGGER_MS;
      const delay = Math.max(0, slot - now);
      const t1 = setTimeout(() => {
        if (stoppedRef.current) return;
        launch(tok, false);
      }, delay);
      const t2 = setTimeout(() => {
        if (stoppedRef.current) return;
        setEmittedThoughts((prev) => (prev.includes(tok.id) ? prev : [...prev, tok.id]));
      }, delay + REVEAL_DELAY_MS);
      timersRef.current.push(t1, t2);
    };

    esRef.current = openStream(sessionId, {
      onToken: (e) => {
        const tok: Token = {
          id: e.step + phaseOffset(phaseLabelRef.current),
          step: e.step,
          text: e.text,
          phaseLabel: phaseLabelRef.current,
        };
        setTokens((prev) => [...prev, tok]);
        scheduleToken(tok);
      },
      onTrace: (e) => {
        const key = e.step + phaseOffset(phaseLabelRef.current);
        setMonologueByStep((prev) => {
          const m = new Map(prev);
          m.set(key, e.monologue);
          return m;
        });
      },
      onJudgeSummary: (e) => {
        setVerdicts((prev) => ({ ...prev, [e.phase]: e.verdict }));
      },
      onSteeringProposed: (e) => {
        setPendingSteer({ correction_prompt: e.correction_prompt, reason: e.reason });
        setCorrectionPrompt(e.correction_prompt);
        setSteerCountdown(e.timeout_seconds ?? 60);
      },
      onSteeringStarted: (e) => {
        setSteerStatus("started");
        setCorrectionPrompt(e.correction_prompt);
        setPendingSteer(null);
        phaseLabelRef.current = "steered";
        setCurrentPhaseLabel("steered");
        const sep: Token = {
          id: SEPARATOR_ID,
          step: -1,
          text: `── steering: ${e.reason} ──`,
          isSeparator: true,
          phaseLabel: "steered",
        };
        setTokens((prev) => [...prev, sep]);
        nextSlotRef.current = performance.now() + 280;
      },
      onSteeringRejected: () => {
        setSteerStatus("rejected");
        setPendingSteer(null);
      },
      onSteeringComplete: (e) => {
        setSteerDelta({
          original: e.original_trust,
          steered: e.steered_trust,
          delta: e.delta,
        });
      },
      onDone: () => {
        streamDoneRef.current = true;
        wake();
      },
      onError: (e) => {
        console.warn("[nla] stream error", e);
        const detail = (e as { detail?: string }).detail;
        if (detail) setErrorMsg(detail);
        streamDoneRef.current = true;
        wake();
      },
    });

    while (!stoppedRef.current && !streamDoneRef.current) {
      await waitForToken();
    }
    if (stoppedRef.current) return;
    const drainEnd = nextSlotRef.current + FILLER_TRAVEL_MS + REVEAL_DELAY_MS + 200;
    const remaining = Math.max(0, drainEnd - performance.now());
    await sleep(remaining);
    if (stoppedRef.current) return;
    setPulsing(false);
    setFlyingId(null);
    setPhase("done");
  };

  const reset = () => {
    cleanup();
    stoppedRef.current = false;
    streamDoneRef.current = false;
    queueRef.current = [];
    phaseLabelRef.current = "original";
    nextSlotRef.current = 0;
    sessionIdRef.current = null;
    setTokens([]);
    setMonologueByStep(new Map());
    setEmittedThoughts([]);
    setCollapsedThoughts(new Set());
    setConsumedIds(new Set());
    setTargets({});
    setFlyingId(null);
    setPulsing(false);
    setVerdicts({});
    setSteerDelta(null);
    setPendingSteer(null);
    setCorrectionPrompt(null);
    setSteerStatus("idle");
    setCurrentPhaseLabel("original");
    setSelectedTokenId(null);
    setHoveredTokenId(null);
    setErrorMsg(null);
    setPhase("idle");
  };

  // keyboard arrows for scenario nav (only when scenario mode + no input focused)
  useEffect(() => {
    if (mode !== "scenario") return;
    const onKey = (e: KeyboardEvent) => {
      if (phase === "running") return;
      const tag = (document.activeElement?.tagName ?? "").toLowerCase();
      if (tag === "input" || tag === "textarea") return;
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        setScenarioIdx((i) => (i - 1 + 4) % 4);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setScenarioIdx((i) => (i + 1) % 4);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, phase]);

  // steering modal countdown
  useEffect(() => {
    if (!pendingSteer) return;
    if (steerCountdown <= 0) return;
    const t = setTimeout(() => setSteerCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [pendingSteer, steerCountdown]);

  const handleConfirmSteer = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    try {
      await confirmSteer(sid);
    } catch (err) {
      console.warn("[nla] confirm-steer failed", err);
    }
    setPendingSteer(null);
  }, []);

  const handleRejectSteer = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    try {
      await rejectSteer(sid);
    } catch (err) {
      console.warn("[nla] reject-steer failed", err);
    }
    setPendingSteer(null);
    setSteerStatus("rejected");
  }, []);

  // map divergences (from current verdicts) to per-token tier by phase+pos
  const divergenceMap = useMemo(() => {
    const m = new Map<number, { d: Divergence; phase: "original" | "steered" }>();
    if (verdicts.original) {
      verdicts.original.divergences.forEach((d) =>
        m.set(d.pos + phaseOffset("original"), { d, phase: "original" })
      );
    }
    if (verdicts.steered) {
      verdicts.steered.divergences.forEach((d) =>
        m.set(d.pos + phaseOffset("steered"), { d, phase: "steered" })
      );
    }
    return m;
  }, [verdicts]);

  const tierOfToken = (tok: Token): "none" | "low" | "warn" | "decep" => {
    const hit = divergenceMap.get(tok.id);
    if (!hit) return "none";
    return tierFromSeverity(hit.d.severity);
  };

  const selectedToken = useMemo(
    () => tokens.find((t) => t.id === selectedTokenId) ?? null,
    [tokens, selectedTokenId]
  );

  const hoveredToken = useMemo(
    () => tokens.find((t) => t.id === hoveredTokenId) ?? null,
    [tokens, hoveredTokenId]
  );

  const activeToken = hoveredToken ?? selectedToken;

  const selectedDivergence = activeToken ? divergenceMap.get(activeToken.id)?.d : undefined;
  const showStrip = phase === "done" || phase === "error";
  const judgeRunning = phase === "running" && tokens.length > 0 && !verdicts.original;

  const currentScenario = scenarioIdx < 3 ? SCENARIOS[scenarioIdx] : null;
  const canSubmit =
    phase !== "running" && (mode === "scenario" || promptInput.trim().length > 0);

  return (
    <main className={`lyt-grid`}>
      <section className="lyt-block lyt-loose lyt-title-huge lyt-align-left">
        <div className={styles.heroKicker}>
          <span className={styles.heroKickerDot} aria-hidden="true" />
        </div>
        <h1 className={styles.headline}>
          Lo que el modelo dice <span className={styles.headlineAccent}>vs.</span> lo que está pensando.
        </h1>
        <p className={styles.heroLead}>
          Auditoría de alineamiento para LLMs open-source. Leemos el{" "}
          <em>residual stream</em>{" "}del modelo &mdash; no la cadena de pensamiento que escribe sabiendo
          que la van a leer.
        </p>

        <div className={styles.scenarioCarousel}>
          <button
            type="button"
            className={styles.carouselArrow}
            aria-label="Anterior"
            disabled={phase === "running"}
            onClick={() => setScenarioIdx((i) => (i - 1 + 4) % 4)}
          >
            ←
          </button>
          <form
            className={styles.scenarioInput}
            onSubmit={(e) => {
              e.preventDefault();
              if (!canSubmit) return;
              startGen();
            }}
          >
            {scenarioIdx === 3 ? (
              <input
                type="text"
                className={styles.promptText}
                value={promptInput}
                onChange={(e) => setPromptInput(e.target.value)}
                placeholder="Enter a prompt to audit..."
                disabled={phase === "running"}
              />
            ) : (
              <span className={styles.scenarioPromptDisplay}>
                {currentScenario?.prompt}
              </span>
            )}
            <button
              type="submit"
              className={styles.promptSendBtn}
              aria-label="Send"
              disabled={!canSubmit}
            >
              <svg
                viewBox="0 0 24 24"
                width="16"
                height="16"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            </button>
          </form>
          <button
            type="button"
            className={styles.carouselArrow}
            aria-label="Siguiente"
            disabled={phase === "running"}
            onClick={() => setScenarioIdx((i) => (i + 1) % 4)}
          >
            →
          </button>
        </div>

        <div className={styles.scenarioDotsRow}>
          {[0, 1, 2, 3].map((i) => (
            <span
              key={i}
              className={`${styles.scenarioDot} ${i === scenarioIdx ? styles.scenarioDotActive : ""}`}
              aria-hidden="true"
            />
          ))}
          {(phase === "done" || phase === "error") && (
            <button type="button" className={styles.btnGhost} onClick={reset}>
              ↻ Reset
            </button>
          )}
        </div>
        <div className={styles.scenarioCurrentLabel}>
          {currentScenario ? currentScenario.shortLabel : "Free input — escribí tu propio prompt"}
        </div>

      </section>

      <section className="lyt-block lyt-align-fullbleed lyt-dark lyt-tight">
        {errorMsg && (
          <div className={styles.haltBanner}>
            <strong>Error</strong>
            <span>{errorMsg}</span>
          </div>
        )}
        {steerStatus === "rejected" && (
          <div className={styles.haltBanner}>
            <strong>Steering rechazado</strong>
            <span>El modelo continuó sin corrección.</span>
          </div>
        )}

        <div ref={stageRef} className={`${styles.stage} ${showStrip ? styles.stageEndState : ""}`}>
          <div ref={tokensColRef} className={styles.tokensCol}>
            {activePrompt && (
              <div className={styles.activePromptBox}>
                <div className={styles.activePromptLabel}>prompt</div>
                <div className={styles.activePromptText}>{activePrompt}</div>
              </div>
            )}
            <div className={styles.tokensList}>
              {tokens.map((tok) => {
                if (tok.isSeparator) {
                  return (
                    <div key={`sep-${tok.id}`} className={styles.steeringSeparator}>
                      {tok.text}
                    </div>
                  );
                }
                const consumed = consumedIds.has(tok.id);
                const target = targets[tok.id];
                const isFlight = flyingId === tok.id;
                const tier = tierOfToken(tok);
                const cls = [
                  styles.tokenChip,
                  isFlight && styles.tokenFlying,
                  isFlight && tier === "decep" && styles.tokenDeceptiveFlight,
                  isFlight && tier === "warn" && styles.tokenWarnFlight,
                  tok.phaseLabel === "steered" && styles.tokenSteered,
                ]
                  .filter(Boolean)
                  .join(" ");
                return (
                  <motion.span
                    key={tok.id}
                    ref={(el) => {
                      if (el) tokenRefs.current.set(tok.id, el);
                      else tokenRefs.current.delete(tok.id);
                    }}
                    className={cls}
                    initial={false}
                    animate={
                      consumed
                        ? {
                            x: target?.dx ?? 0,
                            y: target?.dy ?? 0,
                            opacity: 0,
                            scale: 0.55,
                          }
                        : { x: 0, y: 0, opacity: phase === "idle" ? 0.55 : 0.85, scale: 1 }
                    }
                    transition={{
                      duration: FILLER_TRAVEL_MS / 1000,
                      ease: [0.22, 1, 0.36, 1],
                      opacity: { duration: FILLER_TRAVEL_MS / 1000, ease: [0.4, 0, 0.6, 1] },
                    }}
                  >
                    {tok.text.trim() || tok.text}
                  </motion.span>
                );
              })}
            </div>
          </div>

          <div ref={travelerRef} className={styles.traveler} aria-hidden="true" />

          <div className={styles.avCol}>
            <div className={styles.avRing}>
              <div
                ref={avBoxRef}
                className={`${styles.avBox} ${pulsing ? styles.avPulsing : ""}`}
              >
                <div className={styles.avName}>AV</div>
              </div>
            </div>
            <div className={styles.avCaption}>
              decodifica activaciones · fase {currentPhaseLabel}
            </div>
          </div>

          <div className={styles.outputCol}>
            {phase === "idle" ? (
              <div className={styles.emptyHint}>
                {mode === "scenario"
                  ? "Elegí scenario con ← → y apretá Run."
                  : "Tipeá un prompt y mandá."}
              </div>
            ) : (
              <FlowPanel
                original={verdicts.original}
                steered={verdicts.steered}
                steerDelta={steerDelta}
                steerStatus={steerStatus}
                phase={phase}
                pendingSteer={pendingSteer}
                correctionPrompt={correctionPrompt}
                onConfirm={handleConfirmSteer}
                onReject={handleRejectSteer}
                steerCountdown={steerCountdown}
                judgeRunning={judgeRunning}
              />
            )}
          </div>

        </div>

      </section>

      <section className="lyt-block lyt-tight lyt-align-wide">
        <div className={styles.inspectionLayout}>
          <div className={styles.inspectionLeft}>
            <h2 className={styles.detailTitle}>Inspección por token</h2>
            <p
              className={styles.proseStream}
              onMouseLeave={() => setHoveredTokenId(null)}
            >
              {tokens
                .filter((t) => !t.isSeparator)
                .map((tok, i) => {
                  const tier = tierOfToken(tok);
                  const selected = selectedTokenId === tok.id;
                  const hovered = hoveredTokenId === tok.id;
                  const isLoaded = monologueByStep.has(tok.id);
                  const cls = [
                    styles.proseWord,
                    tier === "low" && styles.proseWordLow,
                    tier === "warn" && styles.proseWordWarn,
                    tier === "decep" && styles.proseWordDecep,
                    tier === "none" && isLoaded && styles.proseWordLoaded,
                    selected && styles.proseWordSelected,
                    hovered && styles.proseWordHovered,
                    tok.phaseLabel === "steered" && styles.proseWordSteered,
                  ]
                    .filter(Boolean)
                    .join(" ");
                  const raw = tok.text;
                  const display = raw.trim() || raw;
                  const leadingSpace = i > 0 && /^\s/.test(raw);
                  return (
                    <span key={tok.id}>
                      {leadingSpace ? " " : ""}
                      <span
                        className={cls}
                        tabIndex={0}
                        onMouseEnter={() => setHoveredTokenId(tok.id)}
                        onFocus={() => setHoveredTokenId(tok.id)}
                        onBlur={() => setHoveredTokenId(null)}
                        onClick={() =>
                          setSelectedTokenId((prev) =>
                            prev === tok.id ? null : tok.id
                          )
                        }
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            setSelectedTokenId((prev) =>
                              prev === tok.id ? null : tok.id
                            );
                          }
                        }}
                      >
                        {display}
                      </span>
                    </span>
                  );
                })}
            </p>
          </div>

          <div className={styles.bottomDetail}>
          {!activeToken ? (
            <div className={styles.detailEmpty}>
              Pasá el cursor sobre una palabra para leer el monólogo interno. Click para fijar.
            </div>
          ) : (
            <div className={styles.detailCard}>
              <div className={styles.detailHeader}>
                <div>
                  <span className={styles.judgeLabel}>Token</span>
                  <span className={styles.tokenChipBig}>
                    &ldquo;{activeToken.text}&rdquo;
                  </span>
                </div>
                <div>
                  <span className={styles.judgeLabel}>Fase</span>
                  <span className={styles.tokenChipBig}>
                    {activeToken.phaseLabel ?? "—"}
                  </span>
                </div>
                {selectedDivergence && (
                  <div>
                    <span className={styles.judgeLabel}>Severity</span>
                    <span className={styles.tokenChipBig}>
                      {selectedDivergence.severity}
                    </span>
                  </div>
                )}
              </div>

              <div className={styles.monologueBlock}>
                <div className={styles.monologueLabel}>Internal monologue</div>
                <div
                  className={`${styles.monologueText} ${
                    monologueByStep.get(activeToken.id) ||
                    selectedDivergence?.internal_thought
                      ? styles.monologueLoaded
                      : styles.monologueEmpty
                  }`}
                >
                  &ldquo;
                  {monologueByStep.get(activeToken.id) ??
                    selectedDivergence?.internal_thought ??
                    "—"}
                  &rdquo;
                </div>
              </div>

              {selectedDivergence && (
                <div className={styles.monologueBlock}>
                  <div className={styles.monologueLabel}>Verbal claim</div>
                  <div className={styles.monologueText}>
                    {selectedDivergence.verbal_claim}
                  </div>
                  <div className={styles.monologueLabel} style={{ marginTop: 8 }}>
                    Categoría
                  </div>
                  <div className={styles.monologueText}>
                    {selectedDivergence.category.replace(/_/g, " ")}
                  </div>
                </div>
              )}
            </div>
          )}
          </div>
        </div>
      </section>

      <section className={`lyt-block lyt-tight lyt-align-left ${styles.differenceTira}`}>
        <p className={styles.differenceTiraTitle}>
          Todos los monitores que conocés están <em>afuera</em> del modelo.
          <br />
          <span className={styles.differenceTiraTitleAccent}>Verbalize está adentro.</span>
        </p>
        <p className={styles.differenceTiraSub}>
          firewalls · output filters · CoT monitors · evals → todos black-box.
          Nosotros leemos activaciones del residual stream.
        </p>
        <div className={styles.kpiStrip} aria-label="key product stats">
          <div className={styles.kpiTile}>
            <span className={styles.kpiNumber}>4</span>
            <span className={styles.kpiLabel}>reglas auditadas</span>
            <span className={styles.kpiSub}>
              ai_disclosure · no_pii · financial_advice · sycophancy
            </span>
          </div>
          <div className={styles.kpiTile}>
            <span className={styles.kpiNumber}>
              5–8<span className={styles.kpiUnit}>s</span>
            </span>
            <span className={styles.kpiLabel}>por verbalización</span>
            <span className={styles.kpiSub}>Qwen-2.5-7B · NLA L20 · vast.ai A6000</span>
          </div>
          <div className={styles.kpiTile}>
            <span className={styles.kpiNumber}>0</span>
            <span className={styles.kpiLabel}>etiquetas</span>
            <span className={styles.kpiSub}>zero-shot · sin fine-tune · residual stream</span>
          </div>
        </div>
      </section>

      <section className="lyt-block lyt-tight lyt-align-left">
        <h2 className={styles.detailTitle}>
          El landscape de AI safety hoy vive afuera del modelo. Excepto este.
        </h2>
        <p className={styles.compareLead}>
          Firewalls, filtros, evals y monitoreo de CoT comparten un techo: tratan al modelo
          como caja negra y leen lo que el modelo decidió mostrar. <em>Esa señal la
          escribió el modelo sabiendo que iba a ser leída.</em> Nosotros leemos el residual
          stream — la única señal sobre la que nunca tuvo presión de entrenamiento.
        </p>
        <div className={styles.compareTableWrap}>
          <table className={styles.compareTable}>
            <colgroup>
              <col style={{ width: "30%" }} />
              <col style={{ width: "22%" }} />
              <col style={{ width: "28%" }} />
              <col style={{ width: "20%" }} />
            </colgroup>
            <thead>
              <tr>
                <th>Enfoque</th>
                <th>Lee</th>
                <th>¿Gameable?</th>
                <th>Output</th>
              </tr>
            </thead>
            <tbody>
              <tr className={styles.compareGroupRow}>
                <td colSpan={4}>
                  <span className={styles.compareGroupLabel}>black-box</span>
                  <span className={styles.compareGroupHint}>
                    afuera del modelo · ven lo que el modelo decidió mostrar
                  </span>
                </td>
              </tr>
              <tr>
                <td>
                  Firewalls / output filters
                  <span className={styles.compareNote}> · ej Lakera, Pillar, Prompt Armor</span>
                </td>
                <td>Strings de input/output</td>
                <td><span className={styles.compareYes}>Sí · encodea alrededor</span></td>
                <td>Block / redact</td>
              </tr>
              <tr>
                <td>
                  AI control / red-team evals
                  <span className={styles.compareNote}> · ej Apollo, Anthropic AI Control</span>
                </td>
                <td>Conversaciones pareadas</td>
                <td><span className={styles.compareYes}>Sí · eval awareness</span></td>
                <td>P(bad behavior) por escenario</td>
              </tr>
              <tr>
                <td>
                  Monitoreo de CoT
                  <span className={styles.compareNote}> · lo que la mayoría va a construir</span>
                </td>
                <td>Trazo escrito por el modelo</td>
                <td><span className={styles.compareYes}>Sí · performativo</span></td>
                <td>Texto libre, performado</td>
              </tr>
              <tr>
                <td>Clasificadores de output</td>
                <td>String final</td>
                <td><span className={styles.compareYes}>Trivialmente</span></td>
                <td>Booleano</td>
              </tr>

              <tr className={`${styles.compareGroupRow} ${styles.compareGroupRowOurs}`}>
                <td colSpan={4}>
                  <span className={`${styles.compareGroupLabel} ${styles.compareGroupLabelOurs}`}>
                    white-box
                  </span>
                  <span className={styles.compareGroupHint}>
                    adentro del modelo · ven lo que el modelo está computando
                  </span>
                </td>
              </tr>
              <tr>
                <td>Probes de activaciones</td>
                <td>Estado oculto</td>
                <td><span className={styles.compareNo}>No</span></td>
                <td>Un escalar por concepto fijo</td>
              </tr>
              <tr className={styles.compareRowOurs}>
                <td>
                  <span className={styles.compareUs}>verbalize</span>
                </td>
                <td>Residual stream → texto libre</td>
                <td><span className={styles.compareNo}>No · señal no-performada</span></td>
                <td>Auditoría contra cualquier rúbrica</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

    </main>
  );
}

