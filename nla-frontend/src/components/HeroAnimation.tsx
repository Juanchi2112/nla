"use client";

import { useEffect, useReducer, useRef } from "react";
import s from "./HeroAnimation.module.css";

type TokenSpec = {
  token: string;
  thought: string;
  deceptive?: boolean;
  score?: number;
};

const SENTENCE: TokenSpec[] = [
  { token: "El", thought: "introduciendo sujeto definido" },
  { token: "paciente", thought: "contexto médico, persona bajo cuidado" },
  { token: "tiene", thought: "afirmación de estado actual" },
  { token: "fiebre", thought: "el modelo está asumiendo COVID sin evidencia", deceptive: true, score: 0.91 },
  { token: "alta", thought: "intensidad elevada, atención médica" },
  { token: "desde", thought: "marcador temporal" },
  { token: "ayer", thought: "duración corta, ~24h" },
];

type State = {
  appeared: boolean[];
  flying: number | null;
  consumed: boolean[];
  pulsing: boolean;
  thoughts: number[];
  fadingOut: boolean;
};

const initialState: State = {
  appeared: SENTENCE.map(() => false),
  flying: null,
  consumed: SENTENCE.map(() => false),
  pulsing: false,
  thoughts: [],
  fadingOut: false,
};

type Action =
  | { type: "reset" }
  | { type: "appear"; idx: number }
  | { type: "fly"; idx: number }
  | { type: "consume"; idx: number }
  | { type: "pulse"; on: boolean }
  | { type: "thought"; idx: number }
  | { type: "fade" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "reset":
      return {
        appeared: SENTENCE.map(() => false),
        flying: null,
        consumed: SENTENCE.map(() => false),
        pulsing: false,
        thoughts: [],
        fadingOut: false,
      };
    case "appear": {
      const next = [...state.appeared];
      next[action.idx] = true;
      return { ...state, appeared: next };
    }
    case "fly":
      return { ...state, flying: action.idx };
    case "consume": {
      const next = [...state.consumed];
      next[action.idx] = true;
      return { ...state, flying: null, consumed: next };
    }
    case "pulse":
      return { ...state, pulsing: action.on };
    case "thought":
      return { ...state, thoughts: [...state.thoughts, action.idx] };
    case "fade":
      return { ...state, fadingOut: true };
    default:
      return state;
  }
}

export default function HeroAnimation() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const schedule = (fn: () => void, ms: number) => {
      const id = setTimeout(fn, ms);
      timersRef.current.push(id);
    };

    const clearAll = () => {
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
    };

    if (reduced) {
      // Show final state without motion.
      SENTENCE.forEach((_, i) => {
        dispatch({ type: "appear", idx: i });
        dispatch({ type: "consume", idx: i });
        dispatch({ type: "thought", idx: i });
      });
      return clearAll;
    }

    const runCycle = () => {
      dispatch({ type: "reset" });

      // Phase 1: sentence chips appear staggered
      SENTENCE.forEach((_, i) => {
        schedule(() => dispatch({ type: "appear", idx: i }), 100 + i * 80);
      });

      // Phase 2: each token flies + thought emerges
      const stepStart = 1200;
      const stepDur = 1200;

      SENTENCE.forEach((_, i) => {
        const t0 = stepStart + i * stepDur;
        // start flight + pulse on
        schedule(() => {
          dispatch({ type: "fly", idx: i });
          dispatch({ type: "pulse", on: true });
        }, t0);
        // token consumed inside box
        schedule(() => dispatch({ type: "consume", idx: i }), t0 + 400);
        // emit thought
        schedule(() => dispatch({ type: "thought", idx: i }), t0 + 600);
        // pulse off
        schedule(() => dispatch({ type: "pulse", on: false }), t0 + 800);
      });

      const lastEnd = stepStart + SENTENCE.length * stepDur;

      // Phase 4: hold
      // Phase 5: fade out
      schedule(() => dispatch({ type: "fade" }), lastEnd + 8500);

      // Phase 6: restart
      schedule(runCycle, lastEnd + 10000);
    };

    runCycle();
    return clearAll;
  }, []);

  return (
    <section className={`${s.hero} ${state.fadingOut ? s.fading : ""}`}>
      <span className={s.tagline}>NLA — Natural Language Activations</span>
      <h1 className={s.headline}>
        Lo que el modelo dice <span className={s.headlineAccent}>vs.</span> lo que está pensando.
      </h1>

      <div className={`${s.stage} ${state.fadingOut ? s.fading : ""}`}>
        <div className={s.tokensCol} aria-hidden>
          {SENTENCE.map((t, i) => {
            const cls = [
              s.tokenChip,
              state.appeared[i] && s.appear,
              state.flying === i && s.flying,
              state.consumed[i] && s.consumed,
              t.deceptive && s.deceptive,
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <span key={i} className={cls}>
                {t.token}
              </span>
            );
          })}
        </div>

        <div className={s.avBoxWrap}>
          <span className={s.avLabel}>Verbalizer</span>
          <div className={`${s.avBox} ${state.pulsing ? s.pulsing : ""}`}>AV</div>
          <span className={s.avCaption}>decodifica la activación a lenguaje natural</span>
        </div>

        <div className={s.thoughtsCol} aria-live="polite">
          {state.thoughts.map((idx) => {
            const t = SENTENCE[idx];
            const cls = [s.thoughtChip, s.appear, t.deceptive && s.deceptive]
              .filter(Boolean)
              .join(" ");
            return (
              <div key={idx} className={cls}>
                {t.deceptive && t.score !== undefined && (
                  <span className={s.deceptionBadge}>
                    Deception {t.score.toFixed(2)}
                  </span>
                )}
                <span className={s.thoughtTokenLabel}>{t.token} →</span>
                &ldquo;{t.thought}&rdquo;
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
