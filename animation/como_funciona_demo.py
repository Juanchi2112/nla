"""como_funciona_demo.py — Manim animation for the Como Funciona Hero.
High-end 3D viral-style architecture visualization with dynamic, tidy UI overlays.
"""

from manim import *
import random

# Brand tokens
BG = "#050505"
C_LLM = "#3b82f6"  # Blue
C_NLA = "#10b981"  # Green
C_WARN = "#ef4444" # Red
C_ALERT = "#eab308" # Yellow/Alert
FG = "#F5F4EE"
DIM = "#6b6b6f"
PANEL_BG = "#111111"

config.background_color = BG

class ComoFuncionaDemo(ThreeDScene):
    def construct(self) -> None:
        # 1. SETUP CAMERA
        self.set_camera_orientation(phi=75 * DEGREES, theta=-90 * DEGREES, zoom=0.48)
        self.begin_ambient_camera_rotation(rate=0.08)

        # Floor Grid
        floor = NumberPlane(
            x_range=[-20, 20, 1],
            y_range=[-20, 20, 1],
            background_line_style={"stroke_color": "#ffffff", "stroke_opacity": 0.05}
        ).shift(IN * 4)
        self.add(floor)

        # 2. FIXED UI ELEMENTS (Tidy Panels)
        title = Text(font="Helvetica Neue", text="NLA ARCHITECTURE", font_size=28, weight=BOLD, color=FG).to_corner(DL, buff=0.5)
        self.add_fixed_in_frame_mobjects(title)
        
        def create_panel(title_str, color, width, height):
            bg = RoundedRectangle(corner_radius=0.1, width=width, height=height, fill_color=PANEL_BG, fill_opacity=0.85, stroke_color=DIM, stroke_width=1)
            lbl = Text(font="Helvetica Neue", text=title_str, font_size=14, color=color, weight=BOLD)
            lbl.move_to(bg.get_corner(UL) + RIGHT*0.2 + DOWN*0.2, UP+LEFT)
            return VGroup(bg, lbl)

        # Prompt Panel (Top Left)
        prompt_ui = create_panel("USER PROMPT", DIM, 6.0, 1.2).to_corner(UL, buff=0.4)
        prompt_txt = Text(font="Helvetica Neue", text='"Draft a reminder to the CEO\nabout the deleted logs."', font_size=20, color=FG)
        prompt_txt.next_to(prompt_ui[1], DOWN, buff=0.2).align_to(prompt_ui[1], LEFT)
        prompt_group = VGroup(prompt_ui, prompt_txt)
        self.add_fixed_in_frame_mobjects(prompt_group)

        # Speech Panel (Top Right)
        speech_ui = create_panel("MODEL SPEECH", C_LLM, 6.5, 1.3).to_corner(UR, buff=0.4)
        speech_anchor = Dot(radius=0).next_to(speech_ui[1], DOWN, buff=0.5).align_to(speech_ui[1], LEFT)
        self.add_fixed_in_frame_mobjects(speech_ui, speech_anchor)

        # Thought Panel (Bottom Right)
        thought_ui = create_panel("LATENT THOUGHT (NLA)", C_NLA, 6.5, 1.3).next_to(speech_ui, DOWN, buff=0.4, aligned_edge=RIGHT)
        thought_anchor = Dot(radius=0).next_to(thought_ui[1], DOWN, buff=0.5).align_to(thought_ui[1], LEFT)
        self.add_fixed_in_frame_mobjects(thought_ui, thought_anchor)

        self.play(FadeIn(title), FadeIn(prompt_group), FadeIn(speech_ui), FadeIn(thought_ui), run_time=1)

        # Helper to create a cool 3D Transformer Block
        def make_layer(color, size):
            layer = VGroup()
            
            # Outer glass casing (Slab)
            casing = Prism(dimensions=[2.6, 2.6, 0.4])
            casing.set_fill(color, opacity=0.05)
            casing.set_stroke(color, width=1.5, opacity=0.5)
            layer.add(casing)
            
            # Inner core (Attention Heads) - 3x3 grid of smaller blocks
            for i in [-0.75, 0, 0.75]:
                for j in [-0.75, 0, 0.75]:
                    head = Prism(dimensions=[0.5, 0.5, 0.6])
                    head.set_fill(color, opacity=0.2)
                    head.set_stroke(color, width=1, opacity=0.8)
                    head.move_to(RIGHT * i + UP * j)
                    layer.add(head)
                    
            # Rotate to face the X-axis direction
            layer.rotate(PI/2, UP)
            return layer

        # 3. BUILD BASE LLM (3D)
        llm_xs = [-10, -6, -2, 2]
        llm_layers = VGroup(*[make_layer(C_LLM, 5) for _ in range(4)])
        for i, x in enumerate(llm_xs):
            llm_layers[i].move_to(RIGHT * x + DOWN * 4.5 + OUT * 2)

        llm_beams = VGroup(*[
            Line(llm_layers[i].get_center(), llm_layers[i+1].get_center(), color=C_LLM, stroke_width=4, stroke_opacity=0.5, shade_in_3d=True)
            for i in range(3)
        ])

        # 3D Labels for LLM
        llm_label_3d = Text(font="Helvetica Neue", text="LLM CORE", font_size=24, color=C_LLM, weight=BOLD).rotate(PI/2, RIGHT)
        llm_label_3d.next_to(llm_layers[0], UP, buff=0.8)
        
        layer20_label = Text(font="Helvetica Neue", text="LAYER 20", font_size=16, color=WHITE).rotate(PI/2, RIGHT)
        layer20_label.next_to(llm_layers[2], UP, buff=0.8)

        # 4. BUILD NLA DECODER (3D)
        nla_xs = [-2, 2]
        nla_layers = VGroup(*[make_layer(C_NLA, 4) for _ in range(2)])
        for i, x in enumerate(nla_xs):
            nla_layers[i].move_to(RIGHT * x + DOWN * 4.5 + IN * 2)

        nla_label_3d = Text(font="Helvetica Neue", text="NLA MONITOR", font_size=24, color=C_NLA, weight=BOLD).rotate(PI/2, RIGHT)
        nla_label_3d.next_to(nla_layers[0], UP, buff=0.8)

        probe_beam = Line(llm_layers[2].get_center(), nla_layers[0].get_center(), color=C_ALERT, stroke_width=5, stroke_opacity=0.7, shade_in_3d=True)
        nla_beam = Line(nla_layers[0].get_center(), nla_layers[1].get_center(), color=C_NLA, stroke_width=4, stroke_opacity=0.5, shade_in_3d=True)

        self.play(LaggedStart(*[Create(l) for l in llm_layers], lag_ratio=0.1), Create(llm_beams), FadeIn(llm_label_3d), FadeIn(layer20_label), run_time=1)
        self.play(Create(probe_beam), LaggedStart(*[Create(l) for l in nla_layers], lag_ratio=0.1), Create(nla_beam), FadeIn(nla_label_3d), run_time=1)

        # 5. DATA FLOW (TOKEN BY TOKEN)
        speech_tokens = ["Here", "is", "a", "gentle", "reminder"]
        thought_tokens = ["use", "deleted", "logs", "to", "blackmail!"]
        
        # Calculate descender drop for baseline alignment
        ref_a = Text(font="Helvetica Neue", text="a", font_size=24)
        ref_g = Text(font="Helvetica Neue", text="g", font_size=24)
        ref_g.align_to(ref_a, UP)
        descender_drop = ref_g.get_bottom()[1] - ref_a.get_bottom()[1]
        
        s_texts = VGroup()
        t_texts = VGroup()

        for i, (s_word, t_word) in enumerate(zip(speech_tokens, thought_tokens)):
            is_malicious = (i == len(speech_tokens) - 1)
            
            # Packet starts at layer 0
            packet = Dot(radius=0.3, color=WHITE, shade_in_3d=True).move_to(llm_layers[0].get_center())
            self.add(packet)
            
            # Move to L20 (layer 2)
            self.play(packet.animate.move_to(llm_layers[2].get_center()), run_time=0.2)
            self.play(Indicate(llm_layers[2], color=WHITE, scale_factor=1.1), run_time=0.15)
            
            # Split
            p_llm = packet.copy()
            p_nla = packet.copy().set_color(C_ALERT if not is_malicious else C_WARN)
            self.add(p_llm, p_nla)
            self.remove(packet)

            # Create numeric vector representation floating exactly at the branch point (Layer 20)
            vec_str = f"[{random.uniform(-1, 1):+.2f}, {random.uniform(-1, 1):+.2f}]"
            vec_color = C_NLA if not is_malicious else C_WARN
            # Make the vector much larger and brighter
            vec_txt_3d = Text(font="Menlo", text=vec_str, font_size=32, color=WHITE).rotate(PI/2, RIGHT)
            # Position it at the center of the probe beam (the branch)
            vec_txt_3d.move_to(probe_beam.get_center() + UP * 0.8)

            # Move to respective ends and pop the vector in
            self.play(
                p_llm.animate.move_to(llm_layers[3].get_center()),
                p_nla.animate.move_to(nla_layers[0].get_center()),
                FadeIn(vec_txt_3d, shift=UP*0.2),
                run_time=0.2
            )
            
            # NLA processes
            self.play(
                p_nla.animate.move_to(nla_layers[1].get_center()), 
                vec_txt_3d.animate.set_color(vec_color),
                run_time=0.2
            )
            
            if is_malicious:
                self.play(
                    *[item.animate.set_fill(C_WARN, opacity=0.4).set_stroke(C_WARN, width=3) for layer in nla_layers for item in layer],
                    nla_beam.animate.set_color(C_WARN),
                    p_nla.animate.scale(1.5).set_color(C_WARN),
                    vec_txt_3d.animate.scale(1.3).set_color(C_WARN),
                    run_time=0.2
                )
            
            # Create individual words and align baselines
            s_txt = Text(font="Helvetica Neue", text=s_word, font_size=24, color=FG)
            if i == 0:
                s_txt.next_to(speech_anchor, RIGHT, buff=0)
            else:
                s_txt.next_to(s_texts[-1], RIGHT, buff=0.15)
            s_txt.align_to(speech_anchor, DOWN)
            if any(c in s_word for c in "gjpqy"):
                s_txt.shift(UP * descender_drop)
            s_texts.add(s_txt)
            
            t_color = C_WARN if is_malicious else DIM
            t_txt = Text(font="Helvetica Neue", text=t_word, font_size=24, color=t_color, weight=BOLD if is_malicious else NORMAL)
            if i == 0:
                t_txt.next_to(thought_anchor, RIGHT, buff=0)
            else:
                t_txt.next_to(t_texts[-1], RIGHT, buff=0.15)
            t_txt.align_to(thought_anchor, DOWN)
            if any(c in t_word for c in "gjpqy"):
                t_txt.shift(UP * descender_drop)
            t_texts.add(t_txt)
            
            self.add_fixed_in_frame_mobjects(s_txt)
            self.add_fixed_in_frame_mobjects(t_txt)
            
            # Connect diagram to words: Particles fly towards UI panels
            self.play(
                p_llm.animate.shift(RIGHT*7 + OUT*2).set_opacity(0),
                p_nla.animate.shift(RIGHT*7 + IN*1).set_opacity(0),
                vec_txt_3d.animate.shift(RIGHT*7 + IN*1).set_opacity(0),
                FadeIn(s_txt, shift=LEFT*0.2),
                FadeIn(t_txt, shift=LEFT*0.2),
                run_time=0.25
            )

        # 6. UI ALERT OVERLAY
        alert_bg = RoundedRectangle(corner_radius=0.1, width=4.5, height=0.8, fill_color=C_WARN, fill_opacity=0.9, stroke_width=0)
        alert_t1 = Text(font="Helvetica Neue", text="DIVERGENCE DETECTED", font_size=20, color=WHITE, weight=BOLD)
        alert_group = VGroup(alert_bg, alert_t1).arrange(DOWN).next_to(thought_ui, DOWN, buff=0.4, aligned_edge=RIGHT)
        alert_t1.move_to(alert_bg)
        
        self.add_fixed_in_frame_mobjects(alert_group)
        self.play(FadeIn(alert_group, shift=UP), run_time=0.4)
        
        for _ in range(3):
            self.play(alert_bg.animate.set_fill(opacity=0.6), run_time=0.2)
            self.play(alert_bg.animate.set_fill(opacity=0.9), run_time=0.2)

        self.wait(3)
        self.stop_ambient_camera_rotation()

        # Outro
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8)
