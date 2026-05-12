"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import s from "./article.module.css";
import ComoFuncionaHero from "@/components/animation/ComoFuncionaHero";

const cx = (...classes: (string | false | null | undefined)[]) =>
  classes.filter(Boolean).join(" ");

const generateValue = () => {
  const v = (Math.random() * 4 - 2).toFixed(3);
  return v.startsWith("-") ? v : " " + v;
};

const buildMatrix = () => {
  const data: string[] = [];
  for (let i = 0; i < 256; i++) data.push(generateValue());
  return data;
};

export default function ComoFunciona() {
  const articleRef = useRef<HTMLElement>(null);
  const triggeredRef = useRef<Set<string>>(new Set());
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const intervalsRef = useRef<ReturnType<typeof setInterval>[]>([]);

  // Block 5 matrix state
  const [matrix, setMatrix] = useState<string[]>([]);
  const [matrixVisible, setMatrixVisible] = useState(false);
  const [visibleRows, setVisibleRows] = useState<Set<number>>(new Set());
  const [promptPhase, setPromptPhase] = useState<"idle" | "show" | "melt" | "stretch" | "dissolve" | "hidden">("idle");

  // Animation state — using class additions on refs (avoids re-render storms)
  // We track which blocks have been triggered and run animations imperatively via setTimeout

  const setT = (fn: () => void, ms: number) => {
    const id = setTimeout(fn, ms);
    timeoutsRef.current.push(id);
    return id;
  };
  const setI = (fn: () => void, ms: number) => {
    const id = setInterval(fn, ms);
    intervalsRef.current.push(id);
    return id;
  };

  useEffect(() => {
    const article = articleRef.current;
    if (!article) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const el = entry.target as HTMLElement;
          const id = el.dataset.blockId;
          if (entry.isIntersecting && id && !triggeredRef.current.has(id)) {
            triggeredRef.current.add(id);
            el.classList.add(s.visible);
            observer.unobserve(el);
            runBlockAnimation(id);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -60px 0px" }
    );

    article.querySelectorAll<HTMLElement>("[data-block-id]").forEach((el) => observer.observe(el));

    return () => {
      observer.disconnect();
      timeoutsRef.current.forEach(clearTimeout);
      intervalsRef.current.forEach(clearInterval);
      timeoutsRef.current = [];
      intervalsRef.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const showById = (id: string, delay: number, cls: string = s.show) => {
    setT(() => {
      const el = document.getElementById(id);
      if (el) el.classList.add(cls);
    }, delay);
  };

  const glitchText = (
    elId: string,
    finalText: string,
    opts: { startDelay: number; glitchDuration: number }
  ) => {
    const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ¿?…";
    setT(() => {
      const el = document.getElementById(elId);
      if (!el) return;
      const start = performance.now();
      const tick = () => {
        const elapsed = performance.now() - start;
        if (elapsed >= opts.glitchDuration) {
          el.textContent = `“${finalText}”`;
          return;
        }
        let str = "";
        for (let i = 0; i < finalText.length; i++) {
          str += finalText[i] === " " ? " " : chars[Math.floor(Math.random() * chars.length)];
        }
        el.textContent = `“${str}”`;
        const t = setTimeout(tick, 60);
        timeoutsRef.current.push(t);
      };
      tick();
    }, opts.startDelay);
  };

  const typeText = (
    elId: string,
    finalText: string,
    opts: { startDelay: number; charDelay: number; wrap?: boolean; onStart?: () => void; onDone?: () => void }
  ) => {
    const wrap = opts.wrap !== false;
    const open = wrap ? "“" : "";
    const close = wrap ? "”" : "";
    setT(() => {
      const el = document.getElementById(elId);
      if (!el) return;
      opts.onStart?.();
      let i = 0;
      el.textContent = open;
      const tick = () => {
        if (i >= finalText.length) {
          el.textContent = `${open}${finalText}${close}`;
          opts.onDone?.();
          return;
        }
        i++;
        el.textContent = `${open}${finalText.slice(0, i)}`;
        const t = setTimeout(tick, opts.charDelay);
        timeoutsRef.current.push(t);
      };
      tick();
    }, opts.startDelay);
  };

  const scanSteps = (parentId: string, baseDelay: number, schedule: number[], holdTail = 600) => {
    setT(() => {
      const parent = document.getElementById(parentId);
      if (!parent) return;
      const steps = Array.from(parent.querySelectorAll<HTMLElement>("[data-b6-step]"));
      steps.forEach((el, i) => {
        const startAt = schedule[i] ?? 0;
        const endAt = i + 1 < schedule.length ? schedule[i + 1] : startAt + holdTail;
        setT(() => el.classList.add(s.b6StepActive), startAt);
        setT(() => el.classList.remove(s.b6StepActive), endAt);
      });
    }, baseDelay);
  };

  const runBlockAnimation = (id: string) => {
    if (id === "block-p1") {
      showById("p1-l1", 200);
      showById("p1-l2", 900);
      showById("p1-code", 1700);
      showById("p1-l3", 2600);
      showById("p1-l4", 3300);
      showById("p1-l5", 4100);
    } else if (id === "block-5") {
      animateBlock5();
    } else if (id === "block-6") {
      showById("b6-early", 400);
      scanSteps("b6-early", 400, [0, 220, 440, 660, 880], 1500);
      glitchText("b6-bottleneck-early", "can be a text about any topic", { startDelay: 900, glitchDuration: 1200 });
      showById("b6-transition", 1400);
      showById("b6-trained", 2200);
      scanSteps("b6-trained", 2200, [0, 220, 440, 660, 880], 1500);
      typeText("b6-bottleneck-trained", "the model is thinking about X", { startDelay: 2700, charDelay: 55 });
      showById("b6-text", 3200);
    } else if (id === "block-7") {
      showById("b7-row-classic", 400);
      showById("b7-row-nla", 1200);
      showById("b7-bn", 1400);
      showById("b7-phrase", 2800);
    } else if (id === "block-p5") {
      showById("p5-intro", 200);
      [1, 2, 3, 4].forEach((n, i) => showById(`p5-step-${n}`, 800 + i * 240));
      [1, 2, 3].forEach((n, i) => showById(`p5-arrow-${n}`, 800 + (i + 1) * 240 - 80));
      const after = 800 + 4 * 240;
      showById("p5-explain", after + 400);
      showById("p5-cite", after + 1100);
      showById("p5-cta", after + 1800);
    }
  };

  const animateBlock5 = () => {
    setMatrix(buildMatrix());
    const prompt = document.getElementById("b5-prompt");

    setPromptPhase("show");

    setT(() => {
      requestAnimationFrame(() => setPromptPhase("melt"));
    }, 1800);

    setT(() => setPromptPhase("stretch"), 2300);

    setT(() => {
      setPromptPhase("dissolve");
      setMatrixVisible(true);
      const rows = 16;
      const mid = Math.floor(rows / 2);
      for (let i = 0; i < rows; i++) {
        const dist = Math.abs(i - mid);
        const idx = i;
        setT(() => setVisibleRows((prev) => new Set(prev).add(idx)), dist * 25);
      }
    }, 2700);

    setT(() => {
      if (prompt) prompt.style.display = "none";
      // Flicker — faster, more cells per tick
      setI(() => {
        const count = 8 + Math.floor(Math.random() * 6);
        setMatrix((prev) => {
          const next = [...prev];
          for (let i = 0; i < count; i++) {
            const idx = Math.floor(Math.random() * 256);
            next[idx] = generateValue();
          }
          return next;
        });
      }, 600);
    }, 3500);

    showById("b5-text", 3700);
  };

  const promptClass = cx(
    s.b5Prompt,
    promptPhase === "show" && s.show,
    (promptPhase === "melt" || promptPhase === "stretch" || promptPhase === "dissolve") && s.show,
    promptPhase === "melt" && s.melt,
    promptPhase === "stretch" && s.melt,
    promptPhase === "stretch" && s.stretch,
    promptPhase === "dissolve" && s.melt,
    promptPhase === "dissolve" && s.stretch,
    promptPhase === "dissolve" && s.dissolve,
  );

  return (
    <>
      <div className={s.pageTop}></div>

      <main className={s.article} ref={articleRef}>

        <ComoFuncionaHero />

        {/* BLOCK 1 — The Problem (NEW, technical) */}
        <div className={cx(s.block, "lyt-loose")} data-block-id="block-p1" id="block-p1">
          <hr className={s.divider} />
          <div className={s.blockNumber}>01</div>
          <h2 className={s.blockTitle}>Illegible thought</h2>
          <div className={s.p1Stage}>
            <p className={s.p1Lead} id="p1-l1">
              Every token from an LLM produces a vector in the residual stream — where the model decides.
            </p>
            <p className={s.p1Lead} id="p1-l2">
              Thousands of dimensions per layer. Here is what one looks like:
            </p>

            <div className={s.p1Code} id="p1-code">
              <div className={s.p1CodeHeader}>
                <span className={s.p1CodePrompt}>{">"}</span>
                <span className={s.p1CodeCmd}>hidden_states[0, 20, &quot;weather&quot;]</span>
              </div>
              <div className={s.p1CodeBody}>
                <span className={s.p1CodeBracket}>[</span>
                <span className={s.p1CodeNums}>
                  {" 0.4231, -1.8547,  0.0712,  0.9384, -0.4108,  1.3219, -0.6843,  0.1576,  0.7642, -0.2891,  0.5435, -0.8327,  0.3814,  0.6147, -0.1209,  0.4778, -0.9521,  0.1873,  0.7251, -0.3411,  0.0623, -0.5326,  0.8912,  0.2174, "}
                </span>
                <span className={s.p1CodeEllipsis}>… 3560 more</span>
                <span className={s.p1CodeBracket}>]</span>
              </div>
            </div>

            <p className={s.p1Lead} id="p1-l3">
              One token, one layer. Qwen2.5-7B: 3584 numbers × 28 layers.
            </p>
            <p className={s.p1Lead} id="p1-l4">
              Until today, illegible.
            </p>
          </div>
        </div>

        {/* BLOCK 5 — Activations */}
        <div className={cx(s.block, s.b5Wide)} data-block-id="block-5" id="block-5">
          <hr className={s.divider} />
          <div className={s.blockNumber}>02</div>
          <h2 className={s.blockTitle}>Activations</h2>
          <div className={s.b5Stage}>
            <div className={promptClass} id="b5-prompt">describe today&apos;s weather</div>
            <div className={s.b5MatrixWrap}>
              <div className={s.b5Matrix}>
                {matrixVisible && Array.from({ length: 16 }).map((_, r) => (
                  <div
                    key={r}
                    className={cx(s.b5MatrixRow, visibleRows.has(r) && s.show)}
                  >
                    {Array.from({ length: 16 }).map((_, c) => {
                      const idx = r * 16 + c;
                      const v = parseFloat(matrix[idx] ?? "0");
                      const mag = Math.abs(v);
                      const high = mag > 1.5;
                      const low = mag < 0.5;
                      return (
                        <span
                          key={c}
                          className={cx(s.b5CellFlash, high && s.b5CellHigh, low && s.b5CellLow)}
                          style={high ? { animationDelay: `${(idx % 7) * 0.4}s` } : undefined}
                        >
                          {(matrix[idx] ?? "  0.000") + (c < 15 ? " " : "")}
                        </span>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
            <p className={s.b5Text} id="b5-text">This is what the model is thinking.</p>
            <p
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 14,
                color: "var(--fg-tertiary)",
                marginTop: 24,
                textAlign: "center",
                letterSpacing: "0.04em",
              }}
            >
              For Qwen2.5-7B, these are vectors of 3584 dimensions per token, across 28 layers.
            </p>
          </div>
        </div>

        {/* BLOCK 6 — The Idea of NLA */}
        <div className={cx(s.block, s.b6Wide, "lyt-loose")} data-block-id="block-6" id="block-6">
          <hr className={s.divider} />
          <div className={s.blockNumber}>03</div>
          <h2 className={s.blockTitle}>The NLA Concept</h2>

          <div className={cx(s.b6Phase, s.b6Early)} id="b6-early">
            <div className={s.b6PhaseLabel}>At the start of training</div>
            <div className={s.b6DiagramWrap}>
              <div className={s.b6Diagram}>
                <div className={s.b6Box} data-b6-step>
                  <span className={s.b6BoxLabel}>Activation</span>
                  <div className={s.b6Grid}>{`0.42 0.17 0.83 0.05
0.91 0.33 0.68 0.12
0.07 0.74 0.29 0.56
0.63 0.48 0.11 0.87`}</div>
                </div>
                <ArrowRight cls={s.b6Arrow} />
                <div className={s.b6Box} data-b6-step>
                  <span className={s.b6BoxLabel}>Verbalizer</span>
                  <div className={s.b6BoxName}>AV</div>
                </div>
                <ArrowRight cls={s.b6Arrow} />
                <div className={s.b6Bottleneck} id="b6-bottleneck-early" data-b6-step>&nbsp;</div>
                <ArrowRight cls={s.b6Arrow} />
                <div className={s.b6Box} data-b6-step>
                  <span className={s.b6BoxLabel}>Reconstructor</span>
                  <div className={s.b6BoxName}>AR</div>
                </div>
                <ArrowRight cls={s.b6Arrow} />
                <div className={s.b6Box} data-b6-step>
                  <span className={s.b6BoxLabel}>Reconstructed</span>
                  <div className={s.b6Grid}>{`0.91 -0.34 0.12 1.05
0.27 0.88 -0.45 0.73
0.54 -0.11 0.96 0.08
-0.38 0.62 0.41 0.19`}</div>
                </div>
              </div>
            </div>
          </div>

          <div className={s.b6TransitionArrow} id="b6-transition">
            <svg width="16" height="32" viewBox="0 0 16 32" fill="none" stroke="currentColor" strokeWidth="1.2">
              <line x1="8" y1="2" x2="8" y2="26" />
              <polyline points="4,22 8,28 12,22" />
            </svg>
            training
            <svg width="16" height="32" viewBox="0 0 16 32" fill="none" stroke="currentColor" strokeWidth="1.2">
              <line x1="8" y1="2" x2="8" y2="26" />
              <polyline points="4,22 8,28 12,22" />
            </svg>
          </div>

          <div className={s.b6Phase} id="b6-trained">
            <div className={s.b6PhaseLabel}>After training</div>
            <div className={s.b6DiagramWrap}>
              <div className={s.b6Diagram}>
                <div className={s.b6Box} data-b6-step>
                  <span className={s.b6BoxLabel}>Activation</span>
                  <div className={s.b6Grid}>{`0.42 0.17 0.83 0.05
0.91 0.33 0.68 0.12
0.07 0.74 0.29 0.56
0.63 0.48 0.11 0.87`}</div>
                </div>
                <ArrowRight cls={s.b6Arrow} />
                <div className={s.b6Box} data-b6-step>
                  <span className={s.b6BoxLabel}>Verbalizer</span>
                  <div className={s.b6BoxName}>AV</div>
                </div>
                <ArrowRight cls={s.b6Arrow} />
                <div className={s.b6Bottleneck} id="b6-bottleneck-trained" data-b6-step style={{ color: "var(--accent)" }}>&nbsp;</div>
                <ArrowRight cls={s.b6Arrow} />
                <div className={s.b6Box} data-b6-step>
                  <span className={s.b6BoxLabel}>Reconstructor</span>
                  <div className={s.b6BoxName}>AR</div>
                </div>
                <ArrowRight cls={s.b6Arrow} />
                <div className={s.b6Box} data-b6-step>
                  <span className={s.b6BoxLabel}>Reconstructed</span>
                  <div className={s.b6Grid}>{`0.41 0.18 0.82 0.06
0.90 0.34 0.67 0.13
0.08 0.73 0.30 0.55
0.62 0.49 0.12 0.86`}</div>
                </div>
              </div>
            </div>
          </div>

          <p className={s.b6Text} id="b6-text">
            One model learns to describe them. Another learns to reconstruct them. If the second one recovers the original vector, the description successfully captured the information.
          </p>
        </div>

        {/* BLOCK 7 — Classic Autoencoder vs NLA */}
        <div className={cx(s.block, s.block7, "lyt-tight")} data-block-id="block-7" id="block-7">
          <hr className={s.divider} />
          <div className={s.blockNumber}>04</div>
          <h2 className={s.blockTitle}>Classic Autoencoder vs NLA</h2>

          <div className={s.b7Comparison}>
            <div className={s.b7Row} id="b7-row-classic">
              <div className={s.b7RowLabel}>Classic Autoencoder</div>
              <div className={s.b7Pipeline}>
                <div className={s.b7Box}>
                  <span className={s.b7BoxLabel}>Input</span>
                  <div className={s.b7BoxText}>the weather is cloudy</div>
                </div>
                <ArrowRight cls={s.b7Arrow} small />
                <div className={s.b7Box}>
                  <span className={s.b7BoxLabel}>Encoder</span>
                  <div className={s.b7BoxName}>E</div>
                </div>
                <ArrowRight cls={s.b7Arrow} small />
                <div className={s.b7Box}>
                  <span className={s.b7BoxLabel}>Latent</span>
                  <div className={s.b7Grid}>{` 0.24 -1.85  0.07  0.93
-0.41  1.32 -0.68  0.15
 0.76 -0.29  1.54 -0.83
 0.38  0.61 -1.12  0.47
-0.95  0.18  0.72 -0.34
 1.06 -0.53  0.89  0.21`}</div>
                </div>
                <ArrowRight cls={s.b7Arrow} small />
                <div className={s.b7Box}>
                  <span className={s.b7BoxLabel}>Decoder</span>
                  <div className={s.b7BoxName}>D</div>
                </div>
                <ArrowRight cls={s.b7Arrow} small />
                <div className={s.b7Box}>
                  <span className={s.b7BoxLabel}>Reconstruction</span>
                  <div className={s.b7BoxText}>the weather is cloudy</div>
                </div>
              </div>
            </div>

            <div className={s.b7Row} id="b7-row-nla">
              <div className={s.b7RowLabel}>NLA</div>
              <div className={s.b7Pipeline}>
                <div className={s.b7Box}>
                  <span className={s.b7BoxLabel}>Activation</span>
                  <div className={s.b7Grid}>{`0.42 0.17 0.83 0.05
0.91 0.33 0.68 0.12
0.07 0.74 0.29 0.56
0.63 0.48 0.11 0.87`}</div>
                </div>
                <ArrowRight cls={s.b7Arrow} small />
                <div className={s.b7Box}>
                  <span className={s.b7BoxLabel}>Verbalizer</span>
                  <div className={s.b7BoxName}>AV</div>
                </div>
                <ArrowRight cls={s.b7Arrow} small />
                <div className={s.b7BottleneckAccent} id="b7-bn">
                  <span className={s.b7BoxLabel}>Bottleneck</span>
                  <div className={s.b7BnText}>&ldquo;the model believes the user is Russian&rdquo;</div>
                </div>
                <ArrowRight cls={s.b7Arrow} small />
                <div className={s.b7Box}>
                  <span className={s.b7BoxLabel}>Reconstructor</span>
                  <div className={s.b7BoxName}>AR</div>
                </div>
                <ArrowRight cls={s.b7Arrow} small />
                <div className={s.b7Box}>
                  <span className={s.b7BoxLabel}>Reconstructed</span>
                  <div className={s.b7Grid}>{`0.41 0.18 0.82 0.06
0.90 0.34 0.67 0.13
0.08 0.73 0.30 0.55
0.62 0.49 0.12 0.86`}</div>
                </div>
              </div>
            </div>
          </div>

          <p className={s.b7MainPhrase} id="b7-phrase">
            The latent space <span className={s.b7Dim}>is not a vector.</span>{" "}
            <span className={s.b7Accent}>It is text.</span>
          </p>
        </div>

        {/* BLOCK 5 — How we apply it */}
        <div className={cx(s.block, s.b6Wide, "lyt-loose")} data-block-id="block-p5" id="block-p5">
          <hr className={s.divider} />
          <div className={s.blockNumber}>05</div>
          <h2 className={s.blockTitle}>How we apply it</h2>

          <p className={s.p5Intro} id="p5-intro">
            Verbalize is the first implementation of NLA as a monitoring layer for production agents.
          </p>

          <div className={s.p5Flow} id="p5-flow">
            {(() => {
              const steps = [
                { num: "01", title: "Run Qwen2.5-7B", body: "Served via SGLang." },
                { num: "02", title: "Extract hidden_states", body: "Layer 20 of the residual stream." },
                { num: "03", title: "Verbalize", body: "kitft AV translates activations to text." },
                { num: "04", title: "Trust score", body: "LLM Judge compares verbal vs. thought.", output: true },
              ];
              return steps.map((step, i) => (
                <Fragment key={step.num}>
                  <div
                    className={cx(s.p5Node, step.output && s.p5NodeOutput, "p5step")}
                    id={`p5-step-${i + 1}`}
                  >
                    <div className={s.p5NodeNum}>{step.num}</div>
                    <div className={s.p5NodeTitle}>{step.title}</div>
                    <div className={s.p5NodeBody}>{step.body}</div>
                    {step.output && <div className={s.p5NodeKicker}>Output</div>}
                  </div>
                  {i < steps.length - 1 && (
                    <svg
                      className={s.p5Arrow}
                      id={`p5-arrow-${i + 1}`}
                      viewBox="0 0 28 14"
                      aria-hidden="true"
                    >
                      <line x1="0" y1="7" x2="22" y2="7" />
                      <polyline points="18,3 24,7 18,11" />
                    </svg>
                  )}
                </Fragment>
              ));
            })()}
          </div>

          <p className={s.p5Explain} id="p5-explain">
            We capture the activations of the residual stream in a mid-to-late layer during generation. The AV translates them into natural language, and the AR reconstructs them to validate fidelity. An LLM judge compares the verbal output with the internal thought and issues an alignment score.
          </p>

          <a
            className={s.p5PaperCard}
            id="p5-cite"
            href="https://transformer-circuits.pub/2026/nla/index.html"
            target="_blank"
            rel="noopener noreferrer"
          >
            <div className={s.p5PaperLeft}>
              <div className={s.p5PaperKicker}>
                [ paper · <em>2026</em> ]
              </div>
              <div className={s.p5PaperCitation}>
                Fraser-Taliente, K., et al. <em>Natural Language Autoencoders Produce Unsupervised Explanations of LLM Activations.</em> Anthropic.
              </div>
            </div>
            <div className={s.p5PaperRail}>
              <span className={s.p5PaperBadge}>transformer-circuits.pub</span>
              <span className={s.p5PaperLink}>Read paper →</span>
            </div>
          </a>

          <a
            href="/example"
            className={s.ctaCard}
            id="p5-cta"
            style={{ opacity: 0, transition: "opacity 800ms var(--ease-default)" }}
          >
            <span className={s.ctaText}>
              See the example in action
              <br />
              <span style={{ color: "var(--fg-secondary)", fontSize: 16 }}>The Hospital · Full Narrative</span>
            </span>
            <span className={s.ctaArrow}>→</span>
          </a>
        </div>
      </main>

      <div className={s.pageBottom}></div>
    </>
  );
}

function ArrowRight({ cls, small = false }: { cls: string; small?: boolean }) {
  if (small) {
    return (
      <svg className={cls} viewBox="0 0 36 16">
        <line x1="3" y1="8" x2="28" y2="8" />
        <polyline points="24,4 30,8 24,12" />
      </svg>
    );
  }
  return (
    <svg className={cls} viewBox="0 0 48 20">
      <line x1="4" y1="10" x2="38" y2="10" />
      <polyline points="34,5 40,10 34,15" />
    </svg>
  );
}
