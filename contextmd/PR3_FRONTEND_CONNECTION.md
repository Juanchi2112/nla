# PR 3: Frontend Connection & State Synchronization

## Goal
Update the Next.js frontend to talk to the real FastAPI backend instead of relying on `mockData.ts`.

## UI Changes
1. **Session ID:** On prompt submission, generate a `crypto.randomUUID()`.
2. **Stream Connection:**
   - Use `const eventSource = new EventSource(\`/api/stream/\${sessionId}\`)`.
   - Update `onmessage` to parse the JSON and update the React `tokens` and `nlaTraces` state.
3. **Deception Monitoring:**
   - If `judge_score > 0.8`, trigger the UI "Spike" animation and halt the stream (or show the steering options).
4. **Steering Trigger:**
   - On clicking a rubric (e.g., "Security"), send `POST /api/steer` with the current session ID.

## Requirements
- Handle `CORS` in FastAPI to allow the Next.js origin.
- Robust error handling for network drops (automatic reconnection or user alert).

## Verification
- Start the Next.js dev server and the FastAPI server.
- Submit a prompt and watch tokens stream into the UI components.
- Confirm the "Deception Detected" toast appears when the backend sends a high score.
