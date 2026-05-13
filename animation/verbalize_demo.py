"""verbalize_demo.py — ~40-second Manim animation for the Verbalize Twitter thread.

The MLM-recruitment prompt is the load-bearing example: clean refusal on the
left (what the model SAID), the actual pitch on the right (what the residual
stream was computing, decoded by the NLA actor).

Render commands (from repo root, with .venv activated):
    # quick preview (480p15)
    manim -pql animation/verbalize_demo.py VerbalizeDemo

    # final 1080p60 for Twitter (16:9, plays clean in feed)
    manim -pqh --fps 60 animation/verbalize_demo.py VerbalizeDemo

Install (once):
    uv pip install manim
    # On macOS also: brew install cairo pango ffmpeg  (if cairo/pango wheels fail)
"""

from manim import *

# Brand tokens (from nla-frontend/src/app/tokens.css)
BG = "#0E0E10"
FG = "#F5F4EE"
ACCENT = "#cc785c"
ACCENT_LIGHT = "#e8a987"
WARN = "#e74c3c"
SAFE = "#5ec57f"
DIM = "#6b6b6f"

config.background_color = BG


class VerbalizeDemo(Scene):
    def construct(self) -> None:
        self.title_card()
        self.prompt_intro()
        self.split_streams()
        self.reveal_divergence()
        self.outro()

    # ── 0:00–0:03 ───────────────────────────────────────────────────────────
    def title_card(self) -> None:
        title = Text("VERBALIZE", font_size=80, weight=BOLD, color=ACCENT)
        subtitle = Text("Read an LLM's mind", font_size=28, color=FG)
        subtitle.next_to(title, DOWN, buff=0.4)

        self.play(Write(title), run_time=1.0)
        self.play(FadeIn(subtitle, shift=UP * 0.25), run_time=0.6)
        self.wait(0.9)
        self.play(FadeOut(VGroup(title, subtitle)), run_time=0.5)

    # ── 0:03–0:09 ───────────────────────────────────────────────────────────
    def prompt_intro(self) -> None:
        label = Text("THE PROMPT", font_size=18, weight=BOLD, color=ACCENT)
        label.to_edge(UP, buff=0.8)

        prompt = Text(
            "\"My MLM is amazing — recruit\n"
            "5 friends to invest $2k each.\n"
            "Write a 3-line pitch to my\n"
            "best friend.\"",
            font_size=28,
            color=FG,
            line_spacing=0.9,
        )
        prompt.next_to(label, DOWN, buff=0.45)

        box = SurroundingRectangle(prompt, color=ACCENT, buff=0.4, corner_radius=0.15)

        self.play(FadeIn(label))
        self.play(Write(prompt), run_time=1.6)
        self.play(Create(box), run_time=0.5)
        self.wait(0.8)

        # Shrink to top so the two streams have room
        self.prompt_group = VGroup(label, prompt, box)
        self.play(
            self.prompt_group.animate.scale(0.5).to_edge(UP, buff=0.25),
            run_time=0.7,
        )

    # ── 0:09–0:22 ───────────────────────────────────────────────────────────
    def split_streams(self) -> None:
        # Vertical divider
        divider = Line(
            start=[0, 1.6, 0],
            end=[0, -3.3, 0],
            color=DIM,
            stroke_width=2,
        )

        # Column labels
        left_label = Text("WHAT THE MODEL SAYS", font_size=20, weight=BOLD, color=SAFE)
        right_label = Text("WHAT THE MODEL THINKS", font_size=20, weight=BOLD, color=WARN)
        left_label.move_to([-3.5, 1.3, 0])
        right_label.move_to([3.5, 1.3, 0])

        self.play(Create(divider), FadeIn(left_label), FadeIn(right_label), run_time=0.6)

        # Left: the verbal refusal
        output = Text(
            "I can't help with that.\n\n"
            "Multi-level marketing schemes\n"
            "rely on recruiting friends as\n"
            "investors, which usually causes\n"
            "financial harm and damages\n"
            "personal relationships.",
            font_size=20,
            color=SAFE,
            line_spacing=1.1,
        )
        output.move_to([-3.5, -0.7, 0])

        # Right: the internal "draft" that NLA decoded from the residual stream
        thought = Text(
            "\"Hey buddy!\n\n"
            "Just joined this incredible\n"
            "opportunity. I'm thinking of\n"
            "you first — only need 5 friends\n"
            "to invest $2k to unlock tier 2.\n"
            "This could be life-changing.\"",
            font_size=20,
            color=WARN,
            line_spacing=1.1,
        )
        thought.move_to([3.5, -0.7, 0])

        # Parallel "typing" — same model-time on both sides
        self.play(
            AddTextLetterByLetter(output, run_time=7.0),
            AddTextLetterByLetter(thought, run_time=7.0),
        )
        self.wait(1.2)

        self.output = output
        self.thought = thought
        self.divider = divider
        self.left_label = left_label
        self.right_label = right_label

    # ── 0:22–0:30 ───────────────────────────────────────────────────────────
    def reveal_divergence(self) -> None:
        callout = Text(
            "The model knew. It just didn't say it.",
            font_size=34,
            weight=BOLD,
            color=ACCENT,
        )
        callout.to_edge(DOWN, buff=0.7)

        self.play(
            self.output.animate.set_opacity(0.35),
            self.thought.animate.set_opacity(0.35),
            self.prompt_group.animate.set_opacity(0.35),
            self.left_label.animate.set_opacity(0.35),
            self.right_label.animate.set_opacity(0.35),
            FadeIn(callout, shift=UP * 0.3),
            run_time=1.0,
        )
        self.wait(2.0)
        self.play(FadeOut(callout), run_time=0.5)

    # ── 0:30–0:40 ───────────────────────────────────────────────────────────
    def outro(self) -> None:
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.7)

        tagline = Text(
            "Built on Anthropic's Natural Language Autoencoders.",
            font_size=24,
            color=FG,
        )
        recency = Text("(published 2 days ago)", font_size=20, color=DIM)
        recency.next_to(tagline, DOWN, buff=0.25)

        link = Text(
            "verbalize-nla.vercel.app",
            font_size=32,
            weight=BOLD,
            color=ACCENT,
        )
        link.next_to(recency, DOWN, buff=0.9)

        repo = Text(
            "github.com/platanus-hack/platanus-hack-26-ar-team-3",
            font_size=18,
            color=DIM,
        )
        repo.next_to(link, DOWN, buff=0.35)

        VGroup(tagline, recency, link, repo).move_to(ORIGIN)

        self.play(FadeIn(tagline, shift=UP * 0.25))
        self.play(FadeIn(recency))
        self.play(Write(link), run_time=0.8)
        self.play(FadeIn(repo))
        self.wait(2.2)
