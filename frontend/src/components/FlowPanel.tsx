"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import styles from "./FlowPanel.module.css";
import type { TurnVerdict, Divergence } from "@/lib/nlaApi";

// Fase numérica para comparar progreso — solo sube, nunca baja
const PHASE_ORDER = [
  "waiting",
  "output",
  "divergences",
  "incumplimiento",
  "correcting",
  "migrating",
  "rerunning",
  "final",
] as const;

type FlowPhase = (typeof PHASE_ORDER)[number];

function phaseGte(current: FlowPhase, target: FlowPhase) {
  return PHASE_ORDER.indexOf(current) >= PHASE_ORDER.indexOf(target);
}

interface FlowPanelProps {
  original?: TurnVerdict;
  steered?: TurnVerdict;
  steerDelta?: { original: number; steered: number; delta: number } | null;
  steerStatus: "idle" | "started" | "rejected";
  phase: "idle" | "running" | "done" | "error";
  pendingSteer: { correction_prompt: string; reason: string } | null;
  correctionPrompt?: string | null;
  onConfirm?: () => void;
  onReject?: () => void;
  steerCountdown?: number;
}

function formatCategory(cat: string) {
  return cat.replace(/_/g, " ").split(" ").slice(0, 2).join(" ");
}

function delay(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}

export default function FlowPanel({
  original,
  steered,
  steerDelta,
  steerStatus,
  phase,
  pendingSteer,
  correctionPrompt,
  onConfirm,
  onReject,
  steerCountdown,
}: FlowPanelProps) {
  const [flowPhase, setFlowPhase] = useState<FlowPhase>("waiting");
  const [savedPrompt, setSavedPrompt] = useState<string | null>(null);
  const seqRef = useRef(false);
  const rerunTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Avanza la fase, pero nunca retrocede (historial acumulativo)
  const advance = (next: FlowPhase) =>
    setFlowPhase((cur) =>
      PHASE_ORDER.indexOf(next) > PHASE_ORDER.indexOf(cur) ? next : cur
    );

  // Guardar el prompt TAN PRONTO como llega — independiente del steerStatus
  useEffect(() => {
    if (pendingSteer?.correction_prompt) {
      setSavedPrompt((prev) => prev ?? pendingSteer.correction_prompt);
    }
  }, [pendingSteer]);

  useEffect(() => {
    if (phase === "idle" || phase === "error") {
      setFlowPhase("waiting");
      setSavedPrompt(null);
      seqRef.current = false;
      if (rerunTimerRef.current) {
        clearTimeout(rerunTimerRef.current);
        rerunTimerRef.current = null;
      }
      return;
    }

    if (steered && original) {
      advance("final");
      return;
    }

    if (steerStatus === "started") {
      advance("migrating");
      if (!rerunTimerRef.current) {
        rerunTimerRef.current = setTimeout(() => {
          advance("rerunning");
          rerunTimerRef.current = null;
        }, 1800);
      }
      return;
    }

    if ((pendingSteer || correctionPrompt) && original) {

      if (seqRef.current) return;
      seqRef.current = true;

      const seq = async () => {
        if (original.divergences?.length) {
          await delay(300);
          advance("output");
          await delay(1400);
          advance("divergences");
          await delay(1600);
          advance("incumplimiento");
          await delay(1000);
        }
        advance("correcting");
        seqRef.current = false;
      };
      seq();
      return;
    }

    if (original?.divergences?.length) {
      if (seqRef.current) return;
      seqRef.current = true;
      const seq = async () => {
        await delay(300);
        advance("output");
        await delay(1200);
        advance("divergences");
        seqRef.current = false;
      };
      seq();
    }
  }, [original, steered, steerStatus, pendingSteer, correctionPrompt, phase]);

  const fp = flowPhase;
  const correctionText = correctionPrompt ?? savedPrompt ?? pendingSteer?.correction_prompt ?? null;

  return (
    <div className={styles.flowRoot}>

      {/* ── WAITING ── */}
      {fp === "waiting" && (
        <motion.div
          className={styles.waitingState}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          <div className={styles.spinner} />
          <p className={styles.waitingText}>Analizando tokens...</p>
        </motion.div>
      )}

      {/* ── SALIDA ORIGINAL ── suma y permanece */}
      {phaseGte(fp, "output") && original && (
        <motion.div
          className={styles.outputSection}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
        >
          <div className={styles.outputLabel}>Salida original</div>
          <div className={styles.outputBox}>{original.summary}</div>
        </motion.div>
      )}

      {/* ── DIVERGENCIAS ── suma y permanece */}
      {phaseGte(fp, "divergences") && original && (
        <motion.div
          className={styles.divergencesSection}
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className={styles.divergencesTitle}>
            Divergencias detectadas ({original.divergences.length})
          </div>
          <motion.div
            className={styles.divergencesContainer}
            initial="hidden"
            animate="visible"
            variants={{
              hidden: { opacity: 0 },
              visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
            }}
          >
            {original.divergences.map((div, idx) => (
              <DivergenceChip key={idx} divergence={div} />
            ))}
          </motion.div>
        </motion.div>
      )}

      {/* ── INCUMPLIMIENTO ── suma y permanece */}
      {phaseGte(fp, "incumplimiento") && (
        <>
          <div className={styles.connectorArrow}>↓</div>
          <motion.div
            className={styles.incumplimientoBanner}
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", damping: 12, mass: 0.7 }}
          >
            <div className={styles.incumplimientoTitle}>INCUMPLIMIENTO</div>
            <div className={styles.incumplimientoSub}>
              El modelo divergió de las reglas de alineamiento
            </div>
          </motion.div>
        </>
      )}

      {/* ── CORRECTION PROMPT ── suma y permanece (fijo) */}
      {phaseGte(fp, "correcting") && correctionText && (
        <motion.div
          className={styles.correctionBlock}
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className={styles.connectorArrow}>↓</div>
          <div className={styles.judgeBlock}>
            <div className={styles.judgeHeader}>
              <span className={styles.judgeLabel}>Corrección · LLM as Judge</span>
              {steerCountdown !== undefined && fp === "correcting" && (
                <span className={styles.judgeCountdown}>{steerCountdown}s</span>
              )}
            </div>
            {/* Prompt fijo — no se mueve ni desaparece */}
            <div className={styles.promptBox}>{correctionText}</div>

            {/* Botones solo mientras esperamos confirmación */}
            {fp === "correcting" && (
              <motion.div
                className={styles.steerActions}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <button type="button" className={styles.btnConfirm} onClick={onConfirm}>
                  Confirmar steering
                </button>
                <button type="button" className={styles.btnReject} onClick={onReject}>
                  Rechazar
                </button>
              </motion.div>
            )}
          </div>
        </motion.div>
      )}

      {/* ── LOOP STATUS ── aparece en migrating, cambia texto, PERMANECE hasta el final */}
      {phaseGte(fp, "migrating") && correctionText && (
        <motion.div
          className={styles.loopBlock}
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className={styles.connectorArrow}>↓</div>
          <div className={styles.loopIndicator}>
            {/* Tokens animados solo mientras migrating */}
            {fp === "migrating" && (
              <div className={styles.tokensStream} aria-hidden="true">
                {correctionText.split(/\s+/).filter(Boolean).map((word, idx) => (
                  <motion.span
                    key={idx}
                    className={styles.migratingToken}
                    initial={{ opacity: 1, x: 0 }}
                    animate={{ opacity: 0, x: -500 }}
                    transition={{ delay: idx * 0.07, duration: 1.5, ease: "easeIn" }}
                  >
                    {word}
                  </motion.span>
                ))}
              </div>
            )}
            {/* Texto que cambia según la sub-fase pero el bloque se queda */}
            <div className={styles.loopStatusRow}>
              {fp === "migrating" ? (
                <>
                  <div className={styles.spinner} />
                  <span className={styles.loopLabel}>↙ ingresando al loop</span>
                </>
              ) : fp === "rerunning" ? (
                <>
                  <div className={styles.spinner} />
                  <span className={styles.loopLabel}>Loop en progreso... ⟳</span>
                </>
              ) : (
                <>
                  <div className={`${styles.spinner} ${styles.spinnerDone}`} />
                  <span className={styles.loopLabel}>↻ loop</span>
                </>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* ── SALIDA CORREGIDA + BADGE ── suma al final */}
      {phaseGte(fp, "final") && steered && (
        <motion.div
          className={styles.finalSection}
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className={styles.connectorArrow}>↓</div>
          <div className={styles.outputLabel}>Salida corregida</div>
          <div className={styles.outputBox}>{steered.summary}</div>
          <motion.div
            className={styles.resultBadge}
            data-action={steered.action}
            initial={{ opacity: 0, scale: 0.88 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", damping: 10, mass: 0.8, delay: 0.3 }}
          >
            <span className={styles.resultAction}>{steered.action}</span>
            <span className={styles.resultTrust}>trust: {steered.trust_score}/100</span>
            {steerDelta && (
              <span className={styles.resultDelta}>
                {steerDelta.original} → {steerDelta.steered}
              </span>
            )}
          </motion.div>
        </motion.div>
      )}

    </div>
  );
}

function DivergenceChip({ divergence }: { divergence: Divergence }) {
  const sev =
    divergence.severity === "high" ? "high"
    : divergence.severity === "medium" ? "medium"
    : "low";

  return (
    <motion.div
      className={styles.divChip}
      data-severity={sev}
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className={styles.divCategory}>{formatCategory(divergence.category)}</div>
      <div className={styles.divClaim}>{divergence.verbal_claim}</div>
    </motion.div>
  );
}
