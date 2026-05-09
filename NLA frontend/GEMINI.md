# NLA Visualization & Steering Demo

## Project Scope
This project is an interactive frontend demonstration for an AI Security Hackathon. It visualizes the **Natural Language Autoencoder (NLA)** research from Anthropic (2026).

### Primary Objectives
1.  **Visualization:** Create a "Deep Dive" interface to show the internal activations of an LLM during inference, translated into natural language (Internal Monologue) by an NLA.
2.  **Safety & Security:** Demonstrate the detection of **Misreported Tool Calls** (deceptive behavior) using a grader LLM to score the NLA's output.
3.  **Steering:** Show real-time intervention by halting generation when high deception scores are detected and steering the model back to truthfulness via prompt injection.

## Project Architecture
-   **Framework:** Next.js (TypeScript) with vanilla CSS modules.
-   **State Management:** React hooks (`useState`, `useRef`) for simulating token-by-token streaming.
-   **Data Model:** `src/lib/mockData.ts` defines the `Token` and `NlaTrace` structures.

## Core Conventions
-   **Styling:** Prefer vanilla CSS in `.module.css` files.
-   **Naming:** Use `camelCase` for variables/functions and `PascalCase` for React components.
-   **NLA Methodology:** Always prioritize the "Internal Monologue" text over raw activation values to remain consistent with the Anthropic paper.

## Current Progress (MVP)
-   [x] Project initialization and directory structure.
-   [x] Mock data for the "Misreported Tool Call" scenario.
-   [x] Interactive split-screen dashboard with token streaming and hover effects.
-   [x] Automated detection of deception spikes.
-   [x] Implementation of the "Steering" correction flow.
-   [ ] Integration with real backend inference output (Pending access to `../nla` folder).

## Documentation Index
-   **Detailed Implementation Plan:** `../../.gemini/tmp/nla-frontend/a67970c0-d571-4aad-bbc5-892f4992b090/plans/nla-demo-plan.md`
-   **Backend Reference:** [Anthropic NLA Paper](https://transformer-circuits.pub/2026/nla/index.html)
