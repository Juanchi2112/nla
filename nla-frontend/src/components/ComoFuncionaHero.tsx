"use client";

import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import s from "./ComoFuncionaHero.module.css";

const VERBAL = ["el", "paciente", "está", "estable", "según", "registros"];
const NLA = ["sujeto", "humano", "estado", "ocultar test", "fuente", "datos"];
const DECEPTION_IDX = 3;
const FLOATS_PER_TOKEN = 4;
const TOTAL_FLOATS = VERBAL.length * FLOATS_PER_TOKEN;

const randFloat = () => {
  const v = (Math.random() * 4 - 2).toFixed(2);
  return v.startsWith("-") ? v : "+" + v;
};
const buildVector = () => Array.from({ length: TOTAL_FLOATS }, randFloat);

export default function ComoFuncionaHero() {
  const rootRef = useRef<HTMLElement>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const intervalsRef = useRef<ReturnType<typeof setInterval>[]>([]);
  const prefersReduced = useReducedMotion();

  const [headIn, setHeadIn] = useState(false);
  const [appeared, setAppeared] = useState<boolean[]>(() => VERBAL.map(() => false));
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const [revealed, setRevealed] = useState<boolean[]>(() => VERBAL.map(() => false));
  const [vector, setVector] = useState<string[]>(() =>
    Array.from({ length: TOTAL_FLOATS }, () => "+0.00")
  );
  const [diverged, setDiverged] = useState(false);
  const [climax, setClimax] = useState(false);
  const [showCaption, setShowCaption] = useState(false);
  const [fading, setFading] = useState(false);

  const setT = (fn: () => void, ms: number) => {
    const id = setTimeout(fn, ms);
    timersRef.current.push(id);
    return id;
  };
  const clearAll = () => {
    timersRef.current.forEach(clearTimeout);
    intervalsRef.current.forEach(clearInterval);
    timersRef.current = [];
    intervalsRef.current = [];
  };

  const reset = () => {
    clearAll();
    setHeadIn(false);
    setAppeared(VERBAL.map(() => false));
    setActiveIdx(null);
    setRevealed(VERBAL.map(() => false));
    setVector(buildVector());
    setDiverged(false);
    setClimax(false);
    setShowCaption(false);
    setFading(false);
  };

  const flickerColumn = (colIdx: number, durationMs: number) => {
    const start = colIdx * FLOATS_PER_TOKEN;
    const id = setInterval(() => {
      setVector((prev) => {
        const next = [...prev];
        for (let i = 0; i < FLOATS_PER_TOKEN; i++) next[start + i] = randFloat();
        return next;
      });
    }, 70);
    intervalsRef.current.push(id);
    setT(() => {
      clearInterval(id);
      intervalsRef.current = intervalsRef.current.filter((x) => x !== id);
    }, durationMs);
  };

  const persistentFlicker = (colIdx: number) => {
    const start = colIdx * FLOATS_PER_TOKEN;
    const id = setInterval(() => {
      setVector((prev) => {
        const next = [...prev];
        for (let i = 0; i < FLOATS_PER_TOKEN; i++) next[start + i] = randFloat();
        return next;
      });
    }, 110);
    intervalsRef.current.push(id);
  };

  const runCycle = () => {
    reset();

    if (prefersReduced) {
      setHeadIn(true);
      setAppeared(VERBAL.map(() => true));
      setRevealed(VERBAL.map(() => true));
      setDiverged(true);
      setShowCaption(true);
      return;
    }

    setT(() => setHeadIn(true), 80);

    const appearStart = 700;
    const appearStep = 90;
    VERBAL.forEach((_, i) => {
      setT(() => {
        setAppeared((prev) => {
          const n = [...prev];
          n[i] = true;
          return n;
        });
      }, appearStart + i * appearStep);
    });

    const scanStart = appearStart + VERBAL.length * appearStep + 350;
    const stepDur = 380;
    let cursor = scanStart;
    VERBAL.forEach((_, i) => {
      const isDeceptive = i === DECEPTION_IDX;
      const t0 = cursor;
      // Beat of silence before the deceptive token
      const pause = isDeceptive ? 280 : 0;
      const tStart = t0 + pause;
      setT(() => setActiveIdx(i), tStart);
      setT(() => flickerColumn(i, 280), tStart + 30);
      setT(() => {
        setRevealed((prev) => {
          const n = [...prev];
          n[i] = true;
          return n;
        });
      }, tStart + 120);
      if (isDeceptive) {
        setT(() => setClimax(true), tStart + 60);
        setT(() => setDiverged(true), tStart + 240);
        setT(() => persistentFlicker(i), tStart + 260);
      }
      cursor = tStart + stepDur;
    });

    const scanEnd = cursor;

    setT(() => setShowCaption(true), scanEnd + 600);
    setT(() => setActiveIdx(null), scanEnd + 1100);
    setT(() => setClimax(false), scanEnd + 1600);
  };

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    let started = false;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !started) {
            started = true;
            runCycle();
            observer.disconnect();
          }
        });
      },
      { threshold: 0.4 }
    );
    observer.observe(el);
    return () => {
      observer.disconnect();
      clearAll();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const colCount = VERBAL.length;
  const stageStyle: CSSProperties = {
    "--col-count": colCount,
    "--floats-per-col": FLOATS_PER_TOKEN,
    "--deception-col": DECEPTION_IDX + 1,
  } as CSSProperties;

  const stageVariants = {
    idle: { rotateX: 0, scale: 1 },
    active: { rotateX: 0, scale: 1.015 },
    climax: { rotateX: 2, scale: 1.02 },
  };

  const focusStateOf = (i: number): "active" | "dim" | "neutral" => {
    if (activeIdx === null) return "neutral";
    if (activeIdx === i) return "active";
    return "dim";
  };

  return (
    <section
      ref={rootRef}
      className={`${s.hero} ${fading ? s.fading : ""} ${climax ? s.heroClimax : ""}`}
      aria-label="Demostración NLA"
    >
      <div className={`${s.head} ${headIn ? s.headIn : ""}`}>
        <h1 className={s.headline}>
          Lo que el modelo <span className={s.headlineAccent}>dice</span>
          {" "}no siempre es lo que{" "}
          <span className={s.headlineAccent}>piensa</span>.
        </h1>
      </div>

      <div className={s.stagePerspective}>
        <motion.div
          className={`${s.stage} ${diverged ? s.divergedStage : ""} ${climax ? s.stageClimax : ""}`}
          style={stageStyle}
          variants={stageVariants}
          animate={climax ? "climax" : activeIdx !== null ? "active" : "idle"}
          transition={{ duration: 0.7, ease: [0.2, 0.8, 0.2, 1] }}
        >
          {diverged && <div className={s.divergenceColumn} aria-hidden />}

          <div className={s.rowLabel} style={{ gridRow: 1, gridColumn: 1 }}>VERBAL</div>
          <div className={s.tokenRow}>
            {VERBAL.map((tok, i) => {
              const focus = focusStateOf(i);
              const isDeceptive = diverged && i === DECEPTION_IDX;
              return (
                <motion.span
                  key={i}
                  style={{ gridRow: 1, gridColumn: i + 2 }}
                  className={[
                    s.tokenChip,
                    appeared[i] && s.appear,
                    focus === "active" && s.active,
                    isDeceptive && s.deceptive,
                  ].filter(Boolean).join(" ")}
                  animate={{
                    scale: focus === "active" ? (isDeceptive ? 1.09 : 1.06) : 1,
                    z: focus === "active" ? 30 : focus === "dim" ? -12 : 0,
                    filter:
                      focus === "dim"
                        ? `blur(var(--depth-blur)) opacity(var(--depth-opacity))`
                        : "blur(0px) opacity(1)",
                  }}
                  transition={{ duration: 0.45, ease: [0.2, 0.8, 0.2, 1] }}
                >
                  {tok}
                </motion.span>
              );
            })}
          </div>

          <div className={s.rowLabel} aria-hidden style={{ gridRow: 2, gridColumn: 1 }}>AV</div>
          <div className={s.encoderRow} aria-hidden>
            {VERBAL.map((_, i) => {
              const focus = focusStateOf(i);
              const isDeceptive = diverged && i === DECEPTION_IDX;
              return (
                <motion.div
                  key={i}
                  style={{ gridRow: 2, gridColumn: i + 2 }}
                  className={[
                    s.encoderCell,
                    focus === "active" && s.encoderActive,
                    isDeceptive && s.encoderDanger,
                  ].filter(Boolean).join(" ")}
                  animate={{
                    opacity: focus === "dim" ? 0.45 : 1,
                  }}
                  transition={{ duration: 0.35 }}
                >
                  <span className={s.arrowDown}>↓</span>
                </motion.div>
              );
            })}
          </div>

          <div className={s.rowLabel} aria-hidden style={{ gridRow: 3, gridColumn: 1 }}>vec</div>
          <div className={s.vectorRow} aria-hidden>
            {vector.map((v, i) => {
              const col = Math.floor(i / FLOATS_PER_TOKEN);
              const isActive = activeIdx === col;
              const isDanger = diverged && col === DECEPTION_IDX;
              const isDim = activeIdx !== null && !isActive;
              return (
                <span
                  key={i}
                  className={[
                    s.vectorCell,
                    isActive && s.vectorActive,
                    isDanger && s.vectorDanger,
                    isDim && s.vectorDim,
                  ].filter(Boolean).join(" ")}
                >
                  {v}
                </span>
              );
            })}
          </div>

          <div className={s.rowLabel} aria-hidden style={{ gridRow: 4, gridColumn: 1 }}>AR</div>
          <div className={s.encoderRow} aria-hidden>
            {VERBAL.map((_, i) => {
              const focus = focusStateOf(i);
              const isDeceptive = diverged && i === DECEPTION_IDX;
              return (
                <motion.div
                  key={i}
                  style={{ gridRow: 4, gridColumn: i + 2 }}
                  className={[
                    s.encoderCell,
                    focus === "active" && s.encoderActive,
                    isDeceptive && s.encoderDanger,
                  ].filter(Boolean).join(" ")}
                  animate={{
                    opacity: focus === "dim" ? 0.45 : 1,
                  }}
                  transition={{ duration: 0.35 }}
                >
                  <span className={s.arrowDown}>↓</span>
                </motion.div>
              );
            })}
          </div>

          <div className={s.rowLabel} style={{ gridRow: 5, gridColumn: 1 }}>NLA</div>
          <div className={s.tokenRow}>
            {NLA.map((w, i) => {
              const focus = focusStateOf(i);
              const isRevealed = revealed[i];
              const isDeceptive = diverged && i === DECEPTION_IDX;
              return (
                <motion.span
                  key={i}
                  style={{ gridRow: 5, gridColumn: i + 2 }}
                  className={[
                    s.thoughtChip,
                    isRevealed && s.appear,
                    isDeceptive && s.deceptive,
                  ].filter(Boolean).join(" ")}
                  animate={{
                    scale: focus === "active" ? (isDeceptive ? 1.09 : 1.06) : 1,
                    z: focus === "active" ? 30 : focus === "dim" ? -12 : 0,
                    filter:
                      focus === "dim"
                        ? `blur(var(--depth-blur)) opacity(var(--depth-opacity))`
                        : "blur(0px) opacity(1)",
                  }}
                  transition={{ duration: 0.45, ease: [0.2, 0.8, 0.2, 1] }}
                >
                  <span className={s.thoughtPlaceholder} aria-hidden>·</span>
                  <AnimatePresence>
                    {isRevealed && (
                      <motion.span
                        key="ink"
                        className={`${s.ink} ${isDeceptive ? s.inkRed : ""}`}
                        initial={{ opacity: 0, ["--ink-r" as string]: "0%" }}
                        animate={{ opacity: 1, ["--ink-r" as string]: "140%" }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.55, ease: [0.2, 0.8, 0.2, 1] }}
                      >
                        {w}
                      </motion.span>
                    )}
                  </AnimatePresence>
                  {isDeceptive && (
                    <span className={s.deceptionBadgeWrap} aria-hidden>
                      <span className={s.deceptionBadge}>Divergencia · 0.91</span>
                    </span>
                  )}
                </motion.span>
              );
            })}
          </div>
        </motion.div>
      </div>

      <p className={`${s.caption} ${showCaption ? s.captionShow : ""}`}>
        El verbalizador (AV) traduce la activación interna a lenguaje natural.
        NLA detecta cuando el pensamiento diverge del habla.
      </p>
    </section>
  );
}
