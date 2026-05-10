"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { motion } from "framer-motion";
import styles from "./page.module.css";
import { mockScenario, buildScenarioFromDecode, type Token, type Scenario } from "@/lib/mockData";
import { decode } from "@/lib/nlaApi";

type Phase = "idle" | "running" | "halted" | "done";

const FILLER_TRAVEL_MS = 520;
const TRACED_TRAVEL_MS = 760;
const FILLER_BATCH_SIZE = 3;
const FILLER_STAGGER_MS = 90;
const FILLER_BATCH_GAP_MS = 140;
const AV_HOLD_MS = 80;
const TRAVEL_FROM_AV_MS = 280;
const HALT_HOLD_MS = 500;
const TRAVEL_EASE = "cubic-bezier(0.65, 0, 0.35, 1)";

type Target = { dx: number; dy: number };

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [emittedTokens, setEmittedTokens] = useState<Token[]>([]);
  const [consumedIds, setConsumedIds] = useState<Set<number>>(new Set());
  const [targets, setTargets] = useState<Record<number, Target>>({});
  const [flyingTracedId, setFlyingTracedId] = useState<number | null>(null);
  const [pulsing, setPulsing] = useState(false);
  const [selectedTokenId, setSelectedTokenId] = useState<number | null>(null);
  const [haltedToken, setHaltedToken] = useState<Token | null>(null);
  const [streamedPrompt, setStreamedPrompt] = useState("");
  const [promptStreamDone, setPromptStreamDone] = useState(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const stoppedRef = useRef(false);
  const activeAnimRef = useRef<Animation | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const avBoxRef = useRef<HTMLDivElement | null>(null);
  const travelerRef = useRef<HTMLDivElement | null>(null);
  const tokenRefs = useRef<Map<number, HTMLSpanElement>>(new Map());
  const thoughtSlotRefs = useRef<Map<number, HTMLElement>>(new Map());

  const [scenario, setScenario] = useState<Scenario>(mockScenario);
  const tokens = scenario.tokens;
  const tracedTokens = useMemo(() => tokens.filter((t) => t.nla_trace), [tokens]);

  useEffect(() => {
    let cancelled = false;
    decode(mockScenario.prompt)
      .then((resp) => {
        if (cancelled) return;
        setScenario(buildScenarioFromDecode(resp, mockScenario));
      })
      .catch((e) => {
        console.warn("[nla] decode failed, using mock:", e);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const target = mockScenario.prompt;
    const startDelay = 1100;
    const charDelay = 26;
    const timers: ReturnType<typeof setTimeout>[] = [];
    timers.push(
      setTimeout(() => {
        let i = 0;
        const tick = () => {
          i++;
          setStreamedPrompt(target.slice(0, i));
          if (i < target.length) {
            timers.push(setTimeout(tick, charDelay));
          } else {
            timers.push(setTimeout(() => setPromptStreamDone(true), 400));
          }
        };
        tick();
      }, startDelay)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  const cleanup = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    stoppedRef.current = true;
    if (activeAnimRef.current) {
      try { activeAnimRef.current.cancel(); } catch {}
      activeAnimRef.current = null;
    }
  };
  useEffect(() => cleanup, []);

  const sleep = (ms: number) =>
    new Promise<void>((resolve) => {
      const id = setTimeout(resolve, ms);
      timersRef.current.push(id);
    });

  const animateTraveler = (
    el: HTMLElement,
    keyframes: Keyframe[],
    duration: number
  ): Promise<void> =>
    new Promise((resolve) => {
      const anim = el.animate(keyframes, {
        duration,
        easing: TRAVEL_EASE,
        fill: "forwards",
      });
      activeAnimRef.current = anim;
      anim.onfinish = () => {
        if (activeAnimRef.current === anim) activeAnimRef.current = null;
        resolve();
      };
      anim.oncancel = () => {
        if (activeAnimRef.current === anim) activeAnimRef.current = null;
        resolve();
      };
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
    if (isTraced) setFlyingTracedId(tok.id);
    // Defer one frame so animate target is set before consumed flips
    requestAnimationFrame(() => consume(tok.id));
  };

  const emitTracedThought = async (tok: Token) => {
    setEmittedTokens((prev) => [...prev, tok]);
    await sleep(220);
  };

  const startStream = async () => {
    cleanup();
    stoppedRef.current = false;
    setEmittedTokens([]);
    setConsumedIds(new Set());
    setTargets({});
    setFlyingTracedId(null);
    setHaltedToken(null);
    setSelectedTokenId(null);
    setPhase("running");

    const traveler = travelerRef.current;
    if (!traveler) return;
    traveler.style.transform = "none";
    traveler.style.opacity = "0";

    let i = 0;
    while (i < tokens.length) {
      if (stoppedRef.current) return;
      const tok = tokens[i];

      if (tok.nla_trace) {
        setPulsing(true);
        launch(tok, true);
        await sleep(TRACED_TRAVEL_MS);
        if (stoppedRef.current) return;
        await sleep(AV_HOLD_MS);
        if (stoppedRef.current) return;
        await emitTracedThought(tok);
        if (stoppedRef.current) return;
        setFlyingTracedId(null);
        setPulsing(false);

        if (tok.nla_trace.judge_score > 0.8) {
          setHaltedToken(tok);
          setPhase("halted");
          await sleep(HALT_HOLD_MS);
          if (stoppedRef.current) return;
          return;
        }
        i++;
      } else {
        const batch: Token[] = [];
        while (
          i < tokens.length &&
          batch.length < FILLER_BATCH_SIZE &&
          !tokens[i].nla_trace
        ) {
          batch.push(tokens[i]);
          i++;
        }
        setPulsing(true);
        batch.forEach((t, lane) => {
          const dly = setTimeout(() => {
            if (stoppedRef.current) return;
            launch(t, false);
          }, lane * FILLER_STAGGER_MS);
          timersRef.current.push(dly);
        });
        await sleep(FILLER_STAGGER_MS * batch.length + FILLER_BATCH_GAP_MS);
      }
    }

    await sleep(FILLER_TRAVEL_MS);
    if (stoppedRef.current) return;
    setPulsing(false);
    setPhase("done");
  };

  const reset = () => {
    cleanup();
    stoppedRef.current = false;
    setPhase("idle");
    setEmittedTokens([]);
    setConsumedIds(new Set());
    setTargets({});
    setFlyingTracedId(null);
    setHaltedToken(null);
    setSelectedTokenId(null);
    setPulsing(false);
    if (travelerRef.current) {
      travelerRef.current.getAnimations().forEach((a) => a.cancel());
      travelerRef.current.style.transition = "none";
      travelerRef.current.style.opacity = "0";
      travelerRef.current.style.transform = "none";
      travelerRef.current.textContent = "";
      travelerRef.current.className = styles.traveler;
    }
  };

  const selectedToken = useMemo(
    () => tokens.find((t) => t.id === selectedTokenId) ?? null,
    [tokens, selectedTokenId]
  );

  const isHalted = phase === "halted";
  const showStrip = phase === "done" || phase === "halted";

  const tierOf = (tok: Token): "none" | "low" | "warn" | "decep" => {
    if (!tok.nla_trace) return "none";
    const s = tok.nla_trace.judge_score;
    if (s > 0.8) return "decep";
    if (s > 0.5) return "warn";
    return "low";
  };

  return (
    <main className={`lyt-grid ${isHalted ? styles.haltedVignette : ""}`}>
      <section className="lyt-block lyt-loose lyt-title-huge lyt-align-left">
        <h1 className={styles.headline}>
          Lo que el modelo dice <span className={styles.headlineAccent}>vs.</span> lo que está pensando.
        </h1>
        <div className={styles.promptCard}>
          {streamedPrompt.length === 0 ? (
            <span className={`${styles.promptText} ${styles.promptPlaceholder}`}>
              Send a message...
            </span>
          ) : (
            <span className={styles.promptText}>
              {streamedPrompt}
              {!promptStreamDone && <span className={styles.promptCaret} />}
            </span>
          )}
          <button className={styles.promptSendBtn} aria-label="Send" tabIndex={-1}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </div>
      </section>

      <section className="lyt-block lyt-align-fullbleed lyt-dark lyt-tight">
        {isHalted && haltedToken && (
          <div className={styles.haltBanner}>
            <strong>⚠ Deception Detected — score {haltedToken.nla_trace?.judge_score.toFixed(2)}</strong>
            <span>Generación halted. La activación interna divergió del output verbal.</span>
          </div>
        )}

        <div ref={stageRef} className={`${styles.stage} ${showStrip ? styles.stageEndState : ""}`}>
          {/* LEFT: tokens (motion chips that fly to AV when consumed) */}
          <div className={styles.tokensCol}>
            <div className={styles.tokensList}>
              {tokens.map((tok) => {
                const consumed = consumedIds.has(tok.id);
                const target = targets[tok.id];
                const isTracedFlight = flyingTracedId === tok.id;
                const tier = tierOf(tok);
                const cls = [
                  styles.tokenChip,
                  isTracedFlight && styles.tokenFlying,
                  isTracedFlight && tier === "decep" && styles.tokenDeceptiveFlight,
                  isTracedFlight && tier === "warn" && styles.tokenWarnFlight,
                ].filter(Boolean).join(" ");
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
                            scale: 0.4,
                          }
                        : { x: 0, y: 0, opacity: phase === "idle" ? 0.55 : 0.85, scale: 1 }
                    }
                    transition={{
                      duration: isTracedFlight ? TRACED_TRAVEL_MS / 1000 : FILLER_TRAVEL_MS / 1000,
                      ease: [0.65, 0, 0.35, 1],
                    }}
                  >
                    {tok.text.trim() || tok.text}
                  </motion.span>
                );
              })}
            </div>
          </div>

          {/* TRAVELER (animated thought from AV to slot) */}
          <div ref={travelerRef} className={styles.traveler} aria-hidden="true" />

          {/* CENTER: AV */}
          <div className={styles.avCol}>
            <div className={styles.avRing}>
              <div ref={avBoxRef} className={`${styles.avBox} ${pulsing ? styles.avPulsing : ""} ${isHalted ? styles.avHalted : ""}`}>
                <div className={styles.avName}>AV</div>
              </div>
            </div>
            <div className={styles.avCaption}>decodifica activaciones a lenguaje natural</div>

            <div className={styles.controls}>
              {(phase === "idle" || phase === "done") && (
                <button
                  className={styles.btnPrimary}
                  onClick={startStream}
                  onMouseEnter={(e) => {
                    const r = e.currentTarget.getBoundingClientRect();
                    e.currentTarget.style.setProperty("--rx", `${e.clientX - r.left}px`);
                    e.currentTarget.style.setProperty("--ry", `${e.clientY - r.top}px`);
                  }}
                  onMouseLeave={(e) => {
                    const r = e.currentTarget.getBoundingClientRect();
                    e.currentTarget.style.setProperty("--rx", `${e.clientX - r.left}px`);
                    e.currentTarget.style.setProperty("--ry", `${e.clientY - r.top}px`);
                  }}
                >
                  ▶ Run Inference
                </button>
              )}
              {phase === "running" && (
                <button className={styles.btnDisabled} disabled>
                  Streaming…
                </button>
              )}
              {phase === "halted" && (
                <button className={styles.btnGhost} onClick={reset}>
                  ↻ Reset
                </button>
              )}
            </div>
          </div>

          {/* RIGHT: criticas (only emitted traced thoughts) or idle hint */}
          <div className={styles.thoughtsCol}>
            <div className={styles.thoughtsList}>
              {phase === "idle" && (
                <div className={styles.emptyHint}>Apretá Run Inference para empezar.</div>
              )}
              {phase !== "idle" && tracedTokens.map((tok) => {
                const trace = tok.nla_trace!;
                const emitted = emittedTokens.some((t) => t.id === tok.id);
                const isDecep = trace.judge_score > 0.8;
                const isWarn = trace.judge_score > 0.5 && trace.judge_score <= 0.8;
                const tier = isDecep ? "high" : isWarn ? "mid" : "low";
                const cls = [
                  styles.thoughtChip,
                  !emitted && styles.thoughtPending,
                  emitted && styles.thoughtVisible,
                  isDecep && styles.thoughtDeceptive,
                  isWarn && styles.thoughtWarn,
                ]
                  .filter(Boolean)
                  .join(" ");
                return (
                  <article
                    key={tok.id}
                    ref={(el) => {
                      if (el) thoughtSlotRefs.current.set(tok.id, el);
                      else thoughtSlotRefs.current.delete(tok.id);
                    }}
                    className={cls}
                  >
                    <header className={styles.thoughtHeader}>
                      <span className={styles.thoughtKicker}>{tok.text.trim()}</span>
                      {trace.judge_score > 0.5 && (
                        <span className={styles.thoughtScore} data-tier={tier}>
                          {trace.judge_score.toFixed(2)}
                        </span>
                      )}
                    </header>
                    <p className={styles.thoughtBody}>{trace.internal_monologue}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="lyt-block lyt-loose lyt-align-left">
          <h2 className={styles.detailTitle}>Inspección</h2>
          <div className={styles.bottomStrip}>
            {tokens.map((tok) => {
              const tier = tierOf(tok);
              const selected = selectedTokenId === tok.id;
              const cls = [
                styles.stripChip,
                tier === "low" && styles.stripChipLow,
                tier === "warn" && styles.stripChipWarn,
                tier === "decep" && styles.stripChipDecep,
                selected && styles.stripChipSelected,
              ].filter(Boolean).join(" ");
              return (
                <button
                  key={tok.id}
                  type="button"
                  className={cls}
                  onClick={() =>
                    setSelectedTokenId((prev) => (prev === tok.id ? null : tok.id))
                  }
                >
                  {tok.text.trim() || tok.text}
                </button>
              );
            })}
          </div>

          <div className={styles.bottomDetail}>
            {!selectedToken ? (
              <div className={styles.detailEmpty}>
                Hacé click en un token para ver su traza.
              </div>
            ) : !selectedToken.nla_trace ? (
              <div className={styles.detailEmpty}>
                Sin información de traza para &ldquo;{selectedToken.text.trim()}&rdquo;.
              </div>
            ) : (
              <div className={styles.detailCard}>
                <div className={styles.detailHeader}>
                  <div>
                    <span className={styles.judgeLabel}>Token</span>
                    <span className={styles.tokenChipBig}>&ldquo;{selectedToken.text}&rdquo;</span>
                  </div>
                  <div className={styles.detailScore}>
                    <span className={styles.judgeLabel}>LLM Judge</span>
                    <span
                      className={styles.scoreBadgeBig}
                      style={{
                        color:
                          selectedToken.nla_trace.judge_score > 0.8
                            ? "var(--diagram-red)"
                            : selectedToken.nla_trace.judge_score > 0.5
                              ? "var(--diagram-gold-dark)"
                              : "var(--fg)",
                      }}
                    >
                      {selectedToken.nla_trace.judge_score.toFixed(2)}
                    </span>
                  </div>
                </div>

                <div className={styles.barTrack}>
                  <div
                    className={styles.barFill}
                    style={{
                      width: `${selectedToken.nla_trace.judge_score * 100}%`,
                      backgroundColor:
                        selectedToken.nla_trace.judge_score > 0.8
                          ? "var(--diagram-red)"
                          : selectedToken.nla_trace.judge_score > 0.5
                            ? "var(--diagram-gold)"
                            : "var(--accent)",
                    }}
                  />
                </div>

                <div className={styles.monologueBlock}>
                  <div className={styles.monologueLabel}>Internal monologue</div>
                  <div className={styles.monologueText}>
                    &ldquo;{selectedToken.nla_trace.internal_monologue}&rdquo;
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
    </main>
  );
}
